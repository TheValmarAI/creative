"""Request-local progress events, independent of any transport or display format."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

from creative.core.schemas import CandidatePool, FrameworkPool, Workflow


@dataclass(frozen=True)
class ProgressEvent:
    stage: str
    status: Literal["started", "completed", "attempt", "retrying"]
    output: FrameworkPool | CandidatePool | Workflow | str | None = None
    selected_index: int | None = None
    attempt: int | None = None
    elapsed_seconds: float | None = None
    timeout_seconds: float | None = None
    retry_delay_seconds: float | None = None
    error_type: str | None = None


ProgressHandler = Callable[[ProgressEvent], None]
