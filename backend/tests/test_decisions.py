from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import insert, text
from sqlalchemy.exc import IntegrityError

from app.core.config import Settings
from app.core.errors import BackendError
from app.db.database import Database
from app.db.migrate import upgrade_database
from app.db.tables import briefs, sessions
from app.decisions.repository import DecisionRepository
from app.decisions.schemas import BriefUpdate, DecisionBrief, HypothesisCreate

BASE = "/api/v1/sessions"
BRIEF = {"query": "Should the organisation approve full deployment?", "domain_key": "education", "constraints": ["Pilot approval only"]}
FACTUAL = {"type": "factual", "claim": "Full deployment is not approved.", "scope": "Synthetic policy; no external verification"}


def session(client, **changes):
    response = client.post(BASE, json=BRIEF | changes)
    assert response.status_code == 201, response.text
    return response.json()


def proposal(client, identity, content=None):
    response = client.post(f"{BASE}/{identity}/hypotheses", json={"expected_session_revision": 1, "content": content or FACTUAL})
    assert response.status_code == 201, response.text
    return response.json()


def test_sessions_survive_app_restart_without_calling_ollama(api_factory):
    app, calls = api_factory()
    with TestClient(app, base_url="http://localhost") as client:
        saved = session(client)
        hypothesis = proposal(client, saved["session_id"])
    second, second_calls = api_factory()
    with TestClient(second, base_url="http://localhost") as client:
        restored = client.get(f"{BASE}/{saved['session_id']}")
        assert restored.status_code == 200
        assert restored.json() == saved | {"hypothesis_count": 1, "updated_at": restored.json()["updated_at"]}
        assert client.get(f"{BASE}/{saved['session_id']}/hypotheses/{hypothesis['hypothesis_id']}").json() == hypothesis
    assert calls == second_calls == []


def test_session_edit_keeps_history_and_rejects_stale_or_identical_write(client):
    saved = session(client)
    path = f"{BASE}/{saved['session_id']}"
    updated = client.patch(path, json={"expected_revision": 1, "brief": BRIEF | {"objective": "Restrict deployment to a pilot"}, "revision_reason": "Clarify objective"})
    assert updated.status_code == 200, updated.text
    assert updated.json()["revision"] == 2
    assert client.patch(path, json={"expected_revision": 1, "brief": BRIEF, "revision_reason": "Stale edit"}).status_code == 409
    assert client.patch(path, json={"expected_revision": 2, "brief": updated.json()["brief"], "revision_reason": "No change"}).status_code == 409
    history = client.get(path + "/brief-versions").json()
    assert [h["revision"] for h in history] == [1, 2]
    assert history[0]["brief"] == saved["brief"]
    assert history[1]["revision_reason"] == "Clarify objective"
    assert len(client.get(path + "/brief-versions?limit=1&offset=1").json()) == 1


def test_session_pagination_and_empty_state(client):
    assert client.get(BASE).json()["items"] == []
    first, second = session(client), session(client, domain_key="custom_domain")
    page = client.get(BASE + "?limit=1&offset=1").json()
    assert page["total"] == 2 and page["items"][0]["session_id"] == first["session_id"]
    assert client.get(BASE + "?limit=51").status_code == 422
    assert client.get(BASE + "?offset=-1").status_code == 422


@pytest.mark.parametrize("change", [
    {"query": "short"}, {"query": " " * 20}, {"domain_key": "../../outside"},
    {"selected_domains": ["law", "law"]}, {"model": "another-model"},
    {"constraints": [""]}, {"objective": ""}, {"specifications": {"": "x"}},
])
def test_invalid_briefs_are_not_saved(client, change):
    response = client.post(BASE, json=BRIEF | change)
    assert response.status_code == 422
    assert client.get(BASE).json()["total"] == 0


