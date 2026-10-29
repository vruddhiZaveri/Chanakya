# Chanakya backend — Increment 1

This increment provides a real local model boundary: FastAPI, Ollama, Pydantic validation and bounded failure handling. It does **not** implement the full research framework yet. The approved React frontend is unchanged and not connected to these endpoints in this increment.

## What runs

| Endpoint | Behavior |
|---|---|
| `GET /api/v1/health` | API liveness, explicitly not model readiness |
| `GET /api/v1/models/status` | Check installed model/digest and reported loaded-memory metadata; never load/download a model |
| `POST /api/v1/baseline` | One real single-agent assessment, with at most one invalid-output repair |

`direct` mode is an unsourced baseline. `source_grounded` mode accepts up to three short **user-supplied** excerpts. There is no retrieval or document ingestion yet. Valid citation IDs mean only that the returned IDs belong to the supplied excerpts. Semantic entailment and source authenticity are not automatically verified.

## Local prerequisites and choices

- Use your existing **Python 3.12** (`py -3.12`). The default `python` on your laptop is 3.13; create this environment explicitly with 3.12.
- Keep your existing **Ollama** and **qwen2.5:3b Q4_K_M**. This model was already shown working with GPU offload on your laptop. The backend does not download or update model weights or drivers.
- Your RTX 2050 has **4 GB dedicated VRAM**, not 8 GB. Start with context 4096 and output budget 384. One model request runs at a time; a simultaneous request gets 429 rather than queuing multiple model loads.
- There is no paid API key, Docker service, Chroma, LangGraph or database prerequisite for this increment. Those belong to later approved phases.

## Windows 11 / VS Code setup

Open a PowerShell terminal in your repository, then:

```powershell
cd "C:\1_PLACEMENT\FINAL PROJECTS\chanakya\backend"
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Run `Copy-Item` only on first setup; preserve your existing `.env` on later updates. There is no need to activate the environment or change PowerShell execution policy. Always call its Python explicitly as shown. `requirements.in` lists direct dependency constraints; `requirements.txt` contains the tested resolution plus the Windows-specific colorama dependency. Linux install/test results do not constitute a native Windows compatibility test.

Open Ollama from the Windows Start menu. Confirm its local model is present:

```powershell
ollama list
```

Start the API in the same terminal:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000 --no-access-log
```

Open `http://127.0.0.1:8000/docs` or `http://127.0.0.1:8000/openapi.json`. Swagger UI's default assets are CDN-hosted and may require internet; the raw OpenAPI schema and all model calls are local. Core inference does not need internet once dependencies and model weights are installed.

Use one worker only. Development reload interrupts in-flight requests; this increment has no durable job recovery or persistence. Press Ctrl+C to stop. To run without the reload watcher, omit `--reload`.

## Verify the actual local connection

In a **second** PowerShell terminal:

```powershell
cd "C:\1_PLACEMENT\FINAL PROJECTS\chanakya\backend"
Invoke-RestMethod http://127.0.0.1:8000/api/v1/health
Invoke-RestMethod http://127.0.0.1:8000/api/v1/models/status | ConvertTo-Json -Depth 8
```

Then run a real model request, independent of test mocks:

```powershell
$body = @{
    mode = "source_grounded"
    question = "Is full deployment approved?"
    sources = @(@{
        id = "S1"
        title = "Synthetic test policy"
        excerpt = "Only a library pilot is approved. Full deployment is not approved."
    })
} | ConvertTo-Json -Depth 10

$result = Invoke-RestMethod `
    -Uri "http://127.0.0.1:8000/api/v1/baseline" `
    -Method Post -ContentType "application/json" -Body $body -TimeoutSec 150
$result | ConvertTo-Json -Depth 12
```

Inspect that the answer says full deployment is **not** approved, cites S1 and shows the actual model digest/timing. The API does not return a predetermined answer. A convenient equivalent diagnostic is `./scripts/smoke.ps1` if your local script policy allows it; otherwise use the inline commands without changing policy.

## Tests: mock boundaries versus live inference

```powershell
# Fast isolated tests; no model download or live inference.
.\.venv\Scripts\python.exe -m pytest -q -m "not live"

# Explicitly opt into an actual local-model integration test.
$env:CHANAKYA_RUN_LIVE_TESTS = "1"
.\.venv\Scripts\python.exe -m pytest -q -m live -s
Remove-Item Env:CHANAKYA_RUN_LIVE_TESTS
```

