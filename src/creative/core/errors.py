"""Shared error classification and safe, transport-independent error responses."""

from pydantic_ai.exceptions import (
    ModelConnectionError,
    ModelHTTPError,
    ModelQuotaExceededError,
    ModelTimeoutError,
    UnexpectedModelBehavior,
)

from creative.core.schemas import ErrorDetail


class StageFailure(Exception):
    def __init__(self, stage: str, code: str, retryable: bool, **diagnostics):
        self.stage = stage
        self.code = code
        self.retryable = retryable
        self.diagnostics = diagnostics
        super().__init__(code)


class GenerationFailure(Exception):
    def __init__(self, detail: ErrorDetail, status_code: int = 502):
        self.detail = detail
        self.status_code = status_code
        super().__init__(detail.message)

    @property
    def payload(self) -> dict:
        return {"error": self.detail.model_dump(exclude_none=True)}


def is_transient(error: Exception) -> bool:
    if isinstance(error, ModelQuotaExceededError):
        return False
    if isinstance(error, ModelHTTPError):
        return error.provider_retry_hint is not False and (
            error.status_code in {408, 409, 429} or error.status_code >= 500
        )
    return isinstance(error, (ModelConnectionError, TimeoutError))


def stage_failure(error: Exception, stage: str, **diagnostics) -> StageFailure:
    if isinstance(error, UnexpectedModelBehavior):
        return StageFailure(stage, "invalid_model_output", False, **diagnostics)
    code = (
        "provider_timeout"
        if isinstance(error, (TimeoutError, ModelTimeoutError))
        else "provider_error"
    )
    return StageFailure(stage, code, is_transient(error), **diagnostics)


def find_stage_failure(error: BaseException) -> StageFailure | None:
    if isinstance(error, StageFailure):
        return error
    if isinstance(error, BaseExceptionGroup):
        for child in error.exceptions:
            if failure := find_stage_failure(child):
                return failure
    return None


def generation_failure(error: Exception, request_id: str, stage: str) -> GenerationFailure:
    if isinstance(error, GenerationFailure):
        return error
    failure = find_stage_failure(error)
    code = "generation_error"
    message = "Generation failed; no finished output was produced"
    retryable = False
    status_code = 502
    if isinstance(error, TimeoutError):
        code = "generation_timeout"
        message = "Generation deadline exceeded"
        retryable = True
        status_code = 504
    elif failure is not None:
        code, stage, retryable = failure.code, failure.stage, failure.retryable
        if code == "provider_timeout":
            message = (
                "Provider request timed out after exhausting its attempts; "
                "see attempts, timeout_seconds and elapsed_seconds"
            )
    return GenerationFailure(
        ErrorDetail(
            request_id=request_id,
            code=code,
            message=message,
            stage=stage,
            retryable=retryable,
            **(failure.diagnostics if failure else {}),
        ),
        status_code=status_code,
    )


def busy_failure(request_id: str) -> GenerationFailure:
    return GenerationFailure(
        ErrorDetail(
            request_id=request_id,
            code="busy",
            message="Generation capacity is full; retry later",
            stage="admission",
            retryable=True,
        ),
        status_code=429,
    )
