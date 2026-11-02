import json
from uuid import uuid4
import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from app.db.database import Database
from app.decisions.schemas import BriefUpdate
from conftest import envelope


def seed(
    c,
    raw=b"Only a library pilot is approved. Full deployment is not approved.",
    limit=3,
    query="deployment approved",
):
    r = c.post("/api/v1/sessions", json={"query": "Is full deployment approved?"})
    assert r.status_code == 201, r.text
    p = "/api/v1/sessions/" + r.json()["session_id"]
    r = c.post(
        p + "/documents?filename=policy.txt&expected_session_revision=1",
        content=raw,
        headers={"Content-Type": "text/plain"},
    )
    assert r.status_code == 201, r.text
    s = c.post(
        p + "/evidence/search",
        json={"query": query, "expected_session_revision": 1, "limit": limit},
    )
    assert s.status_code == 201, s.text
    return p, s.json()


def payload(s):
    return {
        "snapshot_id": s["snapshot_id"],
        "expected_session_revision": 1,
        "idempotency_key": str(uuid4()),
    }


def grounded(req):
    body = json.loads(req.content)
    source = json.loads(body["messages"][1]["content"])["sources"][0]["id"]
    return httpx.Response(
        200,
        json=envelope(
            json.dumps(
                {
                    "answer": "Full deployment is not approved.",
                    "source_ids": [source],
                    "limitations": ["Only the retrieved policy passage was assessed."],
                    "insufficient_evidence": False,
                }
            )
        ),
    )


def test_completed_answer_replay_provenance_restart(api_factory):
    app, calls = api_factory(chat=grounded)
    with TestClient(app, base_url="http://localhost") as c:
        p, s = seed(c)
        req = payload(s)
        r = c.post(p + "/answers", json=req)
        assert r.status_code == 200, r.text
        a = r.json()
        assert a["evidence"] == s
        assert a["brief"]["query"] == "Is full deployment approved?"
        assert a["response"]["assessment"]["source_ids"] == [
            s["passages"][0]["source_id"]
        ]
        assert a["response"]["validation"]["semantic_support_verified"] is False
        assert len(a["model_input_sha256"]) == 64
        assert a["response"]["model_digest"] == "a" * 64
        assert c.post(p + "/answers", json=req).json() == a
        assert len([r for r in calls if r.url.path == "/api/chat"]) == 1
        assert c.get(p + "/answers").json()["total"] == 1
        assert c.get(p + "/hypotheses").json()["total"] == 0
    app2, calls2 = api_factory(chat=grounded)
    with TestClient(app2, base_url="http://localhost") as c:
        assert c.get(p + "/answers/" + a["answer_id"]).json() == a
        assert c.post(p + "/answers", json=req).json() == a
        assert not calls2


def test_cross_session_and_unknown_snapshot(client):
    p, s = seed(client)
    p2, _ = seed(client)
    for target in [p2, p]:
        req = payload(s)
        if target == p:
            req["snapshot_id"] = str(uuid4())
        assert client.post(target + "/answers", json=req).status_code == 404


def test_empty_evidence_no_model(api_factory):
    app, calls = api_factory()
    with TestClient(app, base_url="http://localhost") as c:
        p, s = seed(c, query="unrelatedzebra")
        r = c.post(p + "/answers", json=payload(s))
        assert r.status_code == 422, r.text
        assert r.json()["error"]["code"] == "no_evidence"
        assert not calls
        assert c.get(p + "/answers").json()["total"] == 0


def test_stale_snapshot_and_key_conflict(api_factory):
    app, calls = api_factory(chat=grounded)
    with TestClient(app, base_url="http://localhost") as c:
        p, s = seed(c)
        req = payload(s)
        a = c.post(p + "/answers", json=req)
        assert a.status_code == 200, a.text
        assert (
            c.post(p + "/answers", json=req | {"snapshot_id": str(uuid4())}).json()[
                "error"
            ]["code"]
            == "idempotency_conflict"
        )
        brief = c.get(p).json()["brief"]
        brief["query"] = "Should we expand the library pilot?"
        r = c.patch(
            p,
            json={
                "expected_revision": 1,
                "brief": brief,
                "revision_reason": "New question",
            },
        )
        assert r.status_code == 200, r.text
        assert c.post(p + "/answers", json=req).json() == a.json()
        assert c.post(p + "/answers", json=payload(s)).status_code == 409
        assert (
            c.post(
                p + "/answers", json=payload(s) | {"expected_session_revision": 2}
            ).status_code
            == 409
        )
        assert len([r for r in calls if r.url.path == "/api/chat"]) == 1


