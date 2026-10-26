import json

import httpx2
import pytest
from pydantic_ai import models
from pydantic_ai.models.openai import OpenAIChatModel, OpenAIResponsesModel
from pydantic_ai.providers.gateway import gateway_provider

from creative.core.config import Settings
from creative.core.errors import StageFailure
from creative.core.llm import LLM


def test_default_is_gateway_luna_and_key_loads_from_dotenv(tmp_path, monkeypatch):
    monkeypatch.delenv("PYDANTIC_AI_GATEWAY_API_KEY", raising=False)
    monkeypatch.delenv("PYDANTIC_AI_GATEWAY_BASE_URL", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text(
        "PYDANTIC_AI_GATEWAY_API_KEY=test-gateway-key\n"
        "PYDANTIC_AI_GATEWAY_BASE_URL=https://gateway-eu.pydantic.dev/proxy\n",
        encoding="utf-8",
    )
    settings = Settings(_env_file=env_file)
    assert set(settings.models().values()) == {"gateway/openai-responses:gpt-6-luna"}
    assert settings.pydantic_ai_gateway_api_key == "test-gateway-key"
    assert "test-gateway-key" not in repr(settings)


@pytest.mark.parametrize("error_response", [False, True])
async def test_gateway_responses_uses_loaded_key_and_preserves_typed_output(
    framework, tmp_path, monkeypatch, error_response
):
    for name in ("PYDANTIC_AI_GATEWAY_API_KEY", "PYDANTIC_AI_GATEWAY_BASE_URL", "OPENAI_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text(
        "PYDANTIC_AI_GATEWAY_API_KEY=test-gateway-key\n"
        "PYDANTIC_AI_GATEWAY_BASE_URL=https://gateway-eu.pydantic.dev/proxy\n"
        "CANDIDATE_COUNT=3\nTRANSIENT_RETRIES=0\n",
        encoding="utf-8",
    )
    settings = Settings(_env_file=env_file)
    requests = []

    def handler(request):
        requests.append(request)
        if error_response:
            return httpx2.Response(401, json={"error": {"message": "invalid gateway key"}})
        body = json.loads(request.content)
        pool = {
            "candidates": [
                framework.model_copy(update={"name": f"Approach {i}"}).model_dump()
                for i in range(settings.candidate_count)
            ]
        }
        return httpx2.Response(
            200,
            json={
                "id": "resp_test",
                "object": "response",
                "created_at": 0,
                "status": "completed",
                "model": body["model"],
                "output": [
                    {
                        "type": "function_call",
                        "id": "fc_test",
                        "call_id": "call_test",
                        "name": body["tools"][0]["name"],
                        "arguments": json.dumps(pool),
                        "status": "completed",
                    }
                ],
                "usage": {"input_tokens": 100, "output_tokens": 200, "total_tokens": 300},
            },
        )

    async with httpx2.AsyncClient(transport=httpx2.MockTransport(handler)) as client:
        monkeypatch.setattr(
            "creative.core.llm.gateway_provider",
            lambda upstream, **kwargs: gateway_provider(upstream, **kwargs, http_client=client),
        )
        monkeypatch.setattr(models, "ALLOW_MODEL_REQUESTS", True)
        async with LLM(settings) as llm:
            assert isinstance(llm.models["framework"], OpenAIResponsesModel)
            assert len({id(model) for model in llm.models.values()}) == 1
            trace = []
            if error_response:
                with pytest.raises(StageFailure) as caught:
                    await llm.run("framework", {"request": "bear"}, trace, "framework")
                assert caught.value.code == "provider_error"
                assert not caught.value.retryable
            else:
                result = await llm.run("framework", {"request": "bear"}, trace, "framework")
                assert len(result.candidates) == 3
                assert trace[0].input_tokens == 100
    assert len(requests) == 1
    assert requests[0].url.host == "gateway-eu.pydantic.dev"
    assert requests[0].url.path == "/proxy/openai/responses"
    assert requests[0].headers["authorization"] == "Bearer test-gateway-key"
    body = json.loads(requests[0].content)
    assert body["model"] == "gpt-6-luna"
    assert body["reasoning"]["effort"] == "low"
    assert "exactly 3" in body["instructions"]
    schema = body["tools"][0]["parameters"]["properties"]["candidates"]
    assert schema["minItems"] == schema["maxItems"] == 3


async def test_gateway_luna_chat_override_disables_reasoning_for_function_calling():
    settings = Settings(
        _env_file=None,
        ai_model="gateway/openai-responses:gpt-6-luna",
        generator_model="gateway/openai-chat:gpt-6-luna",
        pydantic_ai_gateway_api_key="test-key",
        pydantic_ai_gateway_base_url="https://gateway-eu.pydantic.dev/proxy",
    )
    async with LLM(settings) as llm:
        assert isinstance(llm.models["candidates"], OpenAIChatModel)
        assert llm._model_settings("candidates")["openai_reasoning_effort"] == "none"
        assert llm._model_settings("plan")["openai_reasoning_effort"] == "low"