The live test fails if Ollama/model execution fails; it is not replaced by a mocked success. Its transport/schema/reference checks do not automatically establish factual correctness; inspect the printed answer. The implementation environment has no access to your laptop's Ollama, so a passing live-model backend integration test is **not claimed** here. Your earlier direct Ollama test proved only the model API, not this new backend end to end.

## Runtime behavior and contract

Requests accept only `mode`, `question` and `sources`; users cannot override the model, endpoint or budgets per request. Inputs are stripped and bounded; duplicate source IDs and unknown fields are rejected. The complete prompt, schema and output reserve must fit a conservative UTF-8 byte-based ceiling; oversized input is rejected rather than truncated. This is not a universal exact tokenizer implementation. Changing model family requires reviewing the budget assumption.

The provider calls only local `/api/tags`, `/api/ps`, `/api/chat`. It disables inherited HTTP proxies and redirects, validates the configured loopback endpoint and rejects cloud-tagged/remote metadata. It does not expose arbitrary tool execution, URL retrieval or provider selection to prompts. The whole baseline operation has a deadline; load failures/timeouts do not trigger repeated retries. Invalid structured assessments have one bounded repair, counted in usage where metadata is available. Prompt/answer bodies are not logged.

The result contains assessment, validation distinctions, configuration, attempt count, actual available token/duration metadata, request ID and model digest. Unknown telemetry is null. Digest lookup is explicitly identified as installed-registry metadata obtained before the call, not cryptographic attestation that the weight file could not change mid-call. Optionally pin a full digest in `.env` for experiments. GPU identity is not inferred from model metadata.

Grounded answers must cite supplied source IDs or mark insufficient evidence. The model can still produce an unsupported statement with a valid ID; no semantic-verification claim is made. Decisions remain advisory. There are no numerical confidence values, probabilistic inference updates, sessions or Human reviewed flags in this baseline response.

## Settings

Copy `.env.example` to `.env` inside backend. All settings start `CHANAKYA_`. Current keys: MODEL_NAME, OLLAMA_BASE_URL, EXPECTED_MODEL_DIGEST (optional), CONTEXT_TOKENS, OUTPUT_TOKENS, REQUEST_TIMEOUT_SECONDS, STATUS_TIMEOUT_SECONDS, MAX_MODEL_ATTEMPTS, MAX_REQUEST_BYTES, ALLOWED_ORIGINS and LOG_LEVEL. The app locates backend/.env regardless of working directory. Restart after configuration changes.

The API is a local single-user development service, **not authenticated multi-user hosting**. Bind it to 127.0.0.1 as shown. Exact loopback Host and configured browser Origin checks limit browser misuse; no blanket CORS wildcard. If Vite starts on 5174, change ALLOWED_ORIGINS explicitly to that actual local origin. The existing hosted Site cannot automatically call the backend on your laptop. No public tunnel is configured.

## Troubleshooting

| Error | Action |
|---|---|
| `model_unavailable` / 503 | Open local Ollama; verify `ollama list`; check 11434 is available |
| `model_not_installed` / 503 | Set the exact already installed local tag; no automatic download occurs |
| `model_load_failed` / 503 | Free RAM/VRAM, close unused apps and retry manually; do not assume a corrupt model |
| `model_timeout` / 504 | Inspect model speed/resources; no partial answer is returned |
| `model_busy` / 429 | Wait for the one active request; do not start multiple workers |
| `invalid_model_output` / 502 | Structured response/reference checks failed after bounded attempts; inspect behavior with synthetic fixtures |
| `model_output_truncated` / 502 | Output budget was exhausted; no truncated result is accepted |
| `prompt_budget_exceeded` / 422 | Shorten supplied excerpts/question; do not blindly increase context on a 4 GB GPU |
| `origin_not_allowed` / 403 | Use your configured local Vite origin; do not disable browser protections |
| `invalid_request` / 422 | Check mode, source IDs and documented field lengths; unknown fields are rejected |
| `model_digest_mismatch` / 503 | Reconcile the intentional model version change before updating an experiment pin |

## Source layout and next phase

`app/main.py` creates the API and shared lifespan resources. `core/config.py` validates local configuration. `schemas.py` owns input/output schemas. `llm/ollama.py` is the actual provider, behind `llm/provider.py`'s protocol. `services/baseline.py` controls budgets, one active call and response validation. `middleware.py` bounds bodies and adds local-request checks/request IDs. `tests/` distinguishes fake-transport tests and the opt-in live test.

Later phases add typed hypotheses/persistence, document retrieval, dynamic LangGraph orchestration, mathematical inference, SSE and the approved frontend integration. None is represented as implemented by this increment. Stop after validating this increment and review before proceeding.
