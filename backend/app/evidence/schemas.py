from typing import Annotated, Literal
from pydantic import Field
from app.schemas import StrictModel, Text


class DocumentRecord(StrictModel):
    document_id: str
    version_id: str
    session_id: str
    filename: str
    media_type: str
    sha256: str
    byte_size: int
    page_count: int
    empty_pages: list[int]
    passage_count: int
    created_at: str
    status: Literal["ready"] = "ready"
    extraction_version: str = "extract-v1"
    authenticity_verified: Literal[False] = False


class SearchRequest(StrictModel):
    query: Annotated[Text, Field(min_length=3, max_length=1000)]
    expected_session_revision: Annotated[int, Field(ge=1)]
    limit: Annotated[int, Field(ge=1, le=5)] = 3
    document_ids: list[Annotated[Text, Field(pattern=r"^[0-9a-f-]{36}$")]] = Field(
        default_factory=list, max_length=10
    )


class Passage(StrictModel):
    source_id: str
    document_id: str
    document_version_id: str
    filename: str
    document_sha256: str
    page: int
    start_char: int
    end_char: int
    excerpt: str
    score: float


class EvidenceSnapshot(StrictModel):
    snapshot_id: str
    session_id: str
    brief_revision: int
    query: str
    passages: list[Passage]
    document_version_ids: list[str]
    created_at: str
    retrieval_method: str = "lexical-bm25-v1"
    offset_basis: str = "Unicode character offsets in the stored extracted page text"
    score_meaning: str = (
        "Lexical relevance ranking only; not confidence or factual support."
    )
    semantic_support_verified: Literal[False] = False
    authenticity_verified: Literal[False] = False
