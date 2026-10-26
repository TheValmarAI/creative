"""Ensure literal structured demonstrations teach valid outputs, not malformed JSON."""

import json
import re

from creative.core import prompt_examples, prompts
from creative.core.schemas import Node, pool_output_type


def json_examples(text):
    decoder = json.JSONDecoder()
    return [decoder.raw_decode(text[match.start() :])[0] for match in re.finditer(r"(?m)^\{", text)]


def test_demonstration_candidate_pools_are_valid_k_five_outputs():
    pools = json_examples(prompt_examples.CANDIDATE_POOLS)
    assert len(pools) == 6
    for pool in pools:
        pool_output_type("candidates", 5).model_validate(pool)


def test_demonstration_node_uses_the_real_context_schema():
    examples = json_examples(prompt_examples.WORKFLOWS)
    assert len(examples) == 1
    node = Node.model_validate(examples[0])
    assert node.isolated_context is False
    assert node.cue is None
    assert "dependencies" not in node.model_dump()
    assert "context" not in node.model_dump()


def test_rendered_examples_keep_literal_json_and_actual_count():
    rendered = prompts.render("candidates", 7)
    for pool in json_examples(rendered):
        pool_output_type("candidates", 5).model_validate(pool)
    assert (
        "Return exactly 7 candidates for the ACTUAL node only. "
        "Do not reproduce the sample pools or output a selection."
    ) in rendered.split("# Examples")[0]
    assert rendered.startswith("# Instructions\n")
    assert rendered.count("\n# Examples\n") == 1
