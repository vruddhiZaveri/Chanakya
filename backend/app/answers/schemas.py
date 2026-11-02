from typing import Annotated, Literal
from uuid import UUID
from pydantic import Field, field_validator
from app.schemas import StrictModel, BaselineResponse
from app.decisions.schemas import DecisionBrief
from app.evidence.schemas import EvidenceSnapshot


class AnswerRequest(StrictModel):
    snapshot_id: UUID
    expected_session_revision: Annotated[int, Field(ge=1)]
    idempotency_key: UUID

    @field_validator("snapshot_id", "idempotency_key", mode="before")
    @classmethod
    def parse_uuid(cls, value):
        if isinstance(value, str):
            return UUID(value)
        return value


class SavedAnswer(StrictModel):
    answer_id: str
    session_id: str
    brief_revision: int
    idempotency_key: str
    created_at: str
    status: Literal["completed"] = "completed"
    brief: DecisionBrief
    evidence: EvidenceSnapshot
    model_input_sha256: str
    response: BaselineResponse
    execution_kind: Literal["single_agent_document_grounded"] = (
        "single_agent_document_grounded"
    )
    notice: str = (
        "Citations identify supplied passages; factual support and document authenticity are not verified. Human decision authority is retained."
    )


class AnswerList(StrictModel):
    items: list[SavedAnswer]
    total: int
    limit: int
    offset: int
