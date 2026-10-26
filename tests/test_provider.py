import json

import httpx2
import pytest
from pydantic_ai import models
from pydantic_ai.providers.openai import OpenAIProvider

from creative.core.errors import StageFailure
from creative.core.llm import LLM


async def test_custom_endpoint_uses_chat_completions_and_role_models(
    settings, framework, monkeypatch
):
    settings.ai_model = "openai-chat:generator-model"
    settings.planner_model = "openai-chat:planner-model"
    settings.writer_model = "openai-chat:writer-model"
    settings.ai_base_url = "https://provider.example/v1"
    settings.ai_api_key = "test-provider-key"
    settings.transient_retries = 0
    settings.candidate_count = 6
    requests = []

    def handler(request):
        requests.append(request)
        body = json.loads(request.content)
        tool_name = body["tools"][0]["function"]["name"]
        pool = {
            "candidates": [
                framework.model_copy(update={"name": f"Approach {i}"}).model_dump()
                for i in range(settings.candidate_count)
            ]
        }
        return httpx2.Response(
            200,
            json={
                "id": "chatcmpl-test",
                "object": "chat.completion",
                "created": 0,
                "model": body["model"],
                "choices": [
                    {
                        "index": 0,
                        "finish_reason": "tool_calls",
                        "message": {
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [
                                {
                                    "id": "call-test",
                                    "type": "function",
                                    "function": {
                                        "name": tool_name,
                                        "arguments": json.dumps(pool),
                                    },
                                }
                            ],
                        },
                    }
                ],
                "usage": {"prompt_tokens": 100, "completion_tokens": 200, "total_tokens": 300},
            },
        )

    async with httpx2.AsyncClient(transport=httpx2.MockTransport(handler)) as client:
        monkeypatch.setattr(
            "creative.core.llm.OpenAIProvider",
            lambda **kwargs: OpenAIProvider(**kwargs, http_client=client),
        )
        # This test exercises the real SDK adapter against an in-memory HTTP transport.
        monkeypatch.setattr(models, "ALLOW_MODEL_REQUESTS", True)
        async with LLM(settings) as llm:
            assert llm.models["framework"] is llm.models["plan"]
            assert llm.models["writer"].model_name == "writer-model"
            assert llm.models["candidates"].model_name == "generator-model"
            trace = []
            output = await llm.run("framework", {"request": "bear"}, trace, "framework")
    assert len(output.candidates) == 6
    assert len(requests) == 1
    assert requests[0].url.path == "/v1/chat/completions"
    assert requests[0].headers["authorization"] == "Bearer test-provider-key"
    assert json.loads(requests[0].content)["model"] == "planner-model"
    body = json.loads(requests[0].content)
    assert "exactly 6" in json.dumps(body["messages"])
    pool_schema = body["tools"][0]["function"]["parameters"]["properties"]["candidates"]
    assert pool_schema["minItems"] == pool_schema["maxItems"] == 6
    assert trace[0].input_tokens == 100
    assert trace[0].output_tokens == 200


async def test_sdk_retries_are_disabled(settings, monkeypatch):
    settings.ai_model = "openai-chat:example"
    settings.ai_base_url = "https://provider.example/v1"
    settings.ai_api_key = "test-provider-key"
    settings.transient_retries = 0
    requests = []

    def handler(request):
        requests.append(request)
        return httpx2.Response(503, json={"error": {"message": "temporarily unavailable"}})

    async with httpx2.AsyncClient(transport=httpx2.MockTransport(handler)) as client:
        monkeypatch.setattr(
            "creative.core.llm.OpenAIProvider",
            lambda **kwargs: OpenAIProvider(**kwargs, http_client=client),
        )
        monkeypatch.setattr(models, "ALLOW_MODEL_REQUESTS", True)
        async with LLM(settings) as llm:
            with pytest.raises(StageFailure) as caught:
                await llm.run("framework", {"request": "bear"}, [], "framework")
    assert len(requests) == 1
    assert caught.value.retryable
