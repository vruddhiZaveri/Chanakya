import hashlib
import json
from uuid import uuid4
from sqlalchemy import select, insert, and_, func
from app.core.errors import BackendError
from app.db.tables import briefs
from app.decisions.repository import now, conflict
from app.evidence.schemas import EvidenceSnapshot
from app.evidence.tables import retrievals
from app.schemas import BaselineRequest, SuppliedSource
from app.answers.schemas import SavedAnswer, AnswerList
from app.answers.tables import answers


def canonical(payload):
    return json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )


class AnswerRepository:
    def __init__(self, database, evidence):
        self.database, self.evidence = database, evidence

    def _prior(self, c, sid, payload):
        row = (
            c.execute(
                select(answers).where(
                    and_(
                        answers.c.session_id == sid,
                        answers.c.idempotency_key == str(payload.idempotency_key),
                    )
                )
            )
            .mappings()
            .first()
        )
        if row is None:
            return None
        if (
            row["snapshot_id"] != str(payload.snapshot_id)
            or row["brief_revision"] != payload.expected_session_revision
        ):
            raise BackendError(
                "idempotency_conflict",
                "This key already identifies a different answer request. Use a new key for a new request.",
                409,
            )
        return SavedAnswer.model_validate(row["result"])

    def prepare(self, sid, payload):
        with self.database.transaction() as c:
            self.evidence._session(c, sid)
            prior = self._prior(c, sid, payload)
            if prior:
                return prior
            self.evidence._session(c, sid, payload.expected_session_revision)
            row = (
                c.execute(
                    select(retrievals).where(
                        and_(
                            retrievals.c.id == str(payload.snapshot_id),
                            retrievals.c.session_id == sid,
                        )
                    )
                )
                .mappings()
                .first()
            )
            if row is None:
                raise BackendError(
                    "snapshot_not_found",
                    "This retrieval snapshot does not belong to the session.",
                    404,
                )
            if row["brief_revision"] != payload.expected_session_revision:
                raise conflict()
            snapshot = EvidenceSnapshot.model_validate(row["result"])
            if not snapshot.passages:
                raise BackendError(
                    "no_evidence",
                    "The snapshot has no matching passages. Upload relevant documents and retrieve evidence first.",
                    422,
                )
            if len(snapshot.passages) > 3:
                raise BackendError(
                    "evidence_limit",
                    "Retrieve at most three passages for this bounded model workflow; use search limit=3 or less.",
                    422,
                )
            brief = c.execute(
                select(briefs.c.brief).where(
                    and_(
                        briefs.c.session_id == sid,
                        briefs.c.revision == payload.expected_session_revision,
                    )
                )
            ).scalar_one()
            # The saved brief supplies the question; the retrieval query is not a substitute.
            model_request = BaselineRequest(
                mode="source_grounded",
                question=brief["query"],
                sources=[
                    SuppliedSource(id=p.source_id, title=p.filename, excerpt=p.excerpt)
                    for p in snapshot.passages
                ],
            )
            return brief, snapshot, model_request

    def save(self, sid, payload, brief, snapshot, model_request, response):
        with self.database.transaction(write=True) as c:
            self.evidence._session(c, sid)
            prior = self._prior(c, sid, payload)
            if prior:
                return prior
            # No write transaction is held during inference. Reject a stale completion.
            self.evidence._session(c, sid, payload.expected_session_revision)
            result = SavedAnswer(
                answer_id=str(uuid4()),
                session_id=sid,
                brief_revision=payload.expected_session_revision,
                idempotency_key=str(payload.idempotency_key),
                created_at=now(),
                brief=brief,
                evidence=snapshot,
                model_input_sha256=hashlib.sha256(
                    canonical(model_request.model_dump()).encode("utf-8")
                ).hexdigest(),
                response=response,
            )
            c.execute(
                insert(answers).values(
                    id=result.answer_id,
                    session_id=sid,
                    brief_revision=result.brief_revision,
                    snapshot_id=snapshot.snapshot_id,
                    idempotency_key=result.idempotency_key,
                    result=result.model_dump(mode="json"),
                )
            )
            return result

    def get(self, sid, identity):
        with self.database.transaction() as c:
            self.evidence._session(c, sid)
            row = c.execute(
                select(answers.c.result).where(
                    and_(answers.c.id == identity, answers.c.session_id == sid)
                )
            ).scalar_one_or_none()
            if row is None:
                raise BackendError(
                    "answer_not_found",
                    "This saved answer does not belong to the session.",
                    404,
                )
            return SavedAnswer.model_validate(row)

    def listing(self, sid, limit, offset):
        with self.database.transaction() as c:
            self.evidence._session(c, sid)
            where = answers.c.session_id == sid
            total = c.scalar(select(func.count()).select_from(answers).where(where))
            rows = (
                c.execute(
                    select(answers.c.result)
                    .where(where)
                    .order_by(answers.c.id)
                    .limit(limit)
                    .offset(offset)
                )
                .scalars()
                .all()
            )
            return AnswerList(
                items=[SavedAnswer.model_validate(r) for r in rows],
                total=total,
                limit=limit,
                offset=offset,
            )