@pytest.mark.parametrize("content", [
    FACTUAL,
    {"type": "causal", "claim": "A staged rollout reduces support incidents.", "scope": "Pilot rollout", "cause": "Staged rollout", "effect": "Fewer incidents", "assumptions": ["No simultaneous product change"]},
    {"type": "comparative", "claim": "A pilot is preferable to full deployment.", "scope": "Current budget", "alternatives": ["Pilot", "Full deployment"], "criteria": ["Operational risk"]},
    {"type": "predictive", "claim": "The pilot will meet its acceptance criteria.", "scope": "Pilot users", "measurable_outcome": "Acceptance criteria met", "time_horizon": "By the end of the four-week pilot"},
    {"type": "diagnostic", "claim": "Resource pressure explains the observed failure.", "scope": "Local inference", "latent_state": "Insufficient free memory", "observations": ["Allocation error"]},
    {"type": "normative", "claim": "We should prioritise the safer pilot option.", "scope": "Deployment planning", "values": ["Safety before speed"]},
])
def test_six_types_preserve_structure_and_never_invent_probabilities(client, content):
    saved = session(client)
    result = proposal(client, saved["session_id"], content)
    version = result["current"]
    assert version["status"] == "proposed"
    assert version["content"]["type"] == content["type"]
    assert version["author_kind"] == "human" and version["created_by_execution_id"] is None
    assert version["probability"]["prior"] is None and version["probability"]["posterior"] is None
    assert version["probability"]["status"] == "not_assessed"
    assert version["brief_revision"] == 1


@pytest.mark.parametrize("content", [
    FACTUAL | {"type": "unknown"}, FACTUAL | {"posterior": .99},
    FACTUAL | {"type": "causal", "cause": "A", "effect": "B", "assumptions": []},
    FACTUAL | {"type": "comparative", "alternatives": ["Pilot", "pilot"], "criteria": ["Risk"]},
    FACTUAL | {"type": "predictive", "measurable_outcome": "Success"},
    FACTUAL | {"type": "diagnostic", "latent_state": "Unknown", "observations": []},
    FACTUAL | {"type": "normative", "values": []}, FACTUAL | {"claim": " "},
])
def test_invalid_typed_hypotheses_are_not_saved(client, content):
    saved = session(client)
    path = f"{BASE}/{saved['session_id']}/hypotheses"
    assert client.post(path, json={"expected_session_revision": 1, "content": content}).status_code == 422
    assert client.get(path).json()["total"] == 0


def test_hypothesis_revision_preserves_previous_version(client):
    saved = session(client); identity = saved["session_id"]
    original = proposal(client, identity)
    path = f"{BASE}/{identity}/hypotheses/{original['hypothesis_id']}"
    revision = {"expected_revision": 1, "expected_session_revision": 1, "content": FACTUAL | {"claim": "Only a limited library pilot is approved."}, "revision_reason": "Narrow the claim"}
    response = client.post(path + "/revisions", json=revision)
    assert response.status_code == 201, response.text
    current = response.json()["current"]
    assert current["revision"] == 2 and current["status"] == "revised"
    assert current["previous_version_id"] == original["current"]["version_id"]
    assert client.post(path + "/revisions", json=revision).status_code == 409
    history = client.get(path + "/versions").json()
    assert history["total"] == 2 and history["items"][0] == original["current"]
    assert client.get(path + "/versions?limit=1&offset=1").json()["items"] == [current]


def test_changed_brief_marks_context_outdated_and_requires_explicit_revision(client):
    identity = session(client)["session_id"]
    original = proposal(client, identity)
    path = f"{BASE}/{identity}/hypotheses/{original['hypothesis_id']}"
    assert client.patch(f"{BASE}/{identity}", json={"expected_revision": 1, "brief": BRIEF | {"objective": "New deployment scope"}, "revision_reason": "Scope changed"}).status_code == 200
    assert client.get(path).json()["context_outdated"] is True
    assert client.post(path + "/transitions", json={"expected_revision": 1, "target_status": "under_investigation", "reason": "Review"}).status_code == 409
    result = client.post(path + "/revisions", json={"expected_revision": 1, "expected_session_revision": 2, "content": FACTUAL, "revision_reason": "Reassess against the new brief"})
    assert result.status_code == 201, result.text
    assert result.json()["context_outdated"] is False
    assert result.json()["current"]["brief_revision"] == 2
    assert client.get(path + "/versions").json()["items"][0]["brief_revision"] == 1


