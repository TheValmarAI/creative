"""Pydantic Logfire setup shared by CLI and HTTP interfaces."""

import sys
from contextlib import nullcontext

import logfire

from creative.core.config import Settings

_configured = False


def configure(settings: Settings, *, console: bool = False) -> None:
    global _configured
    if not settings.logfire_enabled or _configured:
        return
    logfire.configure(
        service_name="creative",
        token=settings.logfire_token or None,
        send_to_logfire="if-token-present",
        console=logfire.ConsoleOptions(output=sys.stderr) if console else False,
    )
    logfire.instrument_pydantic_ai(include_content=settings.logfire_include_content)
    _configured = True


def span(name: str, **attributes):
    return logfire.span(name, **attributes) if _configured else nullcontext()


def flush() -> None:
    if _configured:
        logfire.force_flush(timeout_millis=2000)
