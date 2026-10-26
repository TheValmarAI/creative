"""A private, self-contained browser view of a completed CLI generation."""

import json
import tempfile
import webbrowser
from pathlib import Path

from creative.core.schemas import GenerateResponse, ModelCall


def readable_value(value, level: int = 2) -> str:
    """Show structured input as headings and text, preserving its content without JSON chrome."""
    if isinstance(value, dict):
        headings = {
            "request": "request from user",
            "selected_values": "selected values from previous nodes",
            "instructions": "instructions for this node",
        }
        return "\n\n".join(
            f"{'#' * min(level, 6)} "
            f"{headings.get(key, key.replace('_', ' ')) if level == 2 else key.replace('_', ' ')}"
            f"\n\n{readable_value(item, level + 1)}"
            for key, item in value.items()
        )
    if isinstance(value, list):
        return "\n\n".join(f"- {readable_value(item, level)}" for item in value)
    return value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)


def prompt_text(call: ModelCall) -> str:
    """Use the SDK's effective instruction source, not both mirrored representations."""
    parts = call.request_parameters.get("instruction_parts")
    if parts is not None:
        instructions = "\n\n".join(part["content"] for part in parts)
    else:
        instructions = next(
            (
                message["instructions"]
                for message in reversed(call.messages)
                if message.get("instructions")
            ),
            "",
        )
    blocks = (
        [
            instructions
            if instructions.startswith("# Instructions\n")
            else f"# Instructions\n\n{instructions}"
        ]
        if instructions
        else []
    )
    for message in call.messages:
        for part in message.get("parts", []):
            kind = part["part_kind"]
            value = part.get("content", part)
            if isinstance(value, str):
                try:
                    value = json.loads(value)
                except ValueError:
                    pass
            heading = "UserPrompt" if kind == "user-prompt" else kind.replace("-", " ").title()
            blocks.append(f"# {heading}\n\n{readable_value(value)}")
    return "\n\n".join(blocks)


def view_data(result: GenerateResponse) -> dict:
    """One previous-node link per step; context scope is displayed separately."""
    traces = {entry.stage: entry for entry in result.trace}

    def calls(stage: str) -> dict | None:
        trace = traces.get(stage)
        if trace is None or trace.model_calls is None:
            return None
        return {"model": trace.model, "prompt": prompt_text(trace.model_calls[-1])}

    nodes = [
        {
            "id": "__input__",
            "label": "User Input",
            "purpose": "The original creative brief.",
            "previous_id": None,
            "input": result.prompt,
        },
        {
            "id": "0",
            "label": "Framework",
            "purpose": "Choose the organizing approach before planning the workflow.",
            "previous_id": "__input__",
            "selection": result.framework.model_dump(mode="json"),
            "model_input": calls("framework"),
            "planning_input": calls("plan"),
        },
    ]
    selections = {selection.node_id: selection for selection in result.selections}
    for node in result.workflow.nodes:
        context_inputs = [] if node.isolated_context else [item["id"] for item in nodes]
        nodes.append(
            {
                **node.model_dump(mode="json"),
                "label": node.id.replace("_", " "),
                "previous_id": nodes[-1]["id"],
                "context_inputs": context_inputs,
                "model_input": calls(f"node:{node.id}"),
                "selection": selections[node.id].model_dump(mode="json"),
                "components": [
                    mapping.component
                    for mapping in result.workflow.framework_mapping
                    if node.id in mapping.node_ids
                ],
            }
        )
    nodes.append(
        {
            "id": "__output__",
            "label": "Finished output",
            "purpose": "Develop the finished work and explain its selected dimensions and choices.",
            "previous_id": nodes[-1]["id"],
            "output": result.output,
            "model_input": calls("writer"),
        }
    )
    return {
        "request_id": result.request_id,
        "elapsed_seconds": result.elapsed_seconds,
        "candidate_count": result.candidate_count,
        "nodes": nodes,
    }


def render_visualization(result: GenerateResponse) -> str:
    # Data remains inert even if an LLM returns HTML or a closing script tag.
    payload = json.dumps(view_data(result), ensure_ascii=True).replace("<", "\\u003c")
    template = Path(__file__).with_name("workflow_view.html").read_text(encoding="utf-8")
    return template.replace("__WORKFLOW_DATA__", payload)


def open_visualization(result: GenerateResponse) -> Path:
    """Keep a reopenable file without starting a server or blocking CLI exit."""
    path = Path(tempfile.mkdtemp(prefix="creative-view-")) / "workflow.html"
    path.touch(mode=0o600)
    path.write_text(render_visualization(result), encoding="utf-8")
    webbrowser.open(path.as_uri(), new=1)
    return path
