import json
import subprocess
import sys

import pytest
from pydantic_ai.exceptions import ModelHTTPError

from creative.core.engine import Engine
from creative.core.events import ProgressEvent
from creative.core.schemas import CandidatePool, FrameworkPool, GenerateRequest
from creative.interfaces import cli
from creative.interfaces import visualize as view


@pytest.fixture
def cli_models(scripted, settings, monkeypatch):
    monkeypatch.setattr(cli, "Settings", lambda: settings)
    monkeypatch.setattr(cli, "LLM", lambda _: scripted.llm())
    return scripted


def test_quiet_cli_prints_only_final_output(cli_models, capsys):
    cli.main(["bear", "--candidate-count", "3"])
    captured = capsys.readouterr()
    assert captured.out == "Finished: bear\n"
    assert captured.err == ""
    assert cli_models.counts["framework"] == 1


def test_verbose_cli_prints_steps_pools_and_selections(cli_models, capsys):
    cli.main(["bear", "--candidate-count", "3", "--verbose"])
    captured = capsys.readouterr()
    assert captured.out == "Finished: bear\n"
    assert "[framework] started" in captured.err
    assert "[framework] completed" in captured.err
    assert "[plan] completed" in captured.err
    assert "framework_mapping" in captured.err
    assert "[node:cast] completed" in captured.err
    assert "Candidate 3 (index 2)" in captured.err
    assert "cast: alternative" not in captured.err  # Cast output is the actual complete cast.
    assert "Ada, Bo, Cy" in captured.err
    assert captured.err.count("Selected candidate") == 7
    assert captured.err.index("Selected candidate") < captured.err.index("[plan] started")
    assert "[writer] completed" in captured.err
    assert "Finished in" in captured.err


def test_verbose_json_keeps_stdout_parseable(cli_models, capsys):
    cli.main(["bear", "--candidate-count", "3", "--verbose", "--json"])
    captured = capsys.readouterr()
    result = json.loads(captured.out)
    assert result["candidate_count"] == 3
    assert len(result["framework"]["candidates"]) == 3
    assert all(
        s["selected_value"] == s["candidates"][s["selected_index"]] for s in result["selections"]
    )
    assert "[framework] started" in captured.err


@pytest.mark.parametrize("extra", [[], ["--verbose", "--json"]])
def test_visualize_retains_pools_and_opens_self_contained_view(
    cli_models, capsys, monkeypatch, tmp_path, extra
):
    opened = []
    monkeypatch.setattr(view.tempfile, "mkdtemp", lambda **_: str(tmp_path))
    monkeypatch.setattr(view.webbrowser, "open", lambda url, **_: opened.append(url))
    cli.main(["bear", "--candidate-count", "3", "--visualize", *extra])
    captured = capsys.readouterr()
    path = tmp_path / "workflow.html"
    assert opened == [path.as_uri()]
    html = path.read_text()
    raw = html.split('<script type="application/json" id="workflow-data">')[1].split("</script>")[0]
    data = json.loads(raw)
    assert all(
        len(node["selection"]["candidates"]) == 3 for node in data["nodes"] if "selection" in node
    )
    nodes = {node["id"]: node for node in data["nodes"]}
    assert data["nodes"][0]["id"] == "__input__"
    assert data["nodes"][1]["id"] == "0"
    assert nodes["__input__"]["input"] == "bear"
    assert nodes["0"]["previous_id"] == "__input__"
    assert nodes["inspiration"]["context_inputs"] == []
    assert nodes["inspiration"]["previous_id"] == "world"
    assert nodes["cast"]["previous_id"] == "cast_size"
    assert nodes["outline"]["context_inputs"] == [
        "__input__",
        "0",
        "emotion",
        "world",
        "inspiration",
        "cast_size",
        "cast",
    ]
    for previous, current in zip(data["nodes"], data["nodes"][1:], strict=False):
        assert current["previous_id"] == previous["id"]
    assert all("dependencies" not in node for node in data["nodes"])
    assert nodes["__output__"]["output"] == "Finished: bear"
    model_nodes = [node for node in data["nodes"] if node["id"] != "__input__"]
    assert all(node["model_input"]["prompt"] for node in model_nodes)
    assert nodes["0"]["planning_input"]["prompt"]
    assert all(set(node["model_input"]) == {"model", "prompt"} for node in model_nodes)
    assert "Context and decision instructions" not in html
    assert "Full LLM input" in html
    for node in data["nodes"]:
        if "selection" not in node:
            continue
        selection = node["selection"]
        assert selection["candidates"][selection["selected_index"]] == selection["selected_value"]
    assert path.stat().st_mode & 0o777 == 0o600
    assert "Workflow view:" in captured.err
    if "--json" in extra:
        assert json.loads(captured.out)["output"] == "Finished: bear"
    else:
        assert captured.out == "Finished: bear\n"


