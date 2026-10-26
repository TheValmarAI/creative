import asyncio
import json
import logging
from copy import deepcopy

import pytest
from pydantic import ValidationError
from pydantic_ai.exceptions import ModelHTTPError

from creative.core.engine import Engine
from creative.core.errors import GenerationFailure
from creative.core.schemas import GenerateRequest, GenerateResponse, Workflow, pool_output_type


async def test_framework_first_selection_propagation_and_context(scripted, settings):
    async with scripted.llm() as llm:
        engine = Engine(llm, settings, selector=lambda n: 7)
        result = await engine.generate(GenerateRequest(prompt="Plot of a story about a bear"))
    assert [role for role, _ in scripted.calls[:2]] == ["framework", "plan"]
    planner = scripted.calls[1][1]
    assert set(planner) == {"request", "framework"}
    assert planner["framework"]["name"] == "Approach 7"
    assert result.framework.selected_index == 7
    assert len(result.framework.candidates) == 20
    assert all(item.selected_index == 7 for item in result.selections)
    assert all(item.selected_value == item.candidates[7] for item in result.selections)
    payloads = {p["instructions"]: p for role, p in scripted.calls if role == "candidates"}
    assert payloads["emotion"]["selected_values"] == {}
    assert payloads["inspiration"] == {
        "instructions": "inspiration",
        "cue": "ordinary physical processes",
    }
    assert payloads["world"]["selected_values"] == {"emotion": "emotion: alternative 7"}
    assert payloads["cast_size"]["selected_values"] == {
        "emotion": "emotion: alternative 7",
        "world": "world: alternative 7",
        "inspiration": "inspiration: alternative 7",
    }
    assert payloads["cast"]["selected_values"] == {
        **payloads["cast_size"]["selected_values"],
        "cast_size": "3 characters, configuration 7",
    }
    assert set(payloads["outline"]["selected_values"]) == {
        "emotion",
        "world",
        "inspiration",
        "cast_size",
        "cast",
    }
    writer = next(p for role, p in scripted.calls if role == "writer")
    assert writer["selected_values"] == {s.node_id: s.selected_value for s in result.selections}
    assert writer["workflow"] == result.workflow.model_dump()
    assert all("candidates" not in node for node in writer["workflow"]["nodes"])
    for position, node in enumerate(result.workflow.nodes, start=1):
        payload = payloads[node.instructions]
        assert list(payload)[-1] == "instructions"
        if not node.isolated_context:
            assert payload["framework"] == planner["framework"]
            assert payload["request"] == "Plot of a story about a bear"
            assert payload["node"] == {
                "id": node.id,
                "position": position,
                "total_nodes": len(result.workflow.nodes),
                "purpose": node.purpose,
                "rationale": node.rationale,
            }
    assert len(result.trace) == 9
    assert result.input_tokens >= 80
    assert all(entry.requests == 1 for entry in result.trace)


async def test_candidates_can_be_omitted(scripted, settings):
    async with scripted.llm() as llm:
        result = await Engine(llm, settings).generate(
            GenerateRequest(prompt="bear", include_candidates=False)
        )
    assert result.framework.candidates is None
    assert all(item.candidates is None for item in result.selections)
    assert all(entry.model_calls is None for entry in result.trace)


async def test_prompt_capture_records_actual_inputs_and_keeps_them_out_of_logs(
    scripted, settings, caplog
):
    brief = "private-captured-brief-unique"
    with caplog.at_level(logging.INFO, logger="creative.core.llm"):
        async with scripted.llm() as llm:
            result = await Engine(llm, settings, selector=lambda n: 1).generate(
                GenerateRequest(prompt=brief, candidate_count=3), capture_prompts=True
            )
    for entry, (role, payload), (_, instructions) in zip(
        result.trace, scripted.calls, scripted.instructions, strict=True
    ):
        assert len(entry.model_calls) == 1
        call = entry.model_calls[0]
        assert instructions in [
            part["content"] for part in call.request_parameters["instruction_parts"]
        ]
        user = next(
            part["content"]
            for message in call.messages
            for part in message["parts"]
            if part["part_kind"] == "user-prompt"
        )
        assert json.loads(user) == payload
        if role in {"framework", "candidates"}:
            schema = call.request_parameters["output_tools"][0]["parameters_json_schema"]
            assert schema["properties"]["candidates"]["maxItems"] == 3
        if payload.get("instructions") == "inspiration":
            assert set(json.loads(user)) == {"instructions", "cue"}
    assert brief not in caplog.text
    assert GenerateResponse.model_validate_json(result.model_dump_json()) == result


