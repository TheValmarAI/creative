import json

from creative.core import prompts
from creative.core.schemas import ModelCall
from creative.interfaces.visualize import prompt_text


def test_prompt_display_uses_effective_instructions_once_and_preserves_context():
    instructions = "Unique system instructions for a creative decision."
    payload = {
        "request": "Write a water ad",
        "node": {"id": "hook", "position": 3, "total_nodes": 6},
        "selected_values": {"format": "TikTok, 12 seconds", "voice": "playful"},
        "instructions": "Generate the hooks for this node.",
    }
    call = ModelCall(
        attempt=1,
        messages=[
            {
                "instructions": instructions,
                "parts": [{"part_kind": "user-prompt", "content": json.dumps(payload)}],
            }
        ],
        request_parameters={"instruction_parts": [{"content": instructions}]},
        model_settings=None,
    )
    rendered = prompt_text(call)
    assert rendered.count(instructions) == 1
    for text in ["Write a water ad", "TikTok, 12 seconds", "playful", "hook"]:
        assert text in rendered
    assert "### position\n\n3" in rendered
    assert '"selected_values"' not in rendered
    assert "# UserPrompt\n" in rendered
    assert "## request from user\n" in rendered
    assert "## selected values from previous nodes\n" in rendered
    assert rendered.endswith("## instructions for this node\n\nGenerate the hooks for this node.")


def test_prompt_sections_are_ordered_without_repeated_instruction_header():
    call = ModelCall(
        attempt=1,
        messages=[{"parts": [{"part_kind": "user-prompt", "content": "Current request"}]}],
        request_parameters={"instruction_parts": [{"content": prompts.render("candidates", 5)}]},
        model_settings=None,
    )
    rendered = prompt_text(call)
    assert rendered.count("# Instructions\n") == 1
    assert rendered.index("# Instructions\n") < rendered.index("# Examples\n")
    assert rendered.index("# Examples\n") < rendered.index("# UserPrompt\n")


def test_prompt_display_keeps_retry_history_with_one_current_instruction_source():
    call = ModelCall(
        attempt=2,
        messages=[
            {
                "instructions": "Earlier instructions",
                "parts": [{"part_kind": "user-prompt", "content": "Original input"}],
            },
            {
                "instructions": "Effective instructions",
                "parts": [{"part_kind": "tool-return", "content": "Candidates must be distinct"}],
            },
        ],
        request_parameters={},
        model_settings=None,
    )
    rendered = prompt_text(call)
    assert "Effective instructions" in rendered
    assert "Earlier instructions" not in rendered
    assert "Original input" in rendered
    assert "Candidates must be distinct" in rendered
