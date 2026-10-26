import asyncio
from unittest.mock import Mock

import logfire
import pytest
from pydantic_ai import Agent
from pydantic_ai.exceptions import ModelHTTPError

from creative.core import observability
from creative.core.config import Settings
from creative.core.engine import Engine
from creative.core.errors import GenerationFailure
from creative.core.schemas import GenerateRequest
from creative.interfaces import cli


def test_logfire_setup_reads_dotenv_key_and_instruments_agents(tmp_path, monkeypatch):
    monkeypatch.delenv("LOGFIRE_TOKEN", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text("LOGFIRE_TOKEN=test-logfire-write-token\n", encoding="utf-8")
    settings = Settings(_env_file=env_file)
    configure = Mock()
    instrument = Mock()
    monkeypatch.setattr(observability, "_configured", False)
    monkeypatch.setattr(observability.logfire, "configure", configure)
    monkeypatch.setattr(observability.logfire, "instrument_pydantic_ai", instrument)
    observability.configure(settings, console=True)
    observability.configure(settings, console=True)
    assert configure.call_count == instrument.call_count == 1
    assert configure.call_args.kwargs["token"] == "test-logfire-write-token"
    assert configure.call_args.kwargs["send_to_logfire"] == "if-token-present"
    assert configure.call_args.kwargs["console"].output is not None
    instrument.assert_called_once_with(include_content=False)
    assert "test-logfire-write-token" not in repr(settings)


def test_logfire_can_be_disabled(settings, monkeypatch):
    configure = Mock()
    monkeypatch.setattr(observability.logfire, "configure", configure)
    observability.configure(settings)
    configure.assert_not_called()


async def test_native_agent_spans_and_attempts_share_generation_trace(
    capfire, scripted, settings, monkeypatch
):
    monkeypatch.setattr(observability, "_configured", True)
    logfire.instrument_pydantic_ai(include_content=False)
    try:
        async with scripted.llm() as llm:
            result = await Engine(llm, settings).generate(
                GenerateRequest(prompt="private creative brief", candidate_count=3)
            )
        spans = [
            s
            for s in capfire.exporter.exported_spans
            if s.attributes.get("logfire.span_type") != "pending_span"
        ]
        roots = [s for s in spans if s.name == "creative generation"]
        assert len(roots) == 1
        assert roots[0].attributes["request_id"] == result.request_id
        assert len([s for s in spans if s.name == "provider attempt"]) == 9
        assert any(s.attributes.get("gen_ai.operation.name") == "chat" for s in spans)
        assert len({s.context.trace_id for s in spans}) == 1
        assert "private creative brief" not in str([s.attributes for s in spans])
    finally:
        Agent.instrument_all(False)


async def test_timeout_reports_attempts_and_visible_retry_progress(scripted, settings, monkeypatch):
    settings.call_timeout_seconds = 0.01

    async def block(role, payload):
        await asyncio.Event().wait()

    async def no_wait(delay):
        pass

    scripted.hook = block
    monkeypatch.setattr("creative.core.llm.asyncio.sleep", no_wait)
    events = []
    async with scripted.llm() as llm:
        with pytest.raises(GenerationFailure) as caught:
            await Engine(llm, settings).generate(
                GenerateRequest(prompt="bear"), on_progress=events.append
            )
    detail = caught.value.detail
    assert detail.code == "provider_timeout"
    assert detail.attempts == 3
    assert detail.timeout_seconds == 0.01
    assert detail.elapsed_seconds >= 0.03
    assert detail.error_type == "TimeoutError"
    assert len([e for e in events if e.status == "attempt"]) == 3
    retries = [e for e in events if e.status == "retrying"]
    assert len(retries) == 2
    assert all(e.stage == "framework" and e.error_type == "TimeoutError" for e in retries)
    assert scripted.cancelled == 3


async def test_provider_budget_does_not_count_waiting_for_slot(scripted, settings):
    settings.max_llm_calls = 1
    settings.call_timeout_seconds = 0.01
    async with scripted.llm() as llm:
        await llm.global_semaphore.acquire()
        task = asyncio.create_task(Engine(llm, settings).generate(GenerateRequest(prompt="bear")))
        try:
            await asyncio.sleep(0.03)
            assert not scripted.calls
        finally:
            llm.global_semaphore.release()
        result = await task
    assert result.output == "Finished: bear"


def test_verbose_cli_shows_retry_reason_without_provider_body(
    scripted, settings, monkeypatch, capsys
):
    async def fail_once(role, payload):
        if role == "framework" and scripted.counts["framework"] == 1:
            raise ModelHTTPError(429, "test", body="sensitive upstream body", retry_after=0)

    scripted.hook = fail_once
    monkeypatch.setattr(cli, "Settings", lambda: settings)
    monkeypatch.setattr(cli, "LLM", lambda _: scripted.llm())
    cli.main(["bear", "--verbose", "--candidate-count", "3"])
    captured = capsys.readouterr()
    assert "Provider attempt 1; deadline 180s" in captured.err
    assert "[framework] retrying" in captured.err
    assert "ModelHTTPError" in captured.err
    assert "Provider attempt 2" in captured.err
    assert "sensitive upstream body" not in captured.err
    assert captured.out == "Finished: bear\n"
