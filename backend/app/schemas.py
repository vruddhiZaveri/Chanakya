from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
SourceId = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9_-]{1,40}$")]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Mode(str, Enum):
    DIRECT = "direct"
    SOURCE_GROUNDED = "source_grounded"


class SuppliedSource(StrictModel):
    id: SourceId
    title: Annotated[Text, Field(max_length=120)]
    excerpt: Annotated[Text, Field(max_length=1200)]


class BaselineRequest(StrictModel):
    mode: Literal["direct", "source_grounded"] = "direct"
    question: Annotated[Text, Field(min_length=10, max_length=2000)]
    sources: list[SuppliedSource] = Field(default_factory=list, max_length=3)

    @model_validator(mode="after")
    def source_contract(self):
        if self.mode == "source_grounded" and not self.sources:
            raise ValueError("Source-grounded mode requires supplied sources")
        if self.mode == "direct" and self.sources:
            raise ValueError("Use source_grounded mode when supplying sources")
        if len({source.id for source in self.sources}) != len(self.sources):
            raise ValueError("Source IDs must be unique")
        return self


class Assessment(StrictModel):
    answer: Annotated[Text, Field(max_length=6000)]
    source_ids: list[SourceId] = Field(max_length=3)
    limitations: list[Annotated[Text, Field(max_length=400)]] = Field(min_length=1, max_length=6)
    insufficient_evidence: bool


class Usage(StrictModel):
    input_tokens: int | None
    output_tokens: int | None
    total_model_seconds: float | None


class RuntimeConfig(StrictModel):
    context_tokens: int
    output_tokens: int
    temperature: Literal[0] = 0
    prompt_version: str = "baseline-v1"


class ValidationSummary(StrictModel):
    schema_valid: Literal[True] = True
    citation_ids_valid: Literal[True] = True
    semantic_support_verified: Literal[False] = False
    source_authenticity_verified: Literal[False] = False


class BaselineResponse(StrictModel):
    request_id: str
    mode: Literal["direct", "source_grounded"]
    model: str
    model_digest: str
    digest_basis: str = "installed_registry_before_call"
    assessment: Assessment
    validation: ValidationSummary
    configuration: RuntimeConfig
    model_attempts: int
    usage: Usage
    elapsed_seconds: float
    advisory_notice: str = "Single-agent baseline only; not a verified research conclusion or a human-reviewed decision."


class LoadedModel(StrictModel):
    loaded: bool = False
    reported_size_bytes: int | None = None
    reported_vram_bytes: int | None = None
    context_tokens: int | None = None


class ModelStatus(StrictModel):
    model: str
    installed: bool
    digest: str | None
    quantization: str | None
    parameter_size: str | None
    loaded: LoadedModel
    ready_to_attempt: bool
    note: str = "Installation/readiness metadata does not establish inference quality or hardware identity."
