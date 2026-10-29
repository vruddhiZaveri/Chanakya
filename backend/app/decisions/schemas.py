from typing import Annotated, Literal

from pydantic import Field, model_validator

from app.schemas import StrictModel, Text

ShortText = Annotated[Text, Field(max_length=400)]
DomainKey = Annotated[Text, Field(max_length=80, pattern=r"^[a-z][a-z0-9_-]*$")]
HypothesisType = Literal["factual", "causal", "comparative", "predictive", "diagnostic", "normative"]
HypothesisStatus = Literal["proposed", "under_investigation", "supported", "challenged", "revised", "resolved", "inconclusive"]


class DecisionBrief(StrictModel):
    query: Annotated[Text, Field(min_length=10, max_length=2000)]
    domain_key: DomainKey = "general"
    selected_domains: list[DomainKey] = Field(default_factory=list, max_length=10)
    specifications: dict[Annotated[Text, Field(max_length=80)], ShortText] = Field(default_factory=dict, max_length=20)
    objective: Annotated[Text, Field(max_length=1000)] | None = None
    constraints: list[ShortText] = Field(default_factory=list, max_length=10)
    success_criteria: list[ShortText] = Field(default_factory=list, max_length=10)

    @model_validator(mode="after")
    def distinct_domains(self):
        if len(set(self.selected_domains)) != len(self.selected_domains):
            raise ValueError("Selected domains must be unique")
        return self


class BriefUpdate(StrictModel):
    expected_revision: Annotated[int, Field(ge=1)]
    brief: DecisionBrief
    revision_reason: ShortText


class Content(StrictModel):
    claim: Annotated[Text, Field(min_length=10, max_length=2000)]
    scope: Annotated[Text, Field(max_length=1000)]
    assumptions: list[ShortText] = Field(default_factory=list, max_length=8)
    jurisdiction: ShortText | None = None


class FactualContent(Content):
    type: Literal["factual"]


class CausalContent(Content):
    type: Literal["causal"]
    cause: ShortText
    effect: ShortText
    assumptions: list[ShortText] = Field(min_length=1, max_length=8)


class ComparativeContent(Content):
    type: Literal["comparative"]
    alternatives: list[ShortText] = Field(min_length=2, max_length=5)
    criteria: list[ShortText] = Field(min_length=1, max_length=8)

    @model_validator(mode="after")
    def distinct_alternatives(self):
        if len({x.casefold() for x in self.alternatives}) != len(self.alternatives):
            raise ValueError("Comparative alternatives must be distinct")
        return self


class PredictiveContent(Content):
    type: Literal["predictive"]
    measurable_outcome: ShortText
    time_horizon: ShortText


class DiagnosticContent(Content):
    type: Literal["diagnostic"]
    latent_state: ShortText
    observations: list[ShortText] = Field(min_length=1, max_length=8)


class NormativeContent(Content):
    type: Literal["normative"]
    values: list[ShortText] = Field(min_length=1, max_length=8)


HypothesisContent = Annotated[FactualContent | CausalContent | ComparativeContent | PredictiveContent | DiagnosticContent | NormativeContent, Field(discriminator="type")]


class HypothesisCreate(StrictModel):
    expected_session_revision: Annotated[int, Field(ge=1)]
    content: HypothesisContent


class HypothesisRevision(HypothesisCreate):
    expected_revision: Annotated[int, Field(ge=1)]
    revision_reason: ShortText


class HypothesisTransition(StrictModel):
    expected_revision: Annotated[int, Field(ge=1)]
    target_status: HypothesisStatus
    reason: ShortText


class SessionRecord(StrictModel):
    session_id: str
    revision: int
    brief: DecisionBrief
    created_at: str
    updated_at: str
    hypothesis_count: int


class BriefVersion(StrictModel):
    session_id: str
    revision: int
    brief: DecisionBrief
    revision_reason: str
    created_at: str


class SessionPage(StrictModel):
    items: list[SessionRecord]
    total: int
    offset: int
    limit: int


class ProbabilityUnavailable(StrictModel):
    status: Literal["not_assessed"] = "not_assessed"
    prior: None = None
    posterior: None = None
    reason: str = "No justified probabilistic inference has been performed."


class HypothesisVersion(StrictModel):
    version_id: str
    hypothesis_id: str
    revision: int
    previous_version_id: str | None
    brief_revision: int
    content: HypothesisContent
    status: HypothesisStatus
    revision_reason: str
    author_kind: Literal["human"] = "human"
    created_by_execution_id: None = None
    created_at: str
    probability: ProbabilityUnavailable = Field(default_factory=ProbabilityUnavailable)


class HypothesisRecord(StrictModel):
    hypothesis_id: str
    session_id: str
    current: HypothesisVersion
    context_outdated: bool
    created_at: str


class HypothesisPage(StrictModel):
    items: list[HypothesisRecord]
    total: int


class HypothesisHistory(StrictModel):
    hypothesis_id: str
    session_id: str
    items: list[HypothesisVersion]
    total: int
    limit: int
    offset: int
