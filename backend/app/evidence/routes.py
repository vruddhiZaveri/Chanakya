from typing import Annotated
from uuid import UUID
from urllib.parse import quote
from fastapi import APIRouter, Request, Query
from starlette.concurrency import run_in_threadpool
from starlette.responses import Response
from app.core.errors import BackendError
from app.evidence.extraction import extract_pages
from app.evidence.schemas import DocumentRecord, EvidenceSnapshot, SearchRequest

router = APIRouter(
    prefix="/api/v1/sessions/{session_id}", tags=["Documents and evidence"]
)


@router.post(
    "/documents",
    response_model=DocumentRecord,
    status_code=201,
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {
                m: {"schema": {"type": "string", "format": "binary"}}
                for m in ["text/plain", "text/markdown", "application/pdf"]
            },
        }
    },
)
async def upload(
    session_id: UUID,
    request: Request,
    filename: Annotated[str, Query(min_length=1, max_length=120)],
    expected_session_revision: Annotated[int, Query(ge=1)],
):
    repo = request.app.state.evidence
    await run_in_threadpool(repo.preflight, str(session_id), expected_session_revision)
    raw = await request.body()
    media = request.headers.get("content-type", "").split(";")[0].strip().lower()
    pages = await run_in_threadpool(extract_pages, filename, media, raw)
    return await run_in_threadpool(
        repo.ingest,
        str(session_id),
        expected_session_revision,
        filename,
        media,
        raw,
        pages,
    )


@router.get("/documents", response_model=list[DocumentRecord])
def listing(session_id: UUID, request: Request):
    return request.app.state.evidence.list_documents(str(session_id))


@router.get("/documents/{document_id}/content")
def original(session_id: UUID, document_id: UUID, request: Request):
    row = request.app.state.evidence.document(str(session_id), str(document_id))
    return Response(
        row["raw"],
        media_type=row["media_type"],
        headers={
            "Content-Disposition": "attachment; filename*=UTF-8''"
            + quote(row["filename"], safe=""),
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.get("/documents/{document_id}/pages/{page}")
def page_text(session_id: UUID, document_id: UUID, page: int, request: Request):
    row = request.app.state.evidence.document(str(session_id), str(document_id))
    if not 1 <= page <= len(row["pages"]):
        raise BackendError("page_not_found", "The extracted page does not exist.", 404)
    return {
        "document_id": str(document_id),
        "version_id": row["version_id"],
        "page": page,
        "text": row["pages"][page - 1],
        "offset_basis": "Unicode character offsets in this extracted text",
    }


@router.post("/evidence/search", response_model=EvidenceSnapshot, status_code=201)
def search(session_id: UUID, payload: SearchRequest, request: Request):
    return request.app.state.evidence.search(str(session_id), payload)


@router.get("/evidence/snapshots/{snapshot_id}", response_model=EvidenceSnapshot)
def snapshot(session_id: UUID, snapshot_id: UUID, request: Request):
    return request.app.state.evidence.snapshot(str(session_id), str(snapshot_id))
