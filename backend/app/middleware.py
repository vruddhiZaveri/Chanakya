import json
import logging
import time
from urllib.parse import urlsplit
from uuid import uuid4

from starlette.responses import JSONResponse

from app.core.errors import BackendError, error_body

logger = logging.getLogger("chanakya.access")


class LocalRequestMiddleware:
    """Bound bodies before JSON parsing and keep the single-user API loopback-only."""

    def __init__(self, app, settings):
        self.app, self.settings = app, settings

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        request_id, start = str(uuid4()), time.perf_counter()
        scope.setdefault("state", {})["request_id"] = request_id
        headers = {k.lower(): v for k, v in scope["headers"]}
        status = 500

        async def tagged_send(message):
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
                message["headers"] = list(message.get("headers", [])) + [(b"x-request-id", request_id.encode())]
            await send(message)

        async def fail(code, message, http_status):
            await JSONResponse(error_body(BackendError(code, message, http_status), request_id), status_code=http_status)(scope, receive, tagged_send)

        try:
            try:
                host = urlsplit("http://" + headers.get(b"host", b"").decode("latin-1")).hostname
            except ValueError:
                await fail("invalid_host", "Use a valid local loopback API host.", 400)
                return
            if host not in {"localhost", "127.0.0.1", "::1"}:
                await fail("invalid_host", "Use the local loopback API host.", 400)
                return
            origin = headers.get(b"origin", b"").decode("latin-1")
            if origin and origin not in self.settings.allowed_origins:
                await fail("origin_not_allowed", "This browser origin is not allowed.", 403)
                return
            if scope["method"] in {"POST", "PUT", "PATCH"}:
                if headers.get(b"content-type", b"").split(b";", 1)[0].strip().lower() != b"application/json":
                    await fail("unsupported_media_type", "Send an application/json body.", 415)
                    return
                try:
                    length = int(headers.get(b"content-length", b"0"))
                except ValueError:
                    await fail("invalid_content_length", "Invalid request length.", 400)
                    return
                if length < 0:
                    await fail("invalid_content_length", "Invalid request length.", 400)
                    return
                if length > self.settings.max_request_bytes:
                    await fail("request_too_large", "Request exceeds the permitted byte limit.", 413)
                    return
                chunks, size = [], 0
                while True:
                    message = await receive()
                    if message["type"] == "http.disconnect":
                        return
                    chunk = message.get("body", b"")
                    size += len(chunk)
                    if size > self.settings.max_request_bytes:
                        await fail("request_too_large", "Request exceeds the permitted byte limit.", 413)
                        return
                    chunks.append(chunk)
                    if not message.get("more_body", False):
                        break
                body = b"".join(chunks)
                delivered = False

                async def replay():
                    nonlocal delivered
                    if not delivered:
                        delivered = True
                        return {"type": "http.request", "body": body, "more_body": False}
                    return await receive()

                await self.app(scope, replay, tagged_send)
            else:
                await self.app(scope, receive, tagged_send)
        finally:
            # No request/response bodies, question text, filenames or upstream errors.
            logger.info(json.dumps({"event": "http_request", "request_id": request_id,
                                    "method": scope["method"], "status": status,
                                    "elapsed_seconds": round(time.perf_counter() - start, 4)}))
