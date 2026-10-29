from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Request

from app.decisions.schemas import (BriefUpdate, BriefVersion, DecisionBrief, HypothesisCreate,
    HypothesisHistory, HypothesisPage, HypothesisRecord, HypothesisRevision, HypothesisTransition,
    SessionPage, SessionRecord)

router = APIRouter(prefix="/api/v1/sessions", tags=["Saved decisions"])
Limit = Annotated[int, Query(ge=1, le=50)]
Offset = Annotated[int, Query(ge=0, le=100000)]


def repository(request):
    return request.app.state.decisions


@router.post("", response_model=SessionRecord, status_code=201)
def create_session(payload: DecisionBrief, request: Request):
    return repository(request).create_session(payload)


@router.get("", response_model=SessionPage)
def list_sessions(request: Request, limit: Limit = 20, offset: Offset = 0):
    return repository(request).list_sessions(limit, offset)


@router.get("/{session_id}", response_model=SessionRecord)
def get_session(session_id: UUID, request: Request):
    return repository(request).get_session(str(session_id))


@router.patch("/{session_id}", response_model=SessionRecord)
def update_session(session_id: UUID, payload: BriefUpdate, request: Request):
    return repository(request).update_session(str(session_id), payload)


@router.get("/{session_id}/brief-versions", response_model=list[BriefVersion])
def brief_history(session_id: UUID, request: Request, limit: Limit = 20, offset: Offset = 0):
    return repository(request).brief_history(str(session_id), limit, offset)


@router.post("/{session_id}/hypotheses", response_model=HypothesisRecord, status_code=201)
def create_hypothesis(session_id: UUID, payload: HypothesisCreate, request: Request):
    return repository(request).create_hypothesis(str(session_id), payload)


@router.get("/{session_id}/hypotheses", response_model=HypothesisPage)
def list_hypotheses(session_id: UUID, request: Request):
    return repository(request).list_hypotheses(str(session_id))


@router.get("/{session_id}/hypotheses/{hypothesis_id}", response_model=HypothesisRecord)
def get_hypothesis(session_id: UUID, hypothesis_id: UUID, request: Request):
    return repository(request).get_hypothesis(str(session_id), str(hypothesis_id))


@router.get("/{session_id}/hypotheses/{hypothesis_id}/versions", response_model=HypothesisHistory)
def hypothesis_history(session_id: UUID, hypothesis_id: UUID, request: Request, limit: Limit = 20, offset: Offset = 0):
    return repository(request).hypothesis_history(str(session_id), str(hypothesis_id), limit, offset)


@router.post("/{session_id}/hypotheses/{hypothesis_id}/revisions", response_model=HypothesisRecord, status_code=201)
def revise_hypothesis(session_id: UUID, hypothesis_id: UUID, payload: HypothesisRevision, request: Request):
    return repository(request).revise_hypothesis(str(session_id), str(hypothesis_id), payload)


@router.post("/{session_id}/hypotheses/{hypothesis_id}/transitions", response_model=HypothesisRecord)
def transition(session_id: UUID, hypothesis_id: UUID, payload: HypothesisTransition, request: Request):
    return repository(request).transition(str(session_id), str(hypothesis_id), payload)