def test_visualization_treats_model_html_as_inert_data(cli_models, capsys, monkeypatch, tmp_path):
    monkeypatch.setattr(view.tempfile, "mkdtemp", lambda **_: str(tmp_path))
    monkeypatch.setattr(view.webbrowser, "open", lambda *_, **__: False)
    attack = '</script><script>alert("untrusted")</script>'
    cli.main([attack, "--candidate-count", "1", "--visualize"])
    html = (tmp_path / "workflow.html").read_text()
    assert attack not in html
    assert "\\u003c/script>" in html
    assert "Finished:" in capsys.readouterr().out


def test_visualization_failure_preserves_successful_generation(cli_models, capsys, monkeypatch):
    def fail(_):
        raise OSError("Browser unavailable")

    monkeypatch.setattr(cli, "open_visualization", fail)
    cli.main(["bear", "--visualize", "--candidate-count", "1"])
    captured = capsys.readouterr()
    assert captured.out == "Finished: bear\n"
    assert "Could not open workflow view: Browser unavailable" in captured.err


def test_bad_cli_input_fails_before_model_calls(cli_models, capsys):
    with pytest.raises(SystemExit) as caught:
        cli.main(["bear", "--candidate-count", "0"])
    assert caught.value.code == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "Configuration/input error" in captured.err
    assert not cli_models.calls


def test_cli_uses_standardized_failure_without_provider_body(cli_models, capsys):
    async def fail(role, payload):
        raise ModelHTTPError(400, "test", body="sensitive provider body")

    cli_models.hook = fail
    with pytest.raises(SystemExit) as caught:
        cli.main(["bear"])
    assert caught.value.code == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "provider_error" in captured.err
    assert "framework" in captured.err
    assert "sensitive provider body" not in captured.err
    assert "Traceback" not in captured.err


def test_python_module_exposes_cli_help_without_model_calls():
    result = subprocess.run(
        [sys.executable, "-m", "creative", "--help"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "--verbose" in result.stdout
    assert "--candidate-count" in result.stdout
    assert "--json" in result.stdout
    assert "--visualize" in result.stdout


async def test_core_progress_is_emitted_before_downstream_generation(scripted, settings):
    events: list[ProgressEvent] = []

    def observe(event):
        events.append(event)
        if event.stage == "framework" and event.status == "completed":
            assert [role for role, _ in scripted.calls] == ["framework"]
        if event.stage == "plan" and event.status == "completed":
            assert not any(role == "candidates" for role, _ in scripted.calls)

    async with scripted.llm() as llm:
        result = await Engine(llm, settings, selector=lambda n: 1).generate(
            GenerateRequest(prompt="bear", candidate_count=3), on_progress=observe
        )
    framework_event = next(e for e in events if e.stage == "framework" and e.status == "completed")
    assert isinstance(framework_event.output, FrameworkPool)
    assert framework_event.selected_index == result.framework.selected_index
    nodes = {
        event.stage.removeprefix("node:"): event
        for event in events
        if event.stage.startswith("node:") and event.status == "completed"
    }
    for selection in result.selections:
        event = nodes[selection.node_id]
        assert isinstance(event.output, CandidatePool)
        assert event.output.candidates[event.selected_index] == selection.selected_value
    assert events[-1].stage == "writer" and events[-1].output == result.output
