"""Pydantic AI adapters, with limits applied to each actual provider request."""

import asyncio
import json
import logging
import random
from contextlib import AsyncExitStack
from contextvars import ContextVar
from dataclasses import dataclass, field
from time import monotonic
from typing import Any

from pydantic import TypeAdapter
from pydantic_ai import Agent, ModelRetry, RunContext
from pydantic_ai.exceptions import (
    ModelAPIError,
    UnexpectedModelBehavior,
)
from pydantic_ai.messages import ModelMessage, ModelMessagesTypeAdapter, ModelResponse
from pydantic_ai.models import Model, ModelRequestParameters, infer_model
from pydantic_ai.models.openai import OpenAIChatModel, OpenAIResponsesModel
from pydantic_ai.models.wrapper import WrapperModel
from pydantic_ai.providers import infer_provider
from pydantic_ai.providers.gateway import gateway_provider
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.settings import ModelSettings

from creative.core import prompts
from creative.core.config import Settings
from creative.core.errors import is_transient, stage_failure
from creative.core.events import ProgressEvent, ProgressHandler
from creative.core.observability import span
from creative.core.schemas import (
    CandidatePool,
    Framework,
    FrameworkPool,
    ModelCall,
    StageTrace,
    Workflow,
    pool_output_type,
)

logger = logging.getLogger("creative")
request_parameters_adapter = TypeAdapter(ModelRequestParameters)


@dataclass
class CallScope:
    attempts: int = 0
    stage: str = "unknown"
    on_progress: ProgressHandler | None = None
    capture_prompts: bool = False
    model_calls: list[ModelCall] = field(default_factory=list)

    def emit(self, event: ProgressEvent) -> None:
        if self.on_progress is not None:
            self.on_progress(event)


@dataclass(frozen=True)
class RunDependencies:
    candidate_count: int
    framework: Framework | None = None


call_scope: ContextVar[CallScope] = ContextVar("creative_call_scope")
generation_id: ContextVar[str] = ContextVar("creative_generation_id", default="unknown")


def instructions_for(role: str):
    def instructions(ctx: RunContext[RunDependencies]) -> str:
        return prompts.render(role, ctx.deps.candidate_count)

    return instructions


class LimitedModel(WrapperModel):
    def __init__(self, wrapped: Model, settings: Settings, semaphore: asyncio.Semaphore):
        super().__init__(wrapped)
        self.limits = settings
        self.semaphore = semaphore

    async def request(
        self,
        messages: list[ModelMessage],
        model_settings: ModelSettings | None,
        model_request_parameters: ModelRequestParameters,
    ) -> ModelResponse:
        scope = call_scope.get()
        for attempt in range(self.limits.transient_retries + 1):
            started = monotonic()
            try:
                return await self._request_once(
                    messages, model_settings, model_request_parameters, scope
                )
            except (ModelAPIError, TimeoutError) as error:
                if not is_transient(error) or attempt == self.limits.transient_retries:
                    raise
                retry_after = getattr(error, "retry_after", None)
                delay = max(0.0, retry_after) if retry_after is not None else 2**attempt
                delay += random.uniform(0, 0.25)
                scope.emit(
                    ProgressEvent(
                        scope.stage,
                        "retrying",
                        attempt=scope.attempts,
                        elapsed_seconds=monotonic() - started,
                        timeout_seconds=self.limits.call_timeout_seconds,
                        retry_delay_seconds=delay,
                        error_type=type(error).__name__,
                    )
                )
                # Whole-generation timeout remains authoritative, even for long Retry-After.
                await asyncio.sleep(delay)
        raise AssertionError("Unreachable")

    async def _request_once(
        self,
        messages: list[ModelMessage],
        model_settings: ModelSettings | None,
        model_request_parameters: ModelRequestParameters,
        scope: CallScope,
    ) -> ModelResponse:
        # Backoff and semaphore waits do not consume provider-call timeout or slots.
        async with self.semaphore:
            scope.attempts += 1
            if scope.capture_prompts:
                scope.model_calls.append(
                    ModelCall(
                        attempt=scope.attempts,
                        messages=ModelMessagesTypeAdapter.dump_python(messages, mode="json"),
                        request_parameters=request_parameters_adapter.dump_python(
                            model_request_parameters, mode="json"
                        ),
                        model_settings=dict(model_settings) if model_settings else None,
                    )
                )
            scope.emit(
                ProgressEvent(
                    scope.stage,
                    "attempt",
                    attempt=scope.attempts,
                    timeout_seconds=self.limits.call_timeout_seconds,
                )
            )
            with span(
                "provider attempt",
                stage=scope.stage,
                attempt=scope.attempts,
                model=self.model_id,
                timeout_seconds=self.limits.call_timeout_seconds,
            ):
                async with asyncio.timeout(self.limits.call_timeout_seconds):
                    return await self.wrapped.request(
                        messages, model_settings, model_request_parameters
                    )


