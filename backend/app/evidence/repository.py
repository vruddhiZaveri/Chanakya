import hashlib
from uuid import uuid4
from sqlalchemy import select, insert, func, and_
from app.core.errors import BackendError
from app.db.tables import sessions
from app.decisions.repository import now, conflict
from app.evidence.tables import documents, passages, retrievals
from app.evidence.schemas import DocumentRecord, EvidenceSnapshot, Passage
from app.evidence.extraction import chunks
from app.evidence.retrieval import rank


class EvidenceRepository:
    def __init__(self, database):
        self.database = database

    def _session(self, c, identity, revision=None):
        row = (
            c.execute(select(sessions).where(sessions.c.id == identity))
            .mappings()
            .first()
        )
        if row is None:
            raise BackendError(
                "session_not_found", "The decision session does not exist.", 404
            )
        if revision is not None and row["revision"] != revision:
            raise conflict()
        return row

    def preflight(self, identity, revision):
        with self.database.transaction() as c:
            self._session(c, identity, revision)

    def _document(self, c, sid, did):
        row = (
            c.execute(
                select(documents).where(
                    and_(documents.c.id == did, documents.c.session_id == sid)
                )
            )
            .mappings()
            .first()
        )
        if row is None:
            raise BackendError(
                "document_not_found",
                "This document does not belong to the requested session.",
                404,
            )
        return row

    def _record(self, c, row):
        return DocumentRecord(
            document_id=row["id"],
            version_id=row["version_id"],
            session_id=row["session_id"],
            filename=row["filename"],
            media_type=row["media_type"],
            sha256=row["sha256"],
            byte_size=row["byte_size"],
            page_count=len(row["pages"]),
            empty_pages=[i for i, p in enumerate(row["pages"], 1) if not p.strip()],
            passage_count=c.scalar(
                select(func.count())
                .select_from(passages)
                .where(passages.c.document_id == row["id"])
            ),
            created_at=row["created_at"],
        )

    def ingest(self, sid, revision, filename, media, raw, pages):
        digest = hashlib.sha256(raw).hexdigest()
        with self.database.transaction(write=True) as c:
            self._session(c, sid, revision)
            prior = (
                c.execute(
                    select(documents).where(
                        and_(
                            documents.c.session_id == sid, documents.c.sha256 == digest
                        )
                    )
                )
                .mappings()
                .first()
            )
            if prior:
                return self._record(c, prior)
            if (
                c.scalar(
                    select(func.count())
                    .select_from(documents)
                    .where(documents.c.session_id == sid)
                )
                >= 10
            ):
                raise BackendError(
                    "document_limit",
                    "At most ten immutable documents are permitted per session.",
                    409,
                )
            did, vid = str(uuid4()), str(uuid4())
            c.execute(
                insert(documents).values(
                    id=did,
                    version_id=vid,
                    session_id=sid,
                    filename=filename,
                    media_type=media,
                    sha256=digest,
                    byte_size=len(raw),
                    raw=raw,
                    pages=pages,
                    created_at=now(),
                )
            )
            rows = [
                r | {"document_id": did, "session_id": sid} for r in chunks(vid, pages)
            ]
            c.execute(insert(passages), rows)
            return self._record(c, self._document(c, sid, did))

    def list_documents(self, sid):
        with self.database.transaction() as c:
            self._session(c, sid)
            return [
                self._record(c, r)
                for r in c.execute(
                    select(documents)
                    .where(documents.c.session_id == sid)
                    .order_by(documents.c.created_at, documents.c.id)
                ).mappings()
            ]

    def document(self, sid, did):
        with self.database.transaction() as c:
            self._session(c, sid)
            return dict(self._document(c, sid, did))

    def search(self, sid, payload):
        with self.database.transaction(write=True) as c:
            self._session(c, sid, payload.expected_session_revision)
            corpus = list(
                c.execute(
                    select(documents)
                    .where(documents.c.session_id == sid)
                    .order_by(documents.c.id)
                ).mappings()
            )
            requested = set(payload.document_ids)
            if len(requested) != len(payload.document_ids):
                raise BackendError(
                    "invalid_document_selection",
                    "Selected document IDs must be distinct.",
                    422,
                )
            if requested - set(r["id"] for r in corpus):
                raise BackendError(
                    "document_not_found",
                    "A selected document does not belong to this session.",
                    404,
                )
            corpus = [r for r in corpus if not requested or r["id"] in requested]
            selected = {r["id"]: r for r in corpus}
            rows = list(
                c.execute(
                    select(passages).where(passages.c.document_id.in_(list(selected)))
                ).mappings()
            )
            ranked = rank(rows, payload.query, payload.limit)
            result = EvidenceSnapshot(
                snapshot_id=str(uuid4()),
                session_id=sid,
                brief_revision=payload.expected_session_revision,
                query=payload.query,
                created_at=now(),
                document_version_ids=[r["version_id"] for r in corpus],
                passages=[
                    Passage(
                        source_id=r["id"],
                        document_id=r["document_id"],
                        document_version_id=selected[r["document_id"]]["version_id"],
                        filename=selected[r["document_id"]]["filename"],
                        document_sha256=selected[r["document_id"]]["sha256"],
                        page=r["page"],
                        start_char=r["start_char"],
                        end_char=r["end_char"],
                        excerpt=r["excerpt"],
                        score=r["score"],
                    )
                    for r in ranked
                ],
            )
            c.execute(
                insert(retrievals).values(
                    id=result.snapshot_id,
                    session_id=sid,
                    brief_revision=result.brief_revision,
                    result=result.model_dump(),
                )
            )
            return result

    def snapshot(self, sid, identity):
        with self.database.transaction() as c:
            self._session(c, sid)
            row = (
                c.execute(
                    select(retrievals).where(
                        and_(
                            retrievals.c.id == identity, retrievals.c.session_id == sid
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
            return EvidenceSnapshot.model_validate(row["result"])
