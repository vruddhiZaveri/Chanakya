import json
import sys
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import Settings
from app.llm.ollama import OllamaProvider
from app.main import create_app

DIGEST = "a" * 64


def envelope(content=None, **changes):
    result = {"model": "qwen2.5:3b", "done": True, "done_reason": "stop",
              "message": {"content": content or json.dumps({"answer": "Only a pilot is approved.", "source_ids": ["S1"], "limitations": ["Only the supplied excerpt was assessed."], "insufficient_evidence": False})},
              "prompt_eval_count": 100, "eval_count": 50, "total_duration": 1000000000}
    return result | changes


def registry():
    return {"models": [{"name": "qwen2.5:3b", "digest": DIGEST, "size": 1900000000,
                        "details": {"quantization_level": "Q4_K_M", "parameter_size": "3.1B"}}]}


@pytest.fixture
def payload():
    return {"mode": "source_grounded", "question": "Is full deployment approved?",
            "sources": [{"id": "S1", "title": "Synthetic policy fixture", "excerpt": "Only a pilot is approved. Full deployment is not approved."}]}


@pytest.fixture
def api_factory():
    clients = []
    def build(chat=None, tags=None, ps=None, settings=None):
        calls = []
        def handler(request):
            calls.append(request)
            if request.url.path == "/api/tags":
                return tags(request) if callable(tags) else httpx.Response(200, json=tags if tags is not None else registry())
            if request.url.path == "/api/ps":
                return ps(request) if callable(ps) else httpx.Response(200, json=ps if ps is not None else {"models": []})
            if request.url.path == "/api/chat":
                return chat(request) if callable(chat) else httpx.Response(200, json=chat if chat is not None else envelope())
            raise AssertionError("Unexpected external path: " + request.url.path)

        transport = httpx.MockTransport(handler)
        def provider_factory(client, config):
            # Separate explicit mock transport; production uses the real local pool.
            provider = OllamaProvider(httpx.AsyncClient(base_url="http://127.0.0.1:11434", transport=transport), config)
            clients.append(provider.client)
            return provider
        app = create_app(settings or Settings(_env_file=None), provider_factory)
        return app, calls
    yield build
    # Mock transports have no live sockets or background server.
    import asyncio
    for client in clients:
        asyncio.run(client.aclose())


@pytest.fixture
def client(api_factory):
    app, _ = api_factory()
    with TestClient(app, base_url="http://localhost") as client:
        yield client
