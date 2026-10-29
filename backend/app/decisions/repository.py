from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import and_, func, insert, select, update

from app.core.errors import BackendError
from app.db.tables import briefs, hypotheses, sessions, versions
from app.decisions.schemas import (BriefVersion, DecisionBrief, HypothesisHistory,
    HypothesisPage, HypothesisRecord, HypothesisVersion, SessionPage, SessionRecord)


def now():
    return datetime.now(timezone.utc).isoformat()


def conflict(message="The record changed. Reload it and use its current revision."):
    return BackendError("revision_conflict", message, 409)


class DecisionRepository:
    def __init__(self, database):
        self.database = database

    def _session(self, connection, session_id):
        row = connection.execute(select(sessions).where(sessions.c.id == session_id)).mappings().first()
        if row is None:
            raise BackendError("session_not_found", "The decision session does not exist.", 404)
        return row

    def _brief(self, connection, session_id, revision):
        return connection.execute(select(briefs).where(and_(briefs.c.session_id == session_id, briefs.c.revision == revision))).mappings().one()

    def _session_record(self, connection, row):
        brief = self._brief(connection, row["id"], row["revision"])
        count = connection.scalar(select(func.count()).select_from(hypotheses).where(hypotheses.c.session_id == row["id"]))
        return SessionRecord(session_id=row["id"], revision=row["revision"], brief=DecisionBrief.model_validate(brief["brief"]),
                             created_at=row["created_at"], updated_at=row["updated_at"], hypothesis_count=count)

    def create_session(self, brief):
        identity, timestamp = str(uuid4()), now()
        with self.database.transaction(write=True) as connection:
            connection.execute(insert(sessions).values(id=identity, revision=1, created_at=timestamp, updated_at=timestamp))
            connection.execute(insert(briefs).values(session_id=identity, revision=1, brief=brief.model_dump(), reason="Initial user brief", created_at=timestamp))
            return self._session_record(connection, self._session(connection, identity))

    def get_session(self, identity):
        with self.database.transaction() as connection:
            return self._session_record(connection, self._session(connection, identity))

    def list_sessions(self, limit, offset):
        with self.database.transaction() as connection:
            total = connection.scalar(select(func.count()).select_from(sessions))
            rows = connection.execute(select(sessions).order_by(sessions.c.updated_at.desc(), sessions.c.id).limit(limit).offset(offset)).mappings()
            return SessionPage(items=[self._session_record(connection, row) for row in rows], total=total, offset=offset, limit=limit)

    def update_session(self, identity, payload):
        with self.database.transaction(write=True) as connection:
            current = self._session(connection, identity)
            if current["revision"] != payload.expected_revision:
                raise conflict()
            if self._brief(connection, identity, current["revision"])["brief"] == payload.brief.model_dump():
                raise BackendError("no_change", "The brief is unchanged; no version was created.", 409)
            revision, timestamp = current["revision"] + 1, now()
            connection.execute(insert(briefs).values(session_id=identity, revision=revision, brief=payload.brief.model_dump(), reason=payload.revision_reason, created_at=timestamp))
            result = connection.execute(update(sessions).where(and_(sessions.c.id == identity, sessions.c.revision == payload.expected_revision)).values(revision=revision, updated_at=timestamp))
            if result.rowcount != 1:
                raise conflict()
            return self._session_record(connection, self._session(connection, identity))

    def brief_history(self, identity, limit, offset):
        with self.database.transaction() as connection:
            self._session(connection, identity)
            rows = connection.execute(select(briefs).where(briefs.c.session_id == identity).order_by(briefs.c.revision).limit(limit).offset(offset)).mappings()
            return [BriefVersion(session_id=identity, revision=row["revision"], brief=DecisionBrief.model_validate(row["brief"]), revision_reason=row["reason"], created_at=row["created_at"]) for row in rows]

    def _hypothesis(self, connection, session_id, identity):
        row = connection.execute(select(hypotheses).where(and_(hypotheses.c.id == identity, hypotheses.c.session_id == session_id))).mappings().first()
        if row is None:
            raise BackendError("hypothesis_not_found", "This hypothesis does not belong to the requested session.", 404)
        return row

    def _version(self, connection, identity, revision):
        return connection.execute(select(versions).where(and_(versions.c.hypothesis_id == identity, versions.c.revision == revision))).mappings().one()

    def _version_record(self, row):
        return HypothesisVersion(version_id=row["id"], hypothesis_id=row["hypothesis_id"], revision=row["revision"],
            previous_version_id=row["previous_version_id"], brief_revision=row["brief_revision"], content=row["content"],
            status=row["status"], revision_reason=row["reason"], created_at=row["created_at"])

    def _record(self, connection, row, session):
        current = self._version(connection, row["id"], row["revision"])
        return HypothesisRecord(hypothesis_id=row["id"], session_id=row["session_id"], current=self._version_record(current),
            context_outdated=current["brief_revision"] != session["revision"], created_at=row["created_at"])

    def _append(self, connection, row, brief_revision, content, status, reason):
        current = self._version(connection, row["id"], row["revision"])
        revision, timestamp = row["revision"] + 1, now()
        connection.execute(insert(versions).values(id=str(uuid4()), hypothesis_id=row["id"], session_id=row["session_id"],
            revision=revision, previous_revision=row["revision"], previous_version_id=current["id"], brief_revision=brief_revision,
            type=content["type"], status=status, content=content, reason=reason, created_at=timestamp))
        result = connection.execute(update(hypotheses).where(and_(hypotheses.c.id == row["id"], hypotheses.c.revision == row["revision"])).values(revision=revision))
        if result.rowcount != 1:
            raise conflict()
        connection.execute(update(sessions).where(sessions.c.id == row["session_id"]).values(updated_at=timestamp))

    def create_hypothesis(self, session_id, payload):
        with self.database.transaction(write=True) as connection:
            session = self._session(connection, session_id)
            if session["revision"] != payload.expected_session_revision:
                raise conflict("The decision brief changed. Review the current brief before adding a hypothesis.")
            count = connection.scalar(select(func.count()).select_from(hypotheses).where(hypotheses.c.session_id == session_id))
            if count >= 3:
                raise BackendError("hypothesis_limit", "A decision supports at most three hypothesis identities in this increment.", 409)
            identity, timestamp = str(uuid4()), now()
            connection.execute(insert(hypotheses).values(id=identity, session_id=session_id, revision=1, created_at=timestamp))
            content = payload.content.model_dump()
            connection.execute(insert(versions).values(id=str(uuid4()), hypothesis_id=identity, session_id=session_id,
                revision=1, previous_revision=None, previous_version_id=None, brief_revision=session["revision"],
                type=content["type"], status="proposed", content=content, reason="Initial human-authored hypothesis", created_at=timestamp))
            connection.execute(update(sessions).where(sessions.c.id == session_id).values(updated_at=timestamp))
            return self._record(connection, self._hypothesis(connection, session_id, identity), session)

    def get_hypothesis(self, session_id, identity):
        with self.database.transaction() as connection:
            session = self._session(connection, session_id)
            return self._record(connection, self._hypothesis(connection, session_id, identity), session)

    def list_hypotheses(self, session_id):
        with self.database.transaction() as connection:
            session = self._session(connection, session_id)
            rows = connection.execute(select(hypotheses).where(hypotheses.c.session_id == session_id).order_by(hypotheses.c.created_at, hypotheses.c.id)).mappings()
            items = [self._record(connection, row, session) for row in rows]
            return HypothesisPage(items=items, total=len(items))

    def hypothesis_history(self, session_id, identity, limit, offset):
        with self.database.transaction() as connection:
            self._session(connection, session_id)
            row = self._hypothesis(connection, session_id, identity)
            rows = connection.execute(select(versions).where(versions.c.hypothesis_id == identity).order_by(versions.c.revision).limit(limit).offset(offset)).mappings()
            return HypothesisHistory(hypothesis_id=identity, session_id=session_id,
                items=[self._version_record(v) for v in rows], total=row["revision"], limit=limit, offset=offset)

    def revise_hypothesis(self, session_id, identity, payload):
        with self.database.transaction(write=True) as connection:
            session = self._session(connection, session_id)
            row = self._hypothesis(connection, session_id, identity)
            if row["revision"] != payload.expected_revision or session["revision"] != payload.expected_session_revision:
                raise conflict()
            current = self._version(connection, identity, row["revision"])
            if current["status"] in {"resolved", "inconclusive"}:
                raise BackendError("terminal_hypothesis", "Terminal history cannot be reopened. Start a new hypothesis or decision.", 409)
            content = payload.content.model_dump()
            if current["content"] == content and current["brief_revision"] == session["revision"]:
                raise BackendError("no_change", "The hypothesis and its brief context are unchanged.", 409)
            self._append(connection, row, session["revision"], content, "revised", payload.revision_reason)
            return self._record(connection, self._hypothesis(connection, session_id, identity), session)

    def transition(self, session_id, identity, payload):
        with self.database.transaction(write=True) as connection:
            session = self._session(connection, session_id)
            row = self._hypothesis(connection, session_id, identity)
            if row["revision"] != payload.expected_revision:
                raise conflict()
            current = self._version(connection, identity, row["revision"])
            if current["brief_revision"] != session["revision"]:
                raise BackendError("context_outdated", "Revise the hypothesis against the current brief before changing its status.", 409)
            if payload.target_status in {"supported", "challenged", "resolved"}:
                raise BackendError("evidence_workflow_not_available", "Evidence-backed transitions require the later evidence and evaluation workflow.", 409)
            allowed = {"proposed": {"under_investigation"}, "revised": {"under_investigation"}, "under_investigation": {"inconclusive"}}
            if payload.target_status not in allowed.get(current["status"], set()):
                raise BackendError("invalid_transition", "This lifecycle transition is not permitted.", 409)
            self._append(connection, row, session["revision"], current["content"], payload.target_status, payload.reason)
            return self._record(connection, self._hypothesis(connection, session_id, identity), session)
