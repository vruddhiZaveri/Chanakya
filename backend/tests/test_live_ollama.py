"""Real inference test. Never replaced by a mocked passing test in CI."""

import os

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


@pytest.mark.live
@pytest.mark.skipif(
    os.getenv("CHANAKYA_RUN_LIVE_TESTS") != "1",
    reason="Opt in on the machine running real local Ollama",
)
def test_real_local_model_with_supplied_synthetic_source():
    with TestClient(create_app(Settings()), base_url="http://localhost") as client:
        status = client.get("/api/v1/models/status")
        assert status.status_code == 200, status.text
        response = client.post(
            "/api/v1/baseline",
            json={
                "mode": "source_grounded",
                "question": "Is full deployment approved?",
                "sources": [
                    {
                        "id": "S1",
                        "title": "Synthetic test policy",
                        "excerpt": "Only a library pilot is approved. Full deployment is not approved.",
                    }
                ],
            },
        )
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["assessment"]["source_ids"] == ["S1"]
        assert data["assessment"]["insufficient_evidence"] is False
        assert data["model_digest"] == status.json()["digest"]
        print(
            "\nLIVE MODEL ANSWER (inspect grounding manually):",
            data["assessment"]["answer"],
        )
        print("LIVE TIMING/USAGE:", data["elapsed_seconds"], data["usage"])
        # Structure/reference tests are not a claim of semantic factual correctness.


@pytest.mark.live
@pytest.mark.skipif(
    os.getenv("CHANAKYA_RUN_LIVE_TESTS") != "1",
    reason="Opt in on the machine running real local Ollama",
)
def test_real_document_retrieval_to_saved_local_model_answer():
    from uuid import uuid4

    with TestClient(create_app(Settings()), base_url="http://localhost") as client:
        created = client.post(
            "/api/v1/sessions", json={"query": "Is full deployment approved?"}
        )
        assert created.status_code == 201, created.text
        path = "/api/v1/sessions/" + created.json()["session_id"]
        uploaded = client.post(
            path + "/documents?filename=policy.txt&expected_session_revision=1",
            content=b"Only a library pilot is approved. Full deployment is not approved.",
            headers={"Content-Type": "text/plain"},
        )
        assert uploaded.status_code == 201, uploaded.text
        found = client.post(
            path + "/evidence/search",
            json={
                "query": "deployment approved",
                "expected_session_revision": 1,
                "limit": 1,
            },
        )
        assert found.status_code == 201, found.text
        snapshot = found.json()
        req = {
            "snapshot_id": snapshot["snapshot_id"],
            "expected_session_revision": 1,
            "idempotency_key": str(uuid4()),
        }
        response = client.post(path + "/answers", json=req)
        assert response.status_code == 200, response.text
        saved = response.json()
        assessment = saved["response"]["assessment"]
        assert assessment["source_ids"] == [snapshot["passages"][0]["source_id"]]
        assert assessment["insufficient_evidence"] is False
        assert client.get(path + "/answers/" + saved["answer_id"]).json() == saved
        assert client.post(path + "/answers", json=req).json() == saved
        print(
            "\nLIVE SAVED DOCUMENT ANSWER (inspect grounding manually):",
            assessment["answer"],
        )
        print("LIVE SAVED ANSWER ID:", saved["answer_id"])