def test_lifecycle_is_reasoned_versioned_and_terminal_history_stays_closed(client):
    identity = session(client)["session_id"]; original = proposal(client, identity)
    path = f"{BASE}/{identity}/hypotheses/{original['hypothesis_id']}"
    for target in ["supported", "challenged", "resolved"]:
        denied = client.post(path + "/transitions", json={"expected_revision": 1, "target_status": target, "reason": "No evidence workflow exists yet"})
        assert denied.status_code == 409 and denied.json()["error"]["code"] == "evidence_workflow_not_available"
    assert client.post(path + "/transitions", json={"expected_revision": 1, "target_status": "inconclusive", "reason": "Invalid shortcut"}).status_code == 409
    assert client.post(path + "/transitions", json={"expected_revision": 1, "target_status": "under_investigation", "reason": ""}).status_code == 422
    for revision, target in [(1, "under_investigation"), (2, "inconclusive")]:
        result = client.post(path + "/transitions", json={"expected_revision": revision, "target_status": target, "reason": "User records the investigation state"})
        assert result.status_code == 200, result.text
    assert client.post(path + "/transitions", json={"expected_revision": 3, "target_status": "under_investigation", "reason": "Reopen"}).status_code == 409
    assert client.post(path + "/revisions", json={"expected_revision": 3, "expected_session_revision": 1, "content": FACTUAL, "revision_reason": "Reopen"}).status_code == 409
    history = client.get(path + "/versions").json()["items"]
    assert [v["status"] for v in history] == ["proposed", "under_investigation", "inconclusive"]


def test_session_scoping_unknown_ids_and_strict_revision_fields(client):
    first, second = session(client), session(client)
    original = proposal(client, first["session_id"])
    wrong = f"{BASE}/{second['session_id']}/hypotheses/{original['hypothesis_id']}"
    assert client.get(wrong).status_code == 404
    assert client.post(wrong + "/transitions", json={"expected_revision": 1, "target_status": "under_investigation", "reason": "Review"}).status_code == 404
    assert client.get(f"{BASE}/{uuid4()}").status_code == 404
    assert client.get(BASE + "/not-a-uuid").status_code == 422
    path = f"{BASE}/{first['session_id']}/hypotheses"
    assert client.post(path, json={"expected_session_revision": True, "content": FACTUAL}).status_code == 422
    assert client.post(path, json={"expected_session_revision": 2, "content": FACTUAL}).status_code == 409


def test_hypothesis_cap_is_per_session(client):
    identity = session(client)["session_id"]
    for _ in range(3): proposal(client, identity)
    fourth = client.post(f"{BASE}/{identity}/hypotheses", json={"expected_session_revision": 1, "content": FACTUAL})
    assert fourth.status_code == 409 and fourth.json()["error"]["code"] == "hypothesis_limit"
    assert client.get(f"{BASE}/{identity}").json()["hypothesis_count"] == 3
    assert client.get(f"{BASE}/{identity}/hypotheses").json()["total"] == 3


def test_swagger_origins_and_patch_preflight_work(client):
    for origin in ["http://127.0.0.1:8000", "http://localhost:8000"]:
        response = client.post(BASE, json=BRIEF, headers={"Origin": origin})
        assert response.status_code == 201
        assert response.headers["access-control-allow-origin"] == origin
        preflight = client.options(BASE + "/" + str(uuid4()), headers={"Origin": origin, "Access-Control-Request-Method": "PATCH"})
        assert preflight.status_code == 200


def test_missing_migration_has_honest_health_and_actionable_error(api_factory, tmp_path):
    app, calls = api_factory(settings=Settings(_env_file=None, database_path=tmp_path / "unmigrated.sqlite3"))
    with TestClient(app, base_url="http://localhost") as client:
        assert client.get("/api/v1/health").json()["storage_ready"] is False
        response = client.post(BASE, json=BRIEF)
        assert response.status_code == 503 and response.json()["error"]["code"] == "storage_not_ready"
    assert calls == []


def test_migration_is_repeatable_and_enforces_foreign_keys_and_immutability(isolated_database):
    upgrade_database(isolated_database)
    database = Database(isolated_database); repository = DecisionRepository(database)
    saved = repository.create_session(DecisionBrief.model_validate(BRIEF))
    proposed = repository.create_hypothesis(saved.session_id, HypothesisCreate.model_validate({"expected_session_revision": 1, "content": FACTUAL}))
    try:
        for _ in range(3):
            with database.engine.connect() as connection:
                assert connection.scalar(text("PRAGMA foreign_keys")) == 1
                assert connection.scalar(text("PRAGMA journal_mode")) == "wal"
        for table in ["brief_versions", "hypothesis_versions"]:
            for action in [f"UPDATE {table} SET reason='tampered'", f"DELETE FROM {table}"]:
                with pytest.raises(IntegrityError):
                    with database.engine.begin() as connection: connection.execute(text(action))
        with pytest.raises(IntegrityError):
            with database.engine.begin() as connection:
                connection.execute(insert(briefs).values(session_id=str(uuid4()), revision=1, brief=BRIEF, reason="orphan", created_at="now"))
        assert repository.get_hypothesis(saved.session_id, proposed.hypothesis_id).current.revision == 1
        with database.engine.connect() as connection:
            assert connection.execute(text("PRAGMA foreign_key_check")).all() == []
    finally: database.close()


