# Backend increment 1 — local model foundation

This increment adds a runnable FastAPI service beside the approved frontend. It establishes a real single-agent baseline before retrieval, structured arguments, council deliberation, or decision scoring are implemented. The frontend is unchanged and is not connected to this API yet.

## Runtime choice

Use the existing local `qwen2.5:3b` installation through Ollama, with temperature 0, a 4,096-token context and a 384-token output limit. The user's Windows machine has 16 GB system RAM and an RTX 2050 with 4 GB VRAM; Qwen previously ran successfully with 100% GPU offload. This is evidence for starting with that model, not a guarantee every workload fits. Do not load multiple models or start multiple backend workers.

Use the already installed Python 3.12 for a separate virtual environment. No hosted model, model download, database server or agent framework is required for this increment.

## API contract

| Endpoint | Purpose |
| --- | --- |
| `GET /api/v1/health` | Reports API availability without claiming model readiness. |
| `GET /api/v1/models/status` | Reads the local installed-model registry and loaded-model metadata. Readiness to attempt inference is not a successful inference test. |
| `POST /api/v1/baseline` | Runs one real local model with validated direct or supplied-source output. |

The generated contract is in `backend/docs/openapi.json`. See `backend/README.md` for Windows setup, request examples, configuration, error codes and live checks.

Source-grounded mode uses excerpts supplied in the request. It does not search the web or verify source authenticity. Schema validation and allowed source-ID checks do not prove that an answer is semantically supported. The response explicitly records those verification limits. No probabilities, confidence scores, agent conversations or evidence are fabricated.

## Implemented safeguards

- Loopback-only Ollama connection, no inherited HTTP proxies or redirects, and no automatic model pulls.
- Exact local frontend origins, request-size limits and input validation.
- One active inference operation per process, a total deadline and bounded output validation attempts.
- Explicit missing-model, connection, timeout, memory-loading, malformed-output and busy errors.
- No silent prompt truncation and no partial model answer accepted after output exhaustion.
- Request IDs and timing logs without question, source or generated-answer contents.
- Model registry digest, actual available usage telemetry and explicit unknown values where telemetry is absent.

The service is a single-user local development foundation, not an authenticated public API. Decisions, source excerpts and answers are not persisted yet. Model context budgeting is conservative rather than an exact tokenizer implementation.

## Validation performed

- Python 3.12 environment: **49 automated tests passed; 1 live-model test skipped**.
- Tests exercise the real Ollama HTTP adapter with controlled transport responses. They cover request/response contracts, validation retries, citation membership, privacy, concurrent requests, cancellation, deadline expiry and failure handling.
- A real Uvicorn process was checked over HTTP: health returned 200; an unavailable local Ollama endpoint returned 503; an invalid baseline request returned 422.
- Dependency installation and `pip check` passed on the execution host. Binary wheels for the pinned dependencies were checked for Windows x64 / Python 3.12. This is not a native Windows execution test.
- The installed Starlette test client emits a deprecation warning about its HTTPX integration; the checks pass. This warning does not establish a production failure.
- Live inference has **not** been run from this execution host because it cannot access the user's laptop Ollama service. Run the supplied smoke script and opt-in live test there before calling the local integration validated.

The approved frontend source, assets, routes, dependencies and design are preserved.

## Next increment, after reviewing the local result

Review the returned answer, source IDs, timing and hardware usage on the laptop. Then agree the next increment: persistent decisions and API integration, followed by retrieval and typed evidence/argument structures. Multi-agent deliberation and evaluation should build on those verified structures rather than simulated UI messages.