class LLM:
    def __init__(self, settings: Settings, models: dict[str, Model] | None = None):
        self.settings = settings
        self.model_names = settings.models()
        self.global_semaphore = asyncio.Semaphore(settings.max_llm_calls)
        self.stack = AsyncExitStack()
        resolved: dict[str, Model] = {}
        self.models: dict[str, Model] = {}
        for role, name in self.model_names.items():
            if models is not None:
                model = models[role]
            else:
                if name not in resolved:
                    resolved[name] = self._resolve_model(name)
                model = resolved[name]
            self.models[role] = model

        specs = {
            "framework": FrameworkPool,
            "plan": Workflow,
            "candidates": CandidatePool,
            "writer": str,
        }
        self.agents: dict[str, Agent] = {}
        for role, output_type in specs.items():
            self.agents[role] = Agent(
                LimitedModel(self.models[role], settings, self.global_semaphore),
                output_type=output_type,
                instructions=instructions_for(role),
                deps_type=RunDependencies,
                retries={"output": 1, "tools": 0},
                model_settings=self._model_settings(role),
                name=f"creative_{role}",
            )

        @self.agents["plan"].output_validator
        def validate_mapping(ctx: RunContext[RunDependencies], output: Workflow) -> Workflow:
            assert ctx.deps.framework is not None
            try:
                output.validate_for(ctx.deps.framework)
            except ValueError as error:
                raise ModelRetry(str(error)) from error
            return output

        @self.agents["writer"].output_validator
        def nonempty(output: str) -> str:
            if not output.strip():
                raise ModelRetry("Return a nonempty finished deliverable")
            return output

    def _resolve_model(self, name: str) -> Model:
        if self.settings.ai_base_url:
            return OpenAIChatModel(
                name.split(":", 1)[1],
                provider=OpenAIProvider(
                    base_url=self.settings.ai_base_url, api_key=self.settings.ai_api_key
                ),
            )
        return infer_model(name, provider_factory=self._provider)

    def _provider(self, name: str):
        if name.startswith("gateway/"):
            return gateway_provider(
                name.removeprefix("gateway/"),
                api_key=self.settings.pydantic_ai_gateway_api_key,
                base_url=self.settings.pydantic_ai_gateway_base_url,
            )
        return infer_provider(name)

    def _model_settings(self, role: str) -> ModelSettings:
        settings: ModelSettings = {
            "max_retries": 0,
            "timeout": self.settings.call_timeout_seconds,
        }
        model = self.models[role]
        if model.model_name == "gpt-6-luna":
            if isinstance(model, OpenAIResponsesModel):
                settings["openai_reasoning_effort"] = "low"
            elif isinstance(model, OpenAIChatModel):
                # Luna Chat Completions function calling requires reasoning disabled.
                settings["openai_reasoning_effort"] = "none"
        return settings

    async def __aenter__(self):
        try:
            # Same model object may power several roles; enter/close it exactly once.
            for model in {id(m): m for m in self.models.values()}.values():
                await self.stack.enter_async_context(model)
        except BaseException:
            await self.stack.aclose()
            raise
        return self

    async def __aexit__(self, *exc):
        await self.stack.aclose()

    async def run(
        self,
        role: str,
        payload: dict[str, Any],
        trace: list[StageTrace],
        stage: str,
        framework: Framework | None = None,
        *,
        candidate_count: int | None = None,
        on_progress: ProgressHandler | None = None,
        capture_prompts: bool = False,
    ) -> Any:
        """Error/context boundary; _run_agent contains the normal successful path."""
        scope = CallScope(stage=stage, on_progress=on_progress, capture_prompts=capture_prompts)
        started = monotonic()
        token = call_scope.set(scope)
        deps = RunDependencies(
            candidate_count if candidate_count is not None else self.settings.candidate_count,
            framework,
        )
        try:
            return await self._run_agent(role, payload, deps, scope, trace, stage)
        except (UnexpectedModelBehavior, ModelAPIError, TimeoutError) as error:
            raise stage_failure(
                error,
                stage,
                attempts=scope.attempts,
                timeout_seconds=self.settings.call_timeout_seconds,
                elapsed_seconds=round(monotonic() - started, 4),
                error_type=type(error).__name__,
            ) from error
        finally:
            call_scope.reset(token)

    async def _run_agent(
        self,
        role: str,
        payload: dict[str, Any],
        deps: RunDependencies,
        scope: CallScope,
        trace: list[StageTrace],
        stage: str,
    ) -> Any:
        started = monotonic()
        options = (
            {"output_type": pool_output_type(role, deps.candidate_count)}
            if role in {"framework", "candidates"}
            else {}
        )
        result = await self.agents[role].run(
            json.dumps(payload, ensure_ascii=False), deps=deps, **options
        )
        usage = result.usage
        entry = StageTrace(
            stage=stage,
            model=self.models[role].model_id,
            elapsed_seconds=round(monotonic() - started, 4),
            requests=scope.attempts,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            model_calls=scope.model_calls if scope.capture_prompts else None,
        )
        trace.append(entry)
        logger.info(
            "stage_complete request_id=%s %s",
            generation_id.get(),
            entry.model_dump_json(exclude={"model_calls"}),
        )
        return result.output
