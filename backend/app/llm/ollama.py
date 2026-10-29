import json
from typing import Any

import httpx

from app.core.config import Settings
from app.core.errors import BackendError
from app.schemas import LoadedModel


def strict_json(text: str) -> Any:
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("Duplicate JSON key")
            result[key] = value
        return result
    return json.loads(text, object_pairs_hook=pairs,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError("Nonfinite JSON")))


class OllamaProvider:
    def __init__(self, client: httpx.AsyncClient, settings: Settings):
        self.client, self.settings = client, settings

    async def _request(self, method: str, path: str, payload: dict | None = None) -> dict:
        timeout = self.settings.request_timeout_seconds if payload else self.settings.status_timeout_seconds
        limit = 32768 if payload else 1024 * 1024
        try:
            async with self.client.stream(method, path, json=payload, timeout=timeout) as response:
                chunks, size = [], 0
                async for chunk in response.aiter_bytes():
                    size += len(chunk)
                    if size > limit:
                        raise BackendError("model_protocol_error", "Ollama's response exceeded the permitted size.")
                    chunks.append(chunk)
                raw = b"".join(chunks)
                if response.status_code >= 400:
                    if response.status_code == 404:
                        raise BackendError("model_not_installed", "The configured model or Ollama endpoint is unavailable.", 503)
                    # Classify known loading failures without exposing upstream text or user prompts.
                    lower = raw.lower()
                    if b"allocate" in lower or b"out of memory" in lower or b"loading model" in lower:
                        raise BackendError("model_load_failed", "Ollama could not load the model. Check available RAM/VRAM.", 503)
                    raise BackendError("model_service_error", "Ollama rejected the operation.", 503)
                if response.status_code != 200:
                    raise BackendError("model_protocol_error", "Unexpected Ollama status; redirects are not followed.")
                try:
                    data = strict_json(raw.decode("utf-8"))
                except (ValueError, UnicodeDecodeError) as error:
                    raise BackendError("model_protocol_error", "Ollama returned an invalid JSON envelope.") from error
                if not isinstance(data, dict) or data.get("error"):
                    raise BackendError("model_protocol_error", "Ollama returned an invalid response envelope.")
                return data
        except httpx.TimeoutException as error:
            raise BackendError("model_timeout", "The local model exceeded its request timeout.", 504, True) from error
        except httpx.RequestError as error:
            raise BackendError("model_unavailable", "Cannot reach local Ollama. Open the Ollama application and retry.", 503, True) from error

    async def installed_model(self) -> dict:
        data = await self._request("GET", "/api/tags")
        models = data.get("models")
        if not isinstance(models, list) or any(not isinstance(m, dict) for m in models):
            raise BackendError("model_protocol_error", "Ollama returned an invalid model registry.")
        match = next((m for m in models if m.get("name") == self.settings.model_name or m.get("model") == self.settings.model_name), None)
        if match is None:
            raise BackendError("model_not_installed", "Install the configured local model explicitly; the backend never downloads models.", 503)
        if match.get("remote_host") or match.get("remote_model"):
            raise BackendError("remote_model_blocked", "This backend permits local model weights only.", 503)
        digest = match.get("digest")
        if not isinstance(digest, str) or not digest:
            raise BackendError("model_protocol_error", "The installed model has no reported digest.")
        if self.settings.expected_model_digest and digest != self.settings.expected_model_digest:
            raise BackendError("model_digest_mismatch", "The installed model differs from the configured experiment digest.", 503)
        return match

    async def loaded_model(self) -> LoadedModel:
        data = await self._request("GET", "/api/ps")
        models = data.get("models")
        if not isinstance(models, list) or any(not isinstance(m, dict) for m in models):
            raise BackendError("model_protocol_error", "Ollama returned invalid loaded-model metadata.")
        match = next((m for m in models if m.get("name") == self.settings.model_name or m.get("model") == self.settings.model_name), None)
        if match is None:
            return LoadedModel()
        def integer(key):
            value = match.get(key)
            return value if type(value) is int and value >= 0 else None
        return LoadedModel(loaded=True, reported_size_bytes=integer("size"), reported_vram_bytes=integer("size_vram"), context_tokens=integer("context_length"))

    async def generate(self, messages: list[dict], schema: dict) -> dict:
        data = await self._request("POST", "/api/chat", {
            "model": self.settings.model_name, "stream": False, "keep_alive": "5m",
            "format": schema, "messages": messages,
            "options": {"temperature": 0, "num_ctx": self.settings.context_tokens, "num_predict": self.settings.output_tokens},
        })
        if (data.get("done") is not True or data.get("model") != self.settings.model_name
                or not isinstance(data.get("message"), dict)
                or not isinstance(data["message"].get("content"), str)):
            raise BackendError("model_protocol_error", "Ollama returned an incomplete or mismatched model response.")
        if data.get("done_reason") == "length":
            raise BackendError("model_output_truncated", "The model exhausted its output budget. No partial answer was accepted.")
        return data
