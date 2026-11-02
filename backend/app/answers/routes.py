import asyncio
from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Request, Query
from starlette.concurrency import run_in_threadpool
from app.core.errors import BackendError
from app.answers.schemas import AnswerRequest, SavedAnswer, AnswerList

router = APIRouter(
    prefix="/api/v1/sessions/{session_id}/answers",
    tags=["Saved document-grounded answers"],
)


class AnswerService:
    def __init__(self, repository, baseline):
        self.repository, self.baseline = repository, baseline
        self._lock = asyncio.Lock()

    async def run(self, sid, payload, request_id):
        # Serialise preparation through commit. The baseline's shared lock also guards /baseline.
        if self._lock.locked():
            raise BackendError(
                "answer_busy",
                "One saved-answer request is active. Retry with the same key after it completes.",
                429,
                True,
            )
        async with self._lock:
            prepared = await run_in_threadpool(self.repository.prepare, sid, payload)
            if isinstance(prepared, SavedAnswer):
                return prepared
            brief, snapshot, model_request = prepared
            response = await self.baseline.run(model_request, request_id)
            return await run_in_threadpool(
                self.repository.save,
                sid,
                payload,
                brief,
                snapshot,
                model_request,
                response,
            )


@router.post("", response_model=SavedAnswer)
async def generate(session_id: UUID, payload: AnswerRequest, request: Request):
    return await request.app.state.answer_service.run(
        str(session_id), payload, request.state.request_id
    )


@router.get("", response_model=AnswerList)
def listing(
    session_id: UUID,
    request: Request,
    limit: Annotated[int, Query(ge=1, le=20)] = 10,
    offset: Annotated[int, Query(ge=0, le=100000)] = 0,
):
    return request.app.state.answers.listing(str(session_id), limit, offset)


@router.get("/{answer_id}", response_model=SavedAnswer)
def get(session_id: UUID, answer_id: UUID, request: Request):
    return request.app.state.answers.get(str(session_id), str(answer_id))