async def test_prompt_capture_keeps_correction_history(scripted, settings):
    def transform(role, payload, data):
        if role == "candidates" and scripted.counts[payload["instructions"]] == 1:
            data["candidates"] = ["duplicate"] * 3
        return data

    scripted.transform = transform
    async with scripted.llm() as llm:
        result = await Engine(llm, settings).generate(
            GenerateRequest(prompt="bear", candidate_count=3), capture_prompts=True
        )
    node = next(entry for entry in result.trace if entry.stage == "node:emotion")
    assert [call.attempt for call in node.model_calls] == [1, 2]
    assert any(
        part["part_kind"] == "tool-return" and part.get("retry")
        for message in node.model_calls[1].messages
        for part in message["parts"]
    )


async def test_nodes_run_as_one_ordered_chain_even_when_isolated(scripted, settings):
    first_started = asyncio.Event()
    release_first = asyncio.Event()
    order = []

    async def hook(role, payload):
        if role != "candidates":
            return
        order.append(payload["instructions"])
        if payload["instructions"] == "emotion":
            first_started.set()
            await release_first.wait()
        await asyncio.sleep(0)

    scripted.hook = hook
    async with scripted.llm() as llm:
        task = asyncio.create_task(Engine(llm, settings).generate(GenerateRequest(prompt="bear")))
        try:
            await asyncio.wait_for(first_started.wait(), 2)
            await asyncio.sleep(0)
            assert order == ["emotion"]
            assert scripted.active == 1
        finally:
            release_first.set()
            await asyncio.wait_for(task, 2)
    assert order == [node.id for node in scripted.workflow.nodes]
    assert scripted.peak == 1


async def test_global_call_limit_and_request_isolation(scripted, settings):
    settings.max_llm_calls = 3

    async def hook(role, payload):
        await asyncio.sleep(0.005)

    scripted.hook = hook
    async with scripted.llm() as llm:
        engine = Engine(llm, settings)
        results = await asyncio.gather(
            *[engine.generate(GenerateRequest(prompt=f"brief-{i}")) for i in range(3)]
        )
    assert scripted.peak == 3
    assert len({result.request_id for result in results}) == 3
    assert [r.output for r in results] == [f"Finished: brief-{i}" for i in range(3)]
    for role, payload in scripted.calls:
        if role == "writer":
            assert payload["request"] in {"brief-0", "brief-1", "brief-2"}


async def test_mapping_correction_is_bounded(scripted, settings):
    def transform(role, payload, data):
        if role == "plan" and scripted.counts["plan"] == 1:
            data["framework_mapping"][0]["component"] = "invented obligation"
        return data

    scripted.transform = transform
    async with scripted.llm() as llm:
        await Engine(llm, settings).generate(GenerateRequest(prompt="bear"))
    assert scripted.counts["plan"] == 2


async def test_invalid_candidates_correct_once_then_fail(scripted, settings):
    def transform(role, payload, data):
        if role == "candidates":
            data["candidates"] = ["duplicate"] * 20
        return data

    scripted.transform = transform
    async with scripted.llm() as llm:
        with pytest.raises(GenerationFailure) as caught:
            await Engine(llm, settings).generate(GenerateRequest(prompt="bear"))
    assert caught.value.detail.code == "invalid_model_output"
    assert not caught.value.detail.retryable
    assert not any(role == "writer" for role, _ in scripted.calls)
    assert max(scripted.counts[k] for k in ("emotion", "world", "inspiration")) <= 2


async def test_transient_retry_respects_retry_after(scripted, settings, monkeypatch):
    waits = []

    async def record_sleep(delay):
        waits.append(delay)

    monkeypatch.setattr("creative.core.llm.asyncio.sleep", record_sleep)

    async def hook(role, payload):
        if role == "framework" and scripted.counts["framework"] < 3:
            raise ModelHTTPError(429, "test", headers={"Retry-After": "2"})

    scripted.hook = hook
    async with scripted.llm() as llm:
        result = await Engine(llm, settings).generate(GenerateRequest(prompt="bear"))
    assert scripted.counts["framework"] == 3
    assert len(waits) == 2 and all(2 <= delay <= 2.25 for delay in waits)
    assert result.trace[0].requests == 3


async def test_nontransient_error_does_not_retry_or_expose_provider_body(scripted, settings):
    async def hook(role, payload):
        raise ModelHTTPError(401, "test", body="sensitive provider data")

    scripted.hook = hook
    async with scripted.llm() as llm:
        with pytest.raises(GenerationFailure) as caught:
            await Engine(llm, settings).generate(GenerateRequest(prompt="secret brief"))
    assert scripted.counts["framework"] == 1
    assert caught.value.detail.stage == "framework"
    assert not caught.value.detail.retryable
    assert "sensitive" not in caught.value.detail.model_dump_json()


@pytest.mark.parametrize("overall", [True, False])
async def test_deadlines_cancel_provider_and_release_admission(scripted, settings, overall):
    settings.transient_retries = 0
    if overall:
        settings.generation_timeout_seconds = 0.02
    else:
        settings.call_timeout_seconds = 0.02

    async def hook(role, payload):
        await asyncio.Event().wait()

    scripted.hook = hook
    async with scripted.llm() as llm:
        engine = Engine(llm, settings)
        with pytest.raises(GenerationFailure) as caught:
            await engine.generate(GenerateRequest(prompt="bear"))
        assert engine.active == 0 and not engine.tasks
    assert caught.value.detail.code == ("generation_timeout" if overall else "provider_timeout")
    assert scripted.cancelled == 1