@pytest.mark.parametrize(
    "kind", ["invalid_citation", "no_citation", "invalid_json", "unavailable"]
)
def test_model_errors_do_not_save(api_factory, kind):
    def chat(req):
        if kind == "unavailable":
            return httpx.Response(503)
        content = (
            "not JSON"
            if kind == "invalid_json"
            else json.dumps(
                {
                    "answer": "Unverified answer",
                    "source_ids": ["invented"] if kind == "invalid_citation" else [],
                    "limitations": ["Test"],
                    "insufficient_evidence": False,
                }
            )
        )
        return httpx.Response(200, json=envelope(content))

    app, calls = api_factory(chat=chat)
    with TestClient(app, base_url="http://localhost") as c:
        p, s = seed(c)
        r = c.post(p + "/answers", json=payload(s))
        assert r.status_code >= 400, r.text
        assert c.get(p + "/answers").json()["total"] == 0
        assert len([r for r in calls if r.url.path == "/api/chat"]) <= 2


def test_abstention_saved(api_factory):
    def chat(req):
        return httpx.Response(
            200,
            json=envelope(
                json.dumps(
                    {
                        "answer": "The supplied evidence is insufficient.",
                        "source_ids": [],
                        "limitations": ["A later policy is needed."],
                        "insufficient_evidence": True,
                    }
                )
            ),
        )

    app, _ = api_factory(chat=chat)
    with TestClient(app, base_url="http://localhost") as c:
        p, s = seed(c)
        r = c.post(p + "/answers", json=payload(s))
        assert r.status_code == 200, r.text
        assert r.json()["response"]["assessment"]["insufficient_evidence"] is True


def test_prompt_overflow_does_not_truncate_or_call(api_factory):
    app, calls = api_factory()
    with TestClient(app, base_url="http://localhost") as c:
        p, s = seed(c)
        brief = c.get(p).json()["brief"]
        brief["query"] = "deployment " + ("界" * 1900)
        assert (
            c.patch(
                p,
                json={
                    "expected_revision": 1,
                    "brief": brief,
                    "revision_reason": "Long question",
                },
            ).status_code
            == 200
        )
        s = c.post(
            p + "/evidence/search",
            json={"query": "deployment", "expected_session_revision": 2},
        ).json()
        r = c.post(p + "/answers", json=payload(s) | {"expected_session_revision": 2})
        assert r.status_code == 422, r.text
        assert r.json()["error"]["code"] == "prompt_budget_exceeded"
        assert not calls


def test_excess_passages_no_silent_drop(api_factory):
    app, calls = api_factory()
    with TestClient(app, base_url="http://localhost") as c:
        p, s = seed(c, raw=("deployment approved " * 130).encode(), limit=5)
        assert len(s["passages"]) == 5
        r = c.post(p + "/answers", json=payload(s))
        assert r.status_code == 422
        assert r.json()["error"]["code"] == "evidence_limit"
        assert not calls


def test_changed_brief_during_inference_rejects_completion(api_factory):
    holder = {}

    def chat(req):
        sid = holder["path"].split("/")[-1]
        brief = app.state.decisions.get_session(sid).brief.model_dump()
        brief["query"] = "Should we pause the pilot instead?"
        app.state.decisions.update_session(
            sid,
            BriefUpdate.model_validate(
                {
                    "expected_revision": 1,
                    "brief": brief,
                    "revision_reason": "Question changed during inference",
                }
            ),
        )
        return grounded(req)

    app, _ = api_factory(chat=chat)
    with TestClient(app, base_url="http://localhost") as c:
        p, s = seed(c)
        holder.update(client=c, path=p)
        r = c.post(p + "/answers", json=payload(s))
        assert r.status_code == 409, r.text
        assert c.get(p + "/answers").json()["total"] == 0


def test_answer_immutability_and_ownership(api_factory, isolated_database):
    app, _ = api_factory(chat=grounded)
    with TestClient(app, base_url="http://localhost") as c:
        p, s = seed(c)
        a = c.post(p + "/answers", json=payload(s)).json()
        p2, _ = seed(c)
        assert c.get(p2 + "/answers/" + a["answer_id"]).status_code == 404
        assert c.get(p + "/answers/" + str(uuid4())).status_code == 404
        assert c.get(p + "/answers?limit=21").status_code == 422
        assert c.get(p + "/answers?offset=-1").status_code == 422
        assert c.get(p + "/answers?offset=1").json()["items"] == []
    db = Database(isolated_database)
    for sql in [
        "DELETE FROM saved_answers",
        "UPDATE saved_answers SET idempotency_key='new'",
    ]:
        with pytest.raises(IntegrityError):
            with db.engine.begin() as conn:
                conn.execute(text(sql))
    db.close()


@pytest.mark.parametrize(
    "field,value",
    [
        ("snapshot_id", "bad"),
        ("idempotency_key", "bad"),
        ("expected_session_revision", 0),
    ],
)
def test_request_validation(client, field, value):
    p, s = seed(client)
    assert (
        client.post(p + "/answers", json=payload(s) | {field: value}).status_code == 422
    )


