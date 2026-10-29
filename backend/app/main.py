from contextlib import asynccontextmanager
import logging
from typing import Callable

import httpx
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse

from app.core.config import Settings
from app.core.errors import BackendError, error_body
from app.llm.ollama import OllamaProvider
from app.llm.provider import ModelProvider
from app.middleware import LocalRequestMiddleware
from app.schemas import BaselineRequest, BaselineResponse, ErrorResponse, ModelStatus
from app.services.baseline import BaselineService
from app.db.database import Database
from app.decisions.repository import DecisionRepository
from app.decisions.routes import router as decisions_router


def create_app(settings: Settings | None = None, provider_factory: Callable | None = None) -> FastAPI:
    settings = settings or Settings()

    @asynccontextmanager
    async def lifespan(app):
        logging.basicConfig(level=getattr(logging, settings.log_level), format="%(message)s")
        database = Database(settings.database_path)
        app.state.database = database
        app.state.decisions = DecisionRepository(database)
        # One shared local HTTP pool; no proxy inheritance, redirects or model download.
        async with httpx.AsyncClient(base_url=settings.ollama_base_url, trust_env=False,
                                     follow_redirects=False, limits=httpx.Limits(max_connections=4)) as client:
            provider: ModelProvider = provider_factory(client, settings) if provider_factory else OllamaProvider(client, settings)
            app.state.provider = provider
            app.state.baseline = BaselineService(provider, settings)
            try:
                yield
            finally:
                database.close()

    app = FastAPI(title="Chanakya Local Backend", version="0.2.0", lifespan=lifespan,
                  responses={status: {"model": ErrorResponse} for status in (400, 403, 404, 409, 413, 415, 422, 429, 500, 502, 503, 504)},
                  description="Increment 2: saved decision sessions and immutable, human-authored typed hypotheses. Single-agent baseline retained. No retrieval, council or probability engine yet.")
    app.include_router(decisions_router)
    app.add_middleware(CORSMiddleware, allow_origins=settings.allowed_origins,
                       allow_methods=["GET", "POST", "PATCH"], allow_headers=["Content-Type"],
                       expose_headers=["X-Request-ID"], allow_credentials=False)
    app.add_middleware(LocalRequestMiddleware, settings=settings)

    @app.exception_handler(BackendError)
    async def backend_error(request: Request, error: BackendError):
        return JSONResponse(error_body(error, request.state.request_id), status_code=error.status)

    @app.exception_handler(RequestValidationError)
    async def invalid_request(request: Request, error: RequestValidationError):
        # Pydantic's full error includes original input; do not echo sensitive text.
        details = [{"location": list(e["loc"]), "type": e["type"]} for e in error.errors()]
        return JSONResponse(error_body(BackendError("invalid_request", "Check request fields and input limits.", 422), request.state.request_id, details), status_code=422)

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, error: HTTPException):
        return JSONResponse(error_body(BackendError("http_error", "The requested operation is unavailable.", error.status_code), request.state.request_id), status_code=error.status_code)

    @app.exception_handler(Exception)
    async def unexpected_error(request: Request, error: Exception):
        logging.getLogger("chanakya.errors").error("Unexpected backend failure request_id=%s type=%s", request.state.request_id, type(error).__name__)
        return JSONResponse(error_body(BackendError("internal_error", "An unexpected backend error occurred.", 500), request.state.request_id), status_code=500,
                            headers={"X-Request-ID": request.state.request_id})

    @app.get("/api/v1/health")
    def health(request: Request):
        return {"status": "ok", "increment": 2, "model_readiness_checked": False,
                "persistence": "local_sqlite", "storage_ready": request.app.state.database.ready(),
                "research_execution": "single_agent_baseline_only"}

    @app.get("/api/v1/models/status", response_model=ModelStatus)
    async def model_status(request: Request):
        provider = request.app.state.provider
        installed = await provider.installed_model()
        loaded = await provider.loaded_model()
        details = installed.get("details") if isinstance(installed.get("details"), dict) else {}
        return ModelStatus(model=settings.model_name, installed=True, digest=installed["digest"],
                           quantization=details.get("quantization_level"), parameter_size=details.get("parameter_size"),
                           loaded=loaded, ready_to_attempt=True)

    @app.post("/api/v1/baseline", response_model=BaselineResponse)
    async def baseline(payload: BaselineRequest, request: Request):
        return await request.app.state.baseline.run(payload, request.state.request_id)

    return app


app = create_app()
