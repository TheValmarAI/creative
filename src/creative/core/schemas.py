"""Public contracts and structural validation; no model-generated executable code."""

from functools import lru_cache
from typing import Annotated, Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, create_model, model_validator

Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=16000)]
NodeId = Annotated[str, StringConstraints(pattern=r"^[a-z][a-z0-9_]{0,63}$")]
Prompt = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=16000)]
CandidateCount = Annotated[int, Field(ge=1, le=100)]


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid")


def distinct(values: list[str]) -> None:
    if len({value.strip().casefold() for value in values}) != len(values):
        raise ValueError("Values must be distinct, ignoring case and surrounding whitespace")


class Framework(Contract):
    name: Text
    origin: Literal["established", "adapted", "original"]
    attribution: Text
    organizing_principle: Text
    required_components: Annotated[list[Text], Field(min_length=1, max_length=23)]
    progression_rules: Annotated[list[Text], Field(min_length=1, max_length=23)]
    completion_criteria: Annotated[list[Text], Field(min_length=1, max_length=23)]

    @model_validator(mode="after")
    def unique_components(self) -> Self:
        distinct(self.required_components)
        return self


class FrameworkPool(Contract):
    candidates: Annotated[list[Framework], Field(min_length=1, max_length=100)]

    @model_validator(mode="after")
    def unique_names(self) -> Self:
        distinct([item.name for item in self.candidates])
        return self


class CandidatePool(Contract):
    candidates: Annotated[list[Text], Field(min_length=1, max_length=100)]

    @model_validator(mode="after")
    def unique_candidates(self) -> Self:
        distinct(self.candidates)
        return self


@lru_cache(maxsize=200)
def pool_output_type(role: Literal["framework", "candidates"], count: int) -> type[BaseModel]:
    """Expose the exact requested count to the model's schema and validation retry path."""
    base, item_type = (FrameworkPool, Framework) if role == "framework" else (CandidatePool, Text)
    return create_model(
        f"{base.__name__}{count}",
        __base__=base,
        candidates=(list[item_type], Field(min_length=count, max_length=count)),
    )


class Node(Contract):
    id: NodeId
    purpose: Text
    instructions: Text
    rationale: Text
    isolated_context: bool = False
    cue: Text | None = None

    @model_validator(mode="after")
    def context_consistency(self) -> Self:
        if self.isolated_context and self.cue is None:
            raise ValueError("Isolated nodes need a narrow cue")
        if not self.isolated_context and self.cue is not None:
            raise ValueError("Only isolated nodes may declare a cue")
        return self


class ComponentMapping(Contract):
    component: Text
    node_ids: Annotated[list[NodeId], Field(min_length=1, max_length=23)]


class Workflow(Contract):
    nodes: Annotated[list[Node], Field(min_length=1, max_length=23)]
    framework_mapping: Annotated[list[ComponentMapping], Field(min_length=1, max_length=23)]

    @model_validator(mode="after")
    def valid_sequence(self) -> Self:
        seen: set[str] = set()
        for node in self.nodes:
            if node.id in seen:
                raise ValueError(f"Duplicate node ID: {node.id}")
            seen.add(node.id)
        distinct([mapping.component for mapping in self.framework_mapping])
        for mapping in self.framework_mapping:
            distinct(mapping.node_ids)
            if not set(mapping.node_ids) <= seen:
                raise ValueError("Framework mapping references an unknown node")
        return self

    def validate_for(self, framework: Framework) -> None:
        if {m.component for m in self.framework_mapping} != set(framework.required_components):
            raise ValueError("Map every required component exactly once using its exact text")


class GenerateRequest(Contract):
    prompt: Prompt
    include_candidates: bool = True
    candidate_count: CandidateCount | None = None


class Selection(Contract):
    node_id: str
    selected_index: int = Field(ge=0, lt=100)
    selected_value: str
    candidates: list[str] | None = None


class FrameworkSelection(Contract):
    node_id: Literal["0"] = "0"
    selected_index: int = Field(ge=0, lt=100)
    selected_value: Framework
    candidates: list[Framework] | None = None


class ModelCall(Contract):
    attempt: int
    messages: list[dict[str, Any]]
    request_parameters: dict[str, Any]
    model_settings: dict[str, Any] | None


class StageTrace(Contract):
    stage: str
    model: str
    elapsed_seconds: float
    requests: int
    input_tokens: int
    output_tokens: int
    model_calls: list[ModelCall] | None = None


class GenerateResponse(Contract):
    request_id: str
    prompt: Prompt | None = None
    candidate_count: CandidateCount
    output: str
    framework: FrameworkSelection
    workflow: Workflow
    selections: list[Selection]
    trace: list[StageTrace]
    elapsed_seconds: float
    input_tokens: int
    output_tokens: int


class ErrorDetail(Contract):
    request_id: str
    code: str
    message: str
    stage: str
    retryable: bool
    attempts: int | None = None
    timeout_seconds: float | None = None
    elapsed_seconds: float | None = None
    error_type: str | None = None
