# Contributing

Bug reports, focused fixes, and improvements to creative decision workflows are welcome.

## Local setup

```sh
uv sync --locked
uv run ruff check .
uv run ruff format --check .
uv run pytest -q
```

Normal tests need no provider keys and disable paid model requests. The transport tests bind
a temporary localhost port. Provider adapters use mocked HTTP; engine tests use Pydantic AI
function models. Keep tests deterministic and separate creative-quality review from structural
correctness.

## Live smoke test

To run the optional bear-story smoke test using your configured credentials:

```sh
CREATIVE_LIVE=1 uv run pytest tests/test_live.py -q
```

This spends provider credits and writes the ignored `live-result.json`. Review the result
against [the workflow example](docs/workflow-example.md): alternatives should differ in their
consequences, later steps should develop earlier selections, and the final artifact should
preserve the locked choices. Structural success alone does not establish creative quality.

## Changes

Keep the shared engine independent of CLI, HTTP, and visualization details. Preserve uniform
Python selection; avoid hidden ranking or rerolling. Include tests for meaningful behavior
changes and update the relevant documentation. If dependencies change, update `uv.lock`.

Never commit credentials, generated private runs, or captured prompts. Use `.env.example`
for placeholder configuration. Share minimal reproducible examples in issues instead of
unredacted logs or full private briefs.