def test_failed_transaction_does_not_leave_partial_rows(isolated_database):
    database = Database(isolated_database)
    try:
        with pytest.raises(RuntimeError):
            with database.transaction(write=True) as connection:
                connection.execute(insert(sessions).values(id=str(uuid4()), revision=1, created_at="now", updated_at="now"))
                raise RuntimeError("Interrupted before the initial brief was inserted")
        assert DecisionRepository(database).list_sessions(20, 0).total == 0
    finally: database.close()


def test_simultaneous_brief_updates_allow_only_one_winner(isolated_database):
    database = Database(isolated_database); repository = DecisionRepository(database)
    saved = repository.create_session(DecisionBrief.model_validate(BRIEF))
    def update_one(n):
        payload = BriefUpdate.model_validate({"expected_revision": 1, "brief": BRIEF | {"objective": f"Objective {n}"}, "revision_reason": "Concurrent edit"})
        try: return repository.update_session(saved.session_id, payload).revision
        except BackendError as error: return error.code
    try:
        with ThreadPoolExecutor(max_workers=2) as pool: results = list(pool.map(update_one, range(2)))
        assert sorted(map(str, results)) == ["2", "revision_conflict"]
        assert len(repository.brief_history(saved.session_id, 50, 0)) == 2
    finally: database.close()


def test_simultaneous_proposals_cannot_exceed_the_cap(isolated_database):
    database = Database(isolated_database); repository = DecisionRepository(database)
    saved = repository.create_session(DecisionBrief.model_validate(BRIEF))
    payload = HypothesisCreate.model_validate({"expected_session_revision": 1, "content": FACTUAL})
    def create_one(_):
        try: repository.create_hypothesis(saved.session_id, payload); return "created"
        except BackendError as error: return error.code
    try:
        with ThreadPoolExecutor(max_workers=4) as pool: results = list(pool.map(create_one, range(4)))
        assert results.count("created") == 3 and results.count("hypothesis_limit") == 1
        assert repository.list_hypotheses(saved.session_id).total == 3
    finally: database.close()


def test_database_rejects_missing_current_version_and_rolls_back(isolated_database):
    database = Database(isolated_database)
    try:
        with pytest.raises(BackendError) as failure:
            with database.transaction(write=True) as connection:
                connection.execute(insert(sessions).values(id=str(uuid4()), revision=1, created_at="now", updated_at="now"))
                # Commit without the required initial brief must fail its deferred FK.
        assert failure.value.code == "storage_integrity_error"
        assert DecisionRepository(database).list_sessions(20, 0).total == 0
    finally: database.close()


def test_noop_revision_and_claims_without_scope_are_rejected(client):
    identity = session(client)["session_id"]; original = proposal(client, identity)
    path = f"{BASE}/{identity}/hypotheses/{original['hypothesis_id']}"
    result = client.post(path + "/revisions", json={"expected_revision": 1, "expected_session_revision": 1, "content": FACTUAL, "revision_reason": "No change"})
    assert result.status_code == 409 and result.json()["error"]["code"] == "no_change"
    assert client.get(path + "/versions").json()["total"] == 1
    assert client.post(f"{BASE}/{identity}/hypotheses", json={"expected_session_revision": 1, "content": FACTUAL | {"scope": ""}}).status_code == 422


def test_http_error_documentation_matches_real_envelope(client):
    responses = client.get("/openapi.json").json()["paths"][BASE]["post"]["responses"]
    for status in ["403", "409", "422", "503"]:
        assert responses[status]["content"]["application/json"]["schema"]["$ref"].endswith("/ErrorResponse")


def test_brief_and_claim_contents_do_not_enter_request_logs(client, caplog):
    import logging
    with caplog.at_level(logging.INFO, logger="chanakya.access"):
        identity = session(client, query="PrivateSensitiveQuestion-7654321")['session_id']
        proposal(client, identity, FACTUAL | {"claim": "PrivateSensitiveClaim-1234567"})
    assert "PrivateSensitiveQuestion" not in caplog.text
    assert "PrivateSensitiveClaim" not in caplog.text
