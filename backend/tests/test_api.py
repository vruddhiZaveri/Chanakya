import json

import httpx
import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from conftest import DIGEST, envelope


def test_health_is_not_an_inference_claim(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["model_readiness_checked"] is False
    assert response.json()["persistence"] == "local_sqlite"
    assert response.json()["storage_ready"] is True
    assert response.headers["x-request-id"]


def test_model_status_does_not_load_a_model(client):
    data = client.get("/api/v1/models/status").json()
    assert data["installed"] is True and data["digest"] == DIGEST
    assert data["quantization"] == "Q4_K_M"
    assert data["loaded"]["loaded"] is False
    assert data["ready_to_attempt"] is True


def test_real_adapter_contract_and_validated_response(api_factory, payload):
    app, calls = api_factory()
    with TestClient(app, base_url="http://localhost") as client:
        response = client.post("/api/v1/baseline", json=payload)
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["assessment"]["source_ids"] == ["S1"]
    assert result["validation"]["semantic_support_verified"] is False
    assert result["validation"]["source_authenticity_verified"] is False
    assert result["model_attempts"] == 1 and result["usage"]["output_tokens"] == 50
    assert result["request_id"] == response.headers["x-request-id"]
    sent = json.loads(next(r for r in calls if r.url.path == "/api/chat").content)
    assert sent["model"] == "qwen2.5:3b" and sent["stream"] is False
    assert sent["options"] == {"temperature": 0, "num_ctx": 4096, "num_predict": 384}
    assert sent["format"]["additionalProperties"] is False
    assert all(r.url.host == "127.0.0.1" for r in calls)
    assert not any("pull" in r.url.path for r in calls)


@pytest.mark.parametrize("patch", [
    {"question": "short"}, {"question": " " * 20}, {"model": "another-model"},
    {"sources": []}, {"sources": [{"id": "../bad", "title": "t", "excerpt": "x"}]},
    {"mode": "direct"}, {"sources": [{"id": "S1", "title": "x", "excerpt": "x"}] * 2},
])
def test_bad_input_never_calls_model(api_factory, payload, patch):
    app, calls = api_factory()
    with TestClient(app, base_url="http://localhost") as client:
        response = client.post("/api/v1/baseline", json=payload | patch)
    assert response.status_code == 422
    assert not calls
    assert "input" not in response.json()["error"].get("details", [{}])[0]


def test_request_and_origin_limits(client):
    assert client.post("/api/v1/baseline", content="x" * 17000, headers={"content-type": "application/json"}).status_code == 413
    assert client.post("/api/v1/baseline", content="x", headers={"content-type": "text/plain"}).status_code == 415
    assert client.get("/api/v1/health", headers={"origin": "https://untrusted.example"}).status_code == 403
    assert client.get("/api/v1/health", headers={"host": "untrusted.example"}).status_code == 400
    response = client.options("/api/v1/baseline", headers={"origin": "http://localhost:5173", "access-control-request-method": "POST", "access-control-request-headers": "content-type"})
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_invalid_json_is_sanitized(client):
    response = client.post("/api/v1/baseline", content='{"question":"PRIVATE secret', headers={"content-type": "application/json"})
    assert response.status_code == 422
    assert "PRIVATE" not in response.text


@pytest.mark.parametrize("failure,status,code", [
    ("timeout", 504, "model_timeout"), ("connection", 503, "model_unavailable"),
    ("oom", 503, "model_load_failed"), ("missing", 503, "model_not_installed"),
    ("redirect", 502, "model_protocol_error"), ("oversized", 502, "model_protocol_error"),
])
def test_model_failures_are_honest_and_not_retried(api_factory, payload, failure, status, code):
    def chat(request):
        if failure == "timeout":
            raise httpx.ReadTimeout("PRIVATE prompt upstream", request=request)
        if failure == "connection":
            raise httpx.ConnectError("PRIVATE host details", request=request)
        if failure == "oom":
            return httpx.Response(500, json={"error": "PRIVATE failed to allocate CUDA_Host"})
        if failure == "missing":
            return httpx.Response(404, json={"error": "PRIVATE missing"})
        if failure == "redirect":
            return httpx.Response(302, headers={"location": "https://remote.example"})
        return httpx.Response(200, content=b"x" * 40000)
    app, calls = api_factory(chat=chat)
    with TestClient(app, base_url="http://localhost") as client:
        response = client.post("/api/v1/baseline", json=payload)
    assert response.status_code == status
    assert response.json()["error"]["code"] == code
    assert "PRIVATE" not in response.text
    assert len([r for r in calls if r.url.path == "/api/chat"]) == 1


def test_missing_model_never_generates_or_downloads(api_factory, payload):
    app, calls = api_factory(tags={"models": []})
    with TestClient(app, base_url="http://localhost") as client:
        response = client.post("/api/v1/baseline", json=payload)
    assert response.status_code == 503
    assert [r.url.path for r in calls] == ["/api/tags"]


@pytest.mark.parametrize("bad_content", [
    "not JSON", '{"answer":"a","answer":"b"}',
    json.dumps({"answer": "Fabricated reference.", "source_ids": ["UNKNOWN"], "limitations": ["test"], "insufficient_evidence": False}),
    json.dumps({"answer": "No references.", "source_ids": [], "limitations": ["test"], "insufficient_evidence": False}),
    json.dumps({"answer": "Wrong type.", "source_ids": ["S1"], "limitations": ["test"], "insufficient_evidence": "false"}),
])
def test_invalid_outputs_have_a_bounded_repair_then_fail(api_factory, payload, bad_content):
    app, calls = api_factory(chat=envelope(content=bad_content))
    with TestClient(app, base_url="http://localhost") as client:
        response = client.post("/api/v1/baseline", json=payload)
    assert response.status_code == 502
    assert response.json()["error"]["code"] == "invalid_model_output"
    assert len([r for r in calls if r.url.path == "/api/chat"]) == 2


def test_repair_can_succeed_without_inventing_a_result(api_factory, payload):
    count = 0
    def chat(request):
        nonlocal count
        count += 1
        return httpx.Response(200, json=envelope(content="not JSON") if count == 1 else envelope())
    app, _ = api_factory(chat=chat)
    with TestClient(app, base_url="http://localhost") as client:
        result = client.post("/api/v1/baseline", json=payload).json()
    assert result["model_attempts"] == 2
    assert result["usage"]["input_tokens"] == 200


@pytest.mark.parametrize("change", [{"done": False}, {"model": "different-model"}, {"message": {}}, {"done_reason": "length"}])
def test_incomplete_wrong_or_truncated_envelopes_fail(api_factory, payload, change):
    app, _ = api_factory(chat=envelope(**change))
    with TestClient(app, base_url="http://localhost") as client:
        response = client.post("/api/v1/baseline", json=payload)
    assert response.status_code == 502


def test_missing_usage_is_not_fabricated(api_factory, payload):
    data = envelope()
    for key in ["prompt_eval_count", "eval_count", "total_duration"]:
        del data[key]
    app, _ = api_factory(chat=data)
    with TestClient(app, base_url="http://localhost") as client:
        result = client.post("/api/v1/baseline", json=payload).json()
    assert result["usage"] == {"input_tokens": None, "output_tokens": None, "total_model_seconds": None}


def test_prompt_budget_rejects_without_truncating(api_factory, payload):
    payload["question"] = "Detailed question " * 100
    payload["sources"][0]["excerpt"] = "evidence " * 120
    app, calls = api_factory()
    with TestClient(app, base_url="http://localhost") as client:
        response = client.post("/api/v1/baseline", json=payload)
    assert response.status_code == 422 and response.json()["error"]["code"] == "prompt_budget_exceeded"
    assert calls == []


def test_direct_mode_cannot_fabricate_citations(api_factory):
    app, _ = api_factory()
    with TestClient(app, base_url="http://localhost") as client:
        response = client.post("/api/v1/baseline", json={"question": "What is evidence based decision making?"})
    assert response.status_code == 502


def test_openapi_documents_actual_endpoints(client):
    paths = client.get("/openapi.json").json()["paths"]
    assert {"/api/v1/health", "/api/v1/models/status", "/api/v1/baseline", "/api/v1/sessions"} <= set(paths)


def test_digest_pin_detects_changed_model(api_factory, payload):
    app, calls = api_factory(settings=Settings(_env_file=None, expected_model_digest="b" * 64))
    with TestClient(app, base_url="http://localhost") as client:
        response = client.post("/api/v1/baseline", json=payload)
    assert response.status_code == 503 and response.json()["error"]["code"] == "model_digest_mismatch"
    assert len(calls) == 1


def test_no_prompt_or_answer_in_access_log(client, payload, caplog):
    import logging
    with caplog.at_level(logging.INFO, logger="chanakya.access"):
        client.post("/api/v1/baseline", json=payload)
    assert "http_request" in caplog.text
    assert payload["question"] not in caplog.text and payload["sources"][0]["excerpt"] not in caplog.text


def test_source_grounded_abstention_is_a_valid_answer(api_factory, payload):
    content = json.dumps({"answer": "The supplied source does not establish the budget.", "source_ids": [],
                          "limitations": ["A budget source is missing."], "insufficient_evidence": True})
    app, _ = api_factory(chat=envelope(content=content))
    with TestClient(app, base_url="http://localhost") as client:
        response = client.post("/api/v1/baseline", json=payload)
    assert response.status_code == 200 and response.json()["assessment"]["insufficient_evidence"] is True


def test_direct_baseline_has_no_source_verification_claim(api_factory):
    content = json.dumps({"answer": "Use evidence and inspect limitations.", "source_ids": [],
                          "limitations": ["Not checked against sources."], "insufficient_evidence": False})
    app, _ = api_factory(chat=envelope(content=content))
    with TestClient(app, base_url="http://localhost") as client:
        response = client.post("/api/v1/baseline", json={"question": "Explain evidence based decision making."})
    assert response.status_code == 200 and response.json()["mode"] == "direct"


def test_loaded_model_metadata_is_reported_without_guessing_hardware(api_factory):
    app, _ = api_factory(ps={"models": [{"name": "qwen2.5:3b", "size": 2200000000,
                                         "size_vram": 2200000000, "context_length": 4096}]})
    with TestClient(app, base_url="http://localhost") as client:
        data = client.get("/api/v1/models/status").json()
    assert data["loaded"]["reported_vram_bytes"] == 2200000000
    assert "gpu_name" not in data["loaded"]


def test_unexpected_failure_has_sanitized_error(api_factory, payload):
    def chat(request):
        raise ValueError("PRIVATE details should never be returned")
    app, _ = api_factory(chat=chat)
    with TestClient(app, base_url="http://localhost", raise_server_exceptions=False) as client:
        response = client.post("/api/v1/baseline", json=payload)
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "internal_error"
    assert "PRIVATE" not in response.text
    assert response.headers["x-request-id"] == response.json()["request_id"]


def test_chunked_oversized_body_is_bounded(client):
    response = client.post("/api/v1/baseline", content=(b"x" * 9000 for _ in range(2)), headers={"content-type": "application/json"})
    assert response.status_code == 413
