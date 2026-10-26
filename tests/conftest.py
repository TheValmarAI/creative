import asyncio
import json
from collections import Counter

import pytest
from pydantic_ai import models
from pydantic_ai.messages import ModelResponse, TextPart, ToolCallPart, UserPromptPart
from pydantic_ai.models.function import FunctionModel
from pydantic_ai.usage import RequestUsage

from creative.core.config import Settings
from creative.core.llm import LLM
from creative.core.schemas import Framework, Workflow


@pytest.fixture(autouse=True)
def no_paid_requests(monkeypatch):
    monkeypatch.setattr(models, "ALLOW_MODEL_REQUESTS", False)


@pytest.fixture
def settings():
    return Settings(
        _env_file=None, ai_model="test", api_token="test-secret-123456789", logfire_enabled=False
    )


@pytest.fixture
def framework():
    return Framework(
        name="Five-second transformation",
        origin="adapted",
        attribution="An adapted transformation story approach",
        organizing_principle="A brief realization changes behavior",
        required_components=["change", "contrast"],
        progression_rules=["Choose the contrast before scene details"],
        completion_criteria=["Show the change through action"],
    )


@pytest.fixture
def workflow():
    nodes = [
        {"id": "emotion", "instructions": "emotion"},
        {"id": "world", "instructions": "world"},
        {
            "id": "inspiration",
            "instructions": "inspiration",
            "isolated_context": True,
            "cue": "ordinary physical processes",
        },
        {
            "id": "cast_size",
            "instructions": "cast_size",
        },
        {
            "id": "cast",
            "instructions": "cast",
        },
        {"id": "outline", "instructions": "outline"},
    ]
    return Workflow.model_validate(
        {
            "nodes": [
                {"purpose": node["id"], "rationale": "Advance the framework", **node}
                for node in nodes
            ],
            "framework_mapping": [
                {"component": "change", "node_ids": ["outline"]},
                {"component": "contrast", "node_ids": ["emotion", "outline"]},
            ],
        }
    )


class ScriptedModels:
    """Real Pydantic AI FunctionModels; hooks simulate provider timing and responses."""

    def __init__(self, settings, framework, workflow):
        self.settings = settings
        self.framework = framework
        self.workflow = workflow
        self.calls = []
        self.instructions = []
        self.counts = Counter()
        self.hook = None
        self.transform = None
        self.active = 0
        self.peak = 0
        self.cancelled = 0
        self.models = {role: self.make_model(role) for role in settings.models()}

    def make_model(self, role):
        async def respond(messages, info):
            part = next(
                part
                for message in reversed(messages)
                for part in message.parts
                if isinstance(part, UserPromptPart)
            )
            payload = json.loads(part.content)
            label = payload.get("instructions", role)
            self.calls.append((role, payload))
            self.instructions.append((role, info.instructions))
            count = (
                info.output_tools[0].parameters_json_schema["properties"]["candidates"]["maxItems"]
                if role in {"framework", "candidates"}
                else None
            )
            self.counts[label] += 1
            self.active += 1
            self.peak = max(self.peak, self.active)
            try:
                if self.hook:
                    await self.hook(role, payload)
                if role == "framework":
                    data = {
                        "candidates": [
                            self.framework.model_copy(update={"name": f"Approach {i}"}).model_dump()
                            for i in range(count)
                        ]
                    }
                elif role == "plan":
                    data = self.workflow.model_dump()
                elif role == "candidates":
                    if label == "cast_size":
                        values = [f"3 characters, configuration {i}" for i in range(count)]
                    elif label == "cast":
                        values = [f"Ada, Bo, Cy; relationships {i}" for i in range(count)]
                    else:
                        values = [f"{label}: alternative {i}" for i in range(count)]
                    data = {"candidates": values}
                else:
                    return ModelResponse([TextPart(f"Finished: {payload['request']}")])
                if self.transform:
                    data = self.transform(role, payload, data)
                return ModelResponse(
                    [ToolCallPart(info.output_tools[0].name, data)],
                    usage=RequestUsage(input_tokens=10, output_tokens=20),
                )
            except asyncio.CancelledError:
                self.cancelled += 1
                raise
            finally:
                self.active -= 1

        return FunctionModel(respond, model_name=f"scripted-{role}")

    def llm(self):
        return LLM(self.settings, self.models)


@pytest.fixture
def scripted(settings, framework, workflow):
    return ScriptedModels(settings, framework, workflow)