async def test_busy_and_explicit_cancellation(scripted, settings):
    settings.max_generations = 1
    started = asyncio.Event()

    async def hook(role, payload):
        started.set()
        await asyncio.Event().wait()

    scripted.hook = hook
    async with scripted.llm() as llm:
        engine = Engine(llm, settings)
        task = asyncio.create_task(engine.generate(GenerateRequest(prompt="first")))
        await started.wait()
        with pytest.raises(GenerationFailure) as caught:
            await engine.generate(GenerateRequest(prompt="second"))
        assert caught.value.status_code == 429
        await engine.close()
        assert task.cancelled() and engine.active == 0
    assert scripted.cancelled == 1


@pytest.mark.parametrize(
    "mutation", ["duplicate", "removed_dependencies", "removed_context", "mapping", "too_many"]
)
def test_invalid_ordered_workflows(workflow, mutation):
    data = deepcopy(workflow.model_dump())
    if mutation == "duplicate":
        data["nodes"][1]["id"] = "emotion"
    elif mutation == "mapping":
        data["framework_mapping"][0]["node_ids"] = ["unknown"]
    elif mutation == "removed_dependencies":
        data["nodes"][0]["dependencies"] = ["world"]
    elif mutation == "removed_context":
        data["nodes"][0]["context"] = "restricted"
    elif mutation == "too_many":
        data["nodes"] = [dict(data["nodes"][0], id=f"node_{i}") for i in range(24)]
    with pytest.raises(ValidationError):
        Workflow.model_validate(data)


def test_pool_requires_twenty_distinct_nonempty_candidates():
    for values in (["x"] * 20, [str(i) for i in range(19)], [" "] + [str(i) for i in range(19)]):
        with pytest.raises(ValidationError):
            pool_output_type("candidates", 20)(candidates=values)


async def test_transient_retries_exhaust_after_three_attempts(scripted, settings, monkeypatch):
    async def no_wait(delay):
        pass

    monkeypatch.setattr("creative.core.llm.asyncio.sleep", no_wait)

    async def hook(role, payload):
        raise ModelHTTPError(503, "test")

    scripted.hook = hook
    async with scripted.llm() as llm:
        with pytest.raises(GenerationFailure) as caught:
            await Engine(llm, settings).generate(GenerateRequest(prompt="bear"))
    assert scripted.counts["framework"] == 3
    assert caught.value.detail.retryable


async def test_invalid_framework_mapping_fails_after_one_correction(scripted, settings):
    def transform(role, payload, data):
        if role == "plan":
            data["framework_mapping"][0]["component"] = "wrong component"
        return data

    scripted.transform = transform
    async with scripted.llm() as llm:
        with pytest.raises(GenerationFailure) as caught:
            await Engine(llm, settings).generate(GenerateRequest(prompt="bear"))
    assert scripted.counts["plan"] == 2
    assert caught.value.detail.code == "invalid_model_output"
    assert not any(role == "candidates" for role, _ in scripted.calls)


async def test_node_failure_stops_the_chain_and_skips_writer(scripted, settings):
    async def hook(role, payload):
        if payload.get("instructions") == "world":
            raise ModelHTTPError(400, "test")

    scripted.hook = hook
    async with scripted.llm() as llm:
        with pytest.raises(GenerationFailure) as caught:
            await Engine(llm, settings).generate(GenerateRequest(prompt="bear"))
    assert caught.value.detail.stage == "node:world"
    assert [p["instructions"] for role, p in scripted.calls if role == "candidates"] == [
        "emotion",
        "world",
    ]
    assert not any(role == "writer" for role, _ in scripted.calls)


async def test_cancellation_during_node_stops_remaining_chain(scripted, settings):
    started = asyncio.Event()

    async def hook(role, payload):
        if payload.get("instructions") == "world":
            started.set()
            await asyncio.Event().wait()

    scripted.hook = hook
    async with scripted.llm() as llm:
        engine = Engine(llm, settings)
        task = asyncio.create_task(engine.generate(GenerateRequest(prompt="bear")))
        await asyncio.wait_for(started.wait(), 2)
        await engine.close()
        assert task.cancelled() and engine.active == 0
    assert scripted.cancelled == 1
    assert not any(role == "writer" for role, _ in scripted.calls)


@pytest.mark.parametrize("isolated,cue", [(True, None), (False, "neutral cue")])
def test_isolated_context_requires_exactly_its_own_cue(workflow, isolated, cue):
    data = workflow.model_dump()
    data["nodes"][0].update(isolated_context=isolated, cue=cue)
    with pytest.raises(ValidationError):
        Workflow.model_validate(data)
