import asyncio

import pytest
from pydantic import ValidationError

from creative.core.config import Settings
from creative.core.engine import Engine
from creative.core.errors import GenerationFailure
from creative.core.schemas import GenerateRequest


def test_count_configuration_precedence(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("CANDIDATE_COUNT=7\n", encoding="utf-8")
    monkeypatch.delenv("CANDIDATE_COUNT", raising=False)
    assert Settings(_env_file=None).candidate_count == 20
    assert Settings(_env_file=env_file).candidate_count == 7
    monkeypatch.setenv("CANDIDATE_COUNT", "9")
    assert Settings(_env_file=env_file).candidate_count == 9


@pytest.mark.parametrize("count", [0, -1, 101, 1.5])
def test_invalid_counts_are_rejected(count):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, candidate_count=count)
    with pytest.raises(ValidationError):
        GenerateRequest(prompt="bear", candidate_count=count)


@pytest.mark.parametrize("count", [1, 3, 31, 100])
async def test_count_controls_prompts_pools_and_random_bounds(scripted, settings, count):
    settings.candidate_count = 7
    bounds = []

    def select_last(bound):
        bounds.append(bound)
        return bound - 1

    async with scripted.llm() as llm:
        result = await Engine(llm, settings, selector=select_last).generate(
            GenerateRequest(prompt="bear", candidate_count=count)
        )
    assert result.candidate_count == count
    assert len(result.framework.candidates) == count
    assert result.framework.selected_index == count - 1
    assert all(
        len(s.candidates) == count and s.selected_index == count - 1 for s in result.selections
    )
    assert bounds == [count] * (1 + len(result.selections))
    for role, instructions in scripted.instructions:
        assert "{candidate_count}" not in instructions
        assert "exactly 20" not in instructions
        if role in {"framework", "plan", "candidates"}:
            assert f"exactly {count}" in instructions


async def test_omitted_or_null_override_uses_server_default(scripted, settings):
    settings.candidate_count = 5
    async with scripted.llm() as llm:
        engine = Engine(llm, settings)
        for request in (
            GenerateRequest(prompt="bear"),
            GenerateRequest(prompt="bear", candidate_count=None),
        ):
            result = await engine.generate(request)
            assert result.candidate_count == 5
            assert len(result.framework.candidates) == 5
            assert all(len(s.candidates) == 5 for s in result.selections)


async def test_concurrent_overrides_do_not_change_shared_agents_or_defaults(scripted, settings):
    settings.candidate_count = 5

    async def overlap(role, payload):
        await asyncio.sleep(0.001)

    scripted.hook = overlap
    async with scripted.llm() as llm:
        engine = Engine(llm, settings)
        results = await asyncio.gather(
            *[
                engine.generate(GenerateRequest(prompt=f"brief-{count}", candidate_count=count))
                for count in (2, 7, None)
            ]
        )
    for result, count in zip(results, (2, 7, 5), strict=True):
        assert result.candidate_count == len(result.framework.candidates) == count
        assert all(len(s.candidates) == count for s in result.selections)
    assert settings.candidate_count == 5


@pytest.mark.parametrize("role", ["framework", "candidates"])
async def test_wrong_count_gets_one_correction(scripted, settings, role):
    def transform(current_role, payload, data):
        label = payload.get("instructions", current_role)
        if current_role == role and scripted.counts[label] == 1:
            data["candidates"].pop()
        return data

    scripted.transform = transform
    async with scripted.llm() as llm:
        result = await Engine(llm, settings).generate(
            GenerateRequest(prompt="bear", candidate_count=3)
        )
    assert len(result.framework.candidates) == 3
    assert all(len(s.candidates) == 3 for s in result.selections)
    corrected = [
        entry
        for entry in result.trace
        if entry.stage == role or role == "candidates" and entry.stage.startswith("node:")
    ]
    assert corrected and all(entry.requests == 2 for entry in corrected)


async def test_persistently_wrong_count_fails_without_selection(scripted, settings):
    def transform(role, payload, data):
        if role == "framework":
            data["candidates"].pop()
        return data

    scripted.transform = transform
    async with scripted.llm() as llm:
        with pytest.raises(GenerationFailure) as caught:
            await Engine(llm, settings).generate(GenerateRequest(prompt="bear", candidate_count=3))
    assert scripted.counts["framework"] == 2
    assert caught.value.detail.code == "invalid_model_output"
    assert not any(role == "plan" for role, _ in scripted.calls)