def test_model_timeout_releases_locks_and_allows_retry(api_factory):
    import asyncio
    from app.core.config import Settings

    app, _ = api_factory(
        settings=Settings(_env_file=None, request_timeout_seconds=0.02)
    )
    with TestClient(app, base_url="http://localhost") as c:
        p, s = seed(c)
        req = payload(s)
        original = app.state.provider.generate

        async def slow(*args):
            await asyncio.sleep(1)

        app.state.provider.generate = slow
        r = c.post(p + "/answers", json=req)
        assert r.status_code == 504, r.text
        assert c.get(p + "/answers").json()["total"] == 0
        assert not app.state.answer_service._lock.locked()
        assert not app.state.baseline._lock.locked()

        async def ok(messages, schema):
            source = json.loads(messages[1]["content"])["sources"][0]["id"]
            return envelope(
                json.dumps(
                    {
                        "answer": "Full deployment is not approved.",
                        "source_ids": [source],
                        "limitations": ["Synthetic policy only"],
                        "insufficient_evidence": False,
                    }
                )
            )

        app.state.provider.generate = ok
        app.state.baseline.settings.request_timeout_seconds = 2
        assert c.post(p + "/answers", json=req).status_code == 200


def test_concurrent_answers_and_baseline_share_capacity(api_factory):
    import asyncio
    from app.answers.schemas import AnswerRequest
    from app.core.errors import BackendError
    from app.schemas import BaselineRequest

    app, _ = api_factory()
    with TestClient(app, base_url="http://localhost") as c:
        p, s = seed(c)
        sid = p.split("/")[-1]
        req = AnswerRequest.model_validate(payload(s))

        async def scenario():
            entered = asyncio.Event()
            release = asyncio.Event()

            async def generate(messages, schema):
                entered.set()
                await release.wait()
                source = json.loads(messages[1]["content"])["sources"][0]["id"]
                return envelope(
                    json.dumps(
                        {
                            "answer": "Full deployment is not approved.",
                            "source_ids": [source],
                            "limitations": ["Synthetic policy only"],
                            "insufficient_evidence": False,
                        }
                    )
                )

            app.state.provider.generate = generate
            task = asyncio.create_task(
                app.state.answer_service.run(sid, req, "concurrency-test")
            )
            await asyncio.wait_for(entered.wait(), 2)
            try:
                with pytest.raises(BackendError) as e:
                    await app.state.answer_service.run(sid, req, "duplicate")
                assert e.value.status == 429
                with pytest.raises(BackendError) as e:
                    await app.state.baseline.run(
                        BaselineRequest(question="Should deployment proceed?"),
                        "baseline",
                    )
                assert e.value.status == 429
            finally:
                release.set()
            result = await task
            assert result.evidence.snapshot_id == s["snapshot_id"]

        c.portal.call(scenario)
        assert c.get(p + "/answers").json()["total"] == 1


def test_upgrade_from_increment3_preserves_briefs_and_snapshots(tmp_path):
    from alembic import command
    from alembic.config import Config
    from pathlib import Path
    from app.db.database import make_engine
    from app.db.migrate import upgrade_database
    from app.db.tables import sessions, briefs
    from app.evidence.tables import retrievals
    from sqlalchemy import insert, select

    path = tmp_path / "previous.sqlite3"
    engine = make_engine(path)
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    config.set_main_option(
        "script_location", str(Path(__file__).resolve().parents[1] / "migrations")
    )
    sid = str(uuid4())
    snapshot = str(uuid4())
    with engine.connect() as conn:
        config.attributes["connection"] = conn
        command.upgrade(config, "0002_evidence")
    from app.decisions.schemas import DecisionBrief

    old = {
        "snapshot_id": snapshot,
        "session_id": sid,
        "brief_revision": 1,
        "query": "policy",
        "passages": [],
        "document_version_ids": [],
        "created_at": "2026-01-01T00:00:00+00:00",
    }
    with engine.begin() as conn:
        conn.execute(
            insert(sessions).values(
                id=sid, revision=1, created_at="test", updated_at="test"
            )
        )
        conn.execute(
            insert(briefs).values(
                session_id=sid,
                revision=1,
                brief=DecisionBrief(query="Is full deployment approved?").model_dump(),
                reason="original",
                created_at="test",
            )
        )
        conn.execute(
            insert(retrievals).values(
                id=snapshot, session_id=sid, brief_revision=1, result=old
            )
        )
    engine.dispose()
    upgrade_database(path)
    upgrade_database(path)
    db = Database(path)
    assert db.ready()
    with db.transaction() as conn:
        assert conn.execute(select(retrievals.c.result)).scalar_one() == old
        assert conn.execute(select(briefs.c.reason)).scalar_one() == "original"
    db.close()
