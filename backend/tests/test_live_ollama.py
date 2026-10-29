"""Real inference test. Never replaced by a mocked passing test in CI."""
import os

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


@pytest.mark.live
@pytest.mark.skipif(os.getenv("CHANAKYA_RUN_LIVE_TESTS") != "1", reason="Opt in on the machine running real local Ollama")
def test_real_local_model_with_supplied_synthetic_source():
    with TestClient(create_app(Settings()), base_url="http://localhost") as client:
        status = client.get("/api/v1/models/status")
        assert status.status_code == 200, status.text
        response = client.post("/api/v1/baseline", json={
            "mode": "source_grounded", "question": "Is full deployment approved?",
            "sources": [{"id": "S1", "title": "Synthetic test policy", "excerpt": "Only a library pilot is approved. Full deployment is not approved."}],
        })
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["assessment"]["source_ids"] == ["S1"]
        assert data["assessment"]["insufficient_evidence"] is False
        assert data["model_digest"] == status.json()["digest"]
        print("\nLIVE MODEL ANSWER (inspect grounding manually):", data["assessment"]["answer"])
        print("LIVE TIMING/USAGE:", data["elapsed_seconds"], data["usage"])
        # Structure/reference tests are not a claim of semantic factual correctness.
