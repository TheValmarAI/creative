import asyncio
import logging
import secrets
from collections.abc import Callable
from dataclasses import dataclass, field
from time import monotonic
from uuid import uuid4

from creative.core.config import Settings
from creative.core.errors import busy_failure, generation_failure
from creative.core.events import ProgressEvent, ProgressHandler
from creative.core.llm import LLM, generation_id
from creative.core.observability import span
from creative.core.schemas import (
    Framework,
    FrameworkSelection,
    GenerateRequest,
    GenerateResponse,
    Node,
    Selection,
    StageTrace,
    Workflow,
)

logger = logging.getLogger("creative")


@dataclass
class GenerationRun:
    request_id: str
    candidate_count: int
    started: float = field(default_factory=monotonic)
    trace: list[StageTrace] = field(default_factory=list)
    stage: str = "framework"
    on_progress: ProgressHandler | None = None
    capture_prompts: bool = False

    def emit(self, event: ProgressEvent) -> None:
        if self.on_progress is not None:
            self.on_progress(event)


def context_for(
    request: GenerateRequest,
    framework: Framework,
    node: Node,
    selections: dict[str, Selection],
    *,
    position: int,
    total_nodes: int,
) -> dict:
    # Do not serialize the whole plan, rationale, other nodes, pools, or conversation history.
    if node.isolated_context:
        return {"cue": node.cue, "instructions": node.instructions}
    return {
        "request": request.prompt,
        "node": {
            "id": node.id,
            "position": position,
            "total_nodes": total_nodes,
            "purpose": node.purpose,
            "rationale": node.rationale,
        },
        "framework": framework.model_dump(),
        "selected_values": {node_id: selections[node_id].selected_value for node_id in selections},
        "instructions": node.instructions,
    }


class Engine:
    def __init__(
        self, llm: LLM, settings: Settings, selector: Callable[[int], int] = secrets.randbelow
    ):
        self.llm = llm
        self.settings = settings
        self.selector = selector
        self.active = 0
        self.tasks: set[asyncio.Task] = set()

    async def close(self) -> None:
        tasks = list(self.tasks)
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

    async def generate(
        self,
        request: GenerateRequest,
        *,
        on_progress: ProgressHandler | None = None,
        capture_prompts: bool = False,
    ) -> GenerateResponse:
        """Admission, deadline and error boundary; see _generate for the creative workflow."""
        run = GenerationRun(
            request_id=str(uuid4()),
            candidate_count=(
                request.candidate_count
                if request.candidate_count is not None
                else self.settings.candidate_count
            ),
            on_progress=on_progress,
            capture_prompts=capture_prompts,
        )
        # No await between admission check and increment: atomic on this event loop.
        if self.active >= self.settings.max_generations:
            raise busy_failure(run.request_id)
        self.active += 1
        log_token = generation_id.set(run.request_id)
        task = asyncio.current_task()
        assert task is not None
        self.tasks.add(task)
        try:
            with span(
                "creative generation",
                request_id=run.request_id,
                candidate_count=run.candidate_count,
            ):
                async with asyncio.timeout(self.settings.generation_timeout_seconds):
                    return await self._generate(request, run)
        except Exception as error:
            failure = generation_failure(error, run.request_id, run.stage)
            logger.warning(
                "generation_failed request_id=%s stage=%s code=%s retryable=%s type=%s",
                run.request_id,
                failure.detail.stage,
                failure.detail.code,
                failure.detail.retryable,
                type(error).__name__,
            )
            raise failure from error
        finally:
            self.active -= 1
            self.tasks.discard(task)
            generation_id.reset(log_token)
            logger.info(
                "generation_finished request_id=%s elapsed=%.3f",
                run.request_id,
                monotonic() - run.started,
            )

    async def _generate(self, request: GenerateRequest, run: GenerationRun) -> GenerateResponse:
        """Framework → tailored plan → randomly selected components → finished output."""
        frameworks = await self._run_stage("framework", {"request": request.prompt}, run)
        framework_index = self.selector(len(frameworks.candidates))
        framework = frameworks.candidates[framework_index]
        run.emit(ProgressEvent("framework", "completed", frameworks, framework_index))
        workflow = await self._run_stage(
            "plan", {"request": request.prompt, "framework": framework.model_dump()}, run, framework
        )
        run.emit(ProgressEvent("plan", "completed", workflow))
        run.stage = "nodes"
        selections = await self._execute_nodes(request, framework, workflow, run)
        output = await self._run_stage(
            "writer",
            {
                "request": request.prompt,
                "framework": framework.model_dump(),
                "workflow": workflow.model_dump(),
                "selected_values": {item.node_id: item.selected_value for item in selections},
            },
            run,
        )
        run.emit(ProgressEvent("writer", "completed", output))
        return GenerateResponse(
            request_id=run.request_id,
            prompt=request.prompt,
            candidate_count=run.candidate_count,
            output=output,
            framework=FrameworkSelection(
                selected_index=framework_index,
                selected_value=framework,
                candidates=frameworks.candidates if request.include_candidates else None,
            ),
            workflow=workflow,
            selections=selections,
            trace=run.trace,
            elapsed_seconds=round(monotonic() - run.started, 4),
            input_tokens=sum(entry.input_tokens for entry in run.trace),
            output_tokens=sum(entry.output_tokens for entry in run.trace),
        )

    async def _run_stage(
        self, role: str, payload: dict, run: GenerationRun, framework: Framework | None = None
    ):
        run.stage = role
        run.emit(ProgressEvent(role, "started"))
        return await self.llm.run(
            role,
            payload,
            run.trace,
            role,
            framework,
            candidate_count=run.candidate_count,
            on_progress=run.on_progress,
            capture_prompts=run.capture_prompts,
        )

    async def _execute_nodes(
        self, request: GenerateRequest, framework: Framework, workflow: Workflow, run: GenerationRun
    ) -> list[Selection]:
        selections: dict[str, Selection] = {}
        # One fixed chain, including isolated nodes. Context isolation changes inputs,
        # not execution order. Separate requests still share the async provider limits.
        for position, node in enumerate(workflow.nodes, start=1):
            run.emit(ProgressEvent(f"node:{node.id}", "started"))
            pool = await self.llm.run(
                "candidates",
                context_for(
                    request,
                    framework,
                    node,
                    selections,
                    position=position,
                    total_nodes=len(workflow.nodes),
                ),
                run.trace,
                f"node:{node.id}",
                candidate_count=run.candidate_count,
                on_progress=run.on_progress,
                capture_prompts=run.capture_prompts,
            )
            index = self.selector(len(pool.candidates))
            selections[node.id] = Selection(
                node_id=node.id,
                selected_index=index,
                selected_value=pool.candidates[index],
                candidates=pool.candidates if request.include_candidates else None,
            )
            run.emit(ProgressEvent(f"node:{node.id}", "completed", pool, index))
        return [selections[node.id] for node in workflow.nodes]
