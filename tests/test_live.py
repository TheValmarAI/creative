"""Paid, opt-in smoke test; does not claim to automate semantic creative-quality review."""

import asyncio
import os
from pathlib import Path

import pytest
from pydantic_ai import models

from creative.core.config import Settings
from creative.core.engine import Engine
from creative.core.llm import LLM
from creative.core.schemas import GenerateRequest


@pytest.mark.live
@pytest.mark.skipif(
    os.getenv("CREATIVE_LIVE") != "1", reason="Set CREATIVE_LIVE=1 to spend provider credits"
)
async def test_live_bear_story(monkeypatch):
    monkeypatch.setattr(models, "ALLOW_MODEL_REQUESTS", True)
    settings = Settings()
    async with LLM(settings) as llm:
        result = await Engine(llm, settings).generate(
            GenerateRequest(
                prompt=(
                    "Write the plot of a story about a bear. "
                    "Make details consequential, not decorative."
                )
            )
        )
    result.workflow.validate_for(result.framework.selected_value)
    assert len(result.framework.candidates) == result.candidate_count
    assert all(
        len(s.candidates) == result.candidate_count
        and s.selected_value == s.candidates[s.selected_index]
        for s in result.selections
    )
    assert result.output.strip()
    await asyncio.to_thread(
        Path("live-result.json").write_text, result.model_dump_json(indent=2), encoding="utf-8"
    )
