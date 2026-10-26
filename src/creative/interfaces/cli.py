"""Run a generation directly from the terminal, with optional live progress."""

import argparse
import asyncio
import json
import logging
import sys
import webbrowser

from pydantic import BaseModel, ValidationError
from pydantic_ai.exceptions import UserError

from creative.core.config import Settings
from creative.core.engine import Engine
from creative.core.errors import GenerationFailure
from creative.core.events import ProgressEvent
from creative.core.llm import LLM
from creative.core.observability import configure, flush
from creative.core.schemas import CandidatePool, FrameworkPool, GenerateRequest, GenerateResponse
from creative.interfaces.visualize import open_visualization


def format_value(value: BaseModel | str) -> str:
    return value.model_dump_json(indent=2) if isinstance(value, BaseModel) else value


def print_progress(event: ProgressEvent) -> None:
    """Progress goes to stderr so stdout stays usable as the final text or JSON."""
    print(f"\n[{event.stage}] {event.status}", file=sys.stderr, flush=True)
    if event.status == "attempt":
        print(
            f"  Provider attempt {event.attempt}; deadline {event.timeout_seconds:g}s",
            file=sys.stderr,
            flush=True,
        )
    elif event.status == "retrying":
        print(
            f"  Attempt {event.attempt} failed after {event.elapsed_seconds:.1f}s "
            f"({event.error_type}); retrying in {event.retry_delay_seconds:.1f}s",
            file=sys.stderr,
            flush=True,
        )
    if event.status != "completed" or event.stage == "writer":
        return
    if isinstance(event.output, (FrameworkPool, CandidatePool)):
        for index, candidate in enumerate(event.output.candidates):
            text = format_value(candidate)
            print(f"\nCandidate {index + 1} (index {index}):\n{text}", file=sys.stderr, flush=True)
        index = event.selected_index
        if index is not None:
            candidate = event.output.candidates[index]
            text = format_value(candidate)
            print(
                f"\nSelected candidate {index + 1} (index {index}):\n{text}",
                file=sys.stderr,
                flush=True,
            )
    elif event.output is not None:
        print(format_value(event.output), file=sys.stderr, flush=True)


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(
        prog="creative",
        description="Generate a creative output using frameworks and random choices.",
    )
    command.add_argument("prompt", help="Creative brief, including desired format and constraints")
    command.add_argument(
        "--candidate-count",
        type=int,
        metavar="N",
        help="Candidates per node (1–100; default: .env)",
    )
    command.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Print steps, all candidate outputs and random selections as they complete (stderr)",
    )
    command.add_argument(
        "--visualize",
        action="store_true",
        help="Open a clickable workflow with selections and alternatives after completion",
    )
    command.add_argument(
        "--json", action="store_true", help="Return the full result and candidate pools as JSON"
    )
    return command


async def generate(args: argparse.Namespace) -> GenerateResponse:
    """Normal CLI path: configure → run shared engine → return typed result."""
    request = GenerateRequest(
        prompt=args.prompt,
        candidate_count=args.candidate_count,
        include_candidates=args.json or args.visualize,
    )
    settings = Settings()
    configure(settings, console=args.verbose)
    async with LLM(settings) as llm:
        engine = Engine(llm, settings)
        return await engine.generate(
            request,
            on_progress=print_progress if args.verbose else None,
            capture_prompts=args.visualize,
        )


def main(argv: list[str] | None = None) -> None:
    args = parser().parse_args(argv)
    # Human-facing failures below replace the core's fallback logging in this CLI process.
    logging.getLogger("creative").addHandler(logging.NullHandler())
    try:
        result = asyncio.run(generate(args))
    except GenerationFailure as error:
        print(f"Error: {json.dumps(error.payload)}", file=sys.stderr)
        raise SystemExit(1) from None
    except (ValidationError, UserError) as error:
        print(f"Configuration/input error: {error}", file=sys.stderr)
        raise SystemExit(2) from None
    except KeyboardInterrupt:
        print("\nCancelled.", file=sys.stderr)
        raise SystemExit(130) from None
    finally:
        flush()
    print(result.model_dump_json(indent=2, exclude_none=True) if args.json else result.output)
    if args.visualize:
        try:
            path = open_visualization(result)
            print(f"\nWorkflow view: {path}", file=sys.stderr)
        except (OSError, webbrowser.Error) as error:
            print(f"Could not open workflow view: {error}", file=sys.stderr)
    if args.verbose:
        print(
            f"\nFinished in {result.elapsed_seconds:.2f}s | "
            f"tokens: {result.input_tokens} input / {result.output_tokens} output | "
            f"request: {result.request_id}",
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
