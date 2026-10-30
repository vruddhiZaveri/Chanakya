# Chanakya local backend — Increment 3

The current installation, upload contract, limits, evidence APIs and inline Windows smoke test are in [docs/INCREMENT_3.md](docs/INCREMENT_3.md). This adds local document extraction and reproducible lexical retrieval while preserving the existing baseline and saved typed state. The frontend is unchanged.

The Increment 2 guide below is retained as reference for the existing session/hypothesis and baseline APIs. Its earlier test counts and scope descriptions are historical; use the Increment 3 guide for the current update.

# Chanakya local backend — Increment 2

FastAPI + local Ollama + SQLite, with SQLAlchemy 2.x and Alembic migrations. The approved frontend is unchanged and is not connected to this API yet.

Increment 1's real single-agent baseline is preserved. Increment 2 adds saved decision sessions, immutable brief histories and six types of manually authored hypotheses. It does not implement retrieval, an AI council, probabilistic inference or final decision generation.

## Update an existing Increment 1 installation

Apply the supplied incremental patch from the repository root as described in the package's START_HERE.md. Do not reapply Increment 1 or overwrite your existing .env. Then, in PowerShell:

```powershell
cd "C:\1_PLACEMENT\FINAL PROJECTS\chanakya\backend"
$ErrorActionPreference = "Stop"
$PSNativeCommandUseErrorActionPreference = $true
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m app.db.migrate
.\.venv\Scripts\python.exe -m pytest -q -m "not live"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000 --no-access-log
```

Keep Ollama open when testing the baseline. Storage endpoints do not call Ollama. Run one API worker only. Press Ctrl+C to stop the API before updating or taking a database backup. Restarting the API does not remove saved sessions.

For a fresh installation, first run `py -3.12 -m venv .venv`, then install requirements and copy `.env.example` to `.env`. Use your installed Python 3.12 explicitly; Python 3.13 is the laptop's default. No activation, execution-policy change, new model download, Docker or paid API key is needed.

## Configuration and database migration

`backend/.env` is loaded regardless of terminal location. Defaults remain `qwen2.5:3b`, temperature 0, context 4096, output limit 384, at most two bounded output-validation attempts and one active model request per process. The earlier laptop run reported 100% GPU offload for Qwen on the RTX 2050 with 4 GB VRAM; this does not guarantee every workload fits.

`CHANAKYA_DATABASE_PATH` defaults to `backend/data/chanakya.sqlite3`. A relative value such as `data/chanakya.sqlite3` resolves inside backend, not against the terminal's working directory. Use a local disk, not a network share. Database paths are configuration only, never accepted from API requests.

Migration is explicit: `python -m app.db.migrate` using the virtual environment Python. It upgrades to the latest bundled Alembic revision and is safe to rerun. It does not delete records. Startup does not silently alter schema. An unmigrated service can serve the existing baseline, but health reports `storage_ready: false` and saved-decision operations return `storage_not_ready` / 503. A migration error is not a reason to delete an existing database.

SQLite uses WAL, foreign keys on every connection, bounded lock waits and short write transactions. Brief and hypothesis version rows cannot be updated or deleted: database triggers enforce append-only history. Deferred foreign keys require every current revision to reference an existing version. Migration downgrade is deliberately unavailable because it would destroy this history.

Data is stored locally in plain SQLite. `backend/data/`, SQLite files, .env and .venv are ignored by Git. This is a single-user local API without authentication or multi-user authorization. Human authorship labels identify manual API input; they do not certify a person's identity. Do not expose the server publicly.

## Browser origins

The shared defaults and .env.example now include both the frontend (localhost / 127.0.0.1 on 5173) and Swagger (localhost / 127.0.0.1 on 8000). PATCH preflights are supported. Existing .env settings override defaults; preserve your working origins. If necessary, edit its existing setting to:

```dotenv
CHANAKYA_ALLOWED_ORIGINS=["http://localhost:5173","http://127.0.0.1:5173","http://localhost:8000","http://127.0.0.1:8000"]
```

Add an actual alternate local Vite port explicitly if needed. Restart after configuration changes. There is no wildcard CORS, HTTP proxy inheritance, remote-model fallback or public tunnel.

## API

Open `http://127.0.0.1:8000/docs`. The raw contract is `/openapi.json`; the generated snapshot is `docs/openapi.json`. Swagger's default visual assets may need internet, but installed-model inference and storage are local.

| Method and path | Purpose |
| --- | --- |
| GET /api/v1/health | Liveness and schema readiness, not model execution success |
| GET /api/v1/models/status | Installed local model digest and loaded metadata |
| POST /api/v1/baseline | Existing real single-agent direct / supplied-source assessment |
| POST /api/v1/sessions | Save a decision brief; returns server UUID and revision 1 |
| GET /api/v1/sessions | Paginated saved decisions, ordered by latest activity |
| GET /api/v1/sessions/{session_id} | Read the current brief and hypothesis count |
| PATCH /api/v1/sessions/{session_id} | Replace the brief using expected_revision and revision_reason |
| GET /api/v1/sessions/{session_id}/brief-versions | Read immutable brief history |
| POST /api/v1/sessions/{session_id}/hypotheses | Save a typed, human-authored candidate claim |
| GET /api/v1/sessions/{session_id}/hypotheses | List up to three hypothesis identities |
| GET /api/v1/sessions/{session_id}/hypotheses/{hypothesis_id} | Read a current hypothesis and context_outdated flag |
| GET /api/v1/sessions/{session_id}/hypotheses/{hypothesis_id}/versions | Paginated immutable content / status history |
| POST /api/v1/sessions/{session_id}/hypotheses/{hypothesis_id}/revisions | Append a revised claim or explicit brief rebase |
| POST /api/v1/sessions/{session_id}/hypotheses/{hypothesis_id}/transitions | Append a permitted lifecycle change with a reason |

Pagination accepts limit 1–50 and offset 0–100000. Session revision refers to its brief only; adding a hypothesis updates activity time without changing the brief revision. A session is a saved decision context, not a research run or a final recommendation. Runs and their execution ledger come later.

### Create a session in Swagger

```json
{
  "query": "Should our organisation approve full deployment?",
  "domain_key": "education",
  "objective": "Decide the permitted deployment scope",
  "constraints": ["Only the library pilot is approved"],
  "success_criteria": ["Remain within the approved scope"]
}
```

Save the returned session_id. Domain keys are not restricted to preset domains: use lowercase letters, digits, underscores or hyphens, starting with a letter. Optional selected_domains and specifications support domain-independent briefs. Unknown fields are rejected.

### Add a hypothesis to that session

POST `/api/v1/sessions/{session_id}/hypotheses`:

```json
{
  "expected_session_revision": 1,
  "content": {
    "type": "factual",
    "claim": "Full deployment is not approved.",
    "scope": "Synthetic policy S1; manually supplied claim, not verified evidence"
  }
}
```

The server assigns hypothesis and version UUIDs. It does not treat this text as a model finding or supporting evidence. Every hypothesis begins as proposed, with probability status not_assessed and null prior/posterior. Requests cannot supply a posterior, agent execution ID or human-review certification.

| Type | Additional required structure |
| --- | --- |
| factual | Claim and scope |
| causal | Cause, effect and at least one declared assumption |
| comparative | At least two distinct alternatives and at least one criterion |
| predictive | Measurable outcome and time horizon |
| diagnostic | Latent state and observed facts |
| normative | Explicit values/preferences |

Every content type accepts bounded assumptions and optional jurisdiction. These fields record what must be investigated; they do not prove causation, diagnose a condition or establish a probability.

### Versioning and lifecycle

Edits require the expected current revision. Conflicting edits return 409 rather than overwriting each other. A brief update marks earlier hypothesis context as outdated without changing old rows. To rebase, submit a hypothesis revision with the current expected_session_revision and a reason; unchanged content is allowed only when the brief snapshot changed.

A content revision creates a new version with status revised and a predecessor link. It may change hypothesis type but must satisfy that type's schema. Status changes also append immutable versions. Identical edits and duplicate status changes return 409; a network retry is not permission to reuse a stale revision.

Available manual transitions are proposed → under_investigation, revised → under_investigation, and under_investigation → inconclusive. Under investigation is a user-recorded state, not a running agent job. Inconclusive is terminal and requires a reason. Terminal records cannot be reopened; begin a new hypothesis within the three-identity cap or a new session. Content revision is allowed only for nonterminal history.

Supported, challenged and resolved are reserved lifecycle types. Requests for those statuses return evidence_workflow_not_available until genuine evidence links and adjudication rules exist. No fake validation or confidence numbers are created. There is no deletion API in this increment.

## Validate storage and model execution separately

Isolated checks:

```powershell
.\.venv\Scripts\python.exe -m pytest -q -m "not live"
```

The execution host passed 89 tests covering the original model boundary and the new persistence/versioning behavior. A Starlette HTTPX test-client deprecation warning remains; it is not a failed test. Dependencies were checked on Python 3.12 on Linux; native Windows execution of Increment 2 and your laptop's model connection still need the commands below. Increment 1's 49 isolated and one live check already passed on your laptop.

With the API running, `scripts/smoke-storage.ps1` creates clearly labelled synthetic records and checks version preservation. If your local policy permits script execution, run it from a second terminal inside backend:

```powershell
.\scripts\smoke-storage.ps1
```

It prints a reload_url. Stop and restart the API, then GET that exact URL to verify the record remains. Each script invocation creates a new synthetic session; it is not a cleanup command. If scripts are blocked, use the equivalent Swagger requests above without changing execution policy.

To retest real Ollama inference independently:

```powershell
$env:CHANAKYA_RUN_LIVE_TESTS = "1"
try {
    .\.venv\Scripts\python.exe -m pytest -q -m live -s
}
finally {
    Remove-Item Env:CHANAKYA_RUN_LIVE_TESTS -ErrorAction SilentlyContinue
}
```

Tests use temporary databases and never erase the configured application data. The opt-in live test calls real Ollama and prints its answer for semantic inspection. No live inference success is claimed from this execution host.

## Existing baseline request

POST `/api/v1/baseline`:

```json
{
  "mode": "source_grounded",
  "question": "Is full deployment approved?",
  "sources": [{
    "id": "S1",
    "title": "Synthetic policy",
    "excerpt": "Only a library pilot is approved. Full deployment is not approved."
  }]
}
```

The baseline still does not save its result or auto-create hypotheses. Direct mode is unsourced. Source-grounded mode uses only supplied excerpts, not retrieved documents. Valid source IDs do not prove semantic support or source authenticity. Response metadata distinguishes those limits. There is no private chain-of-thought exposure or fabricated confidence.

Prompts must fit a conservative byte-based context ceiling that includes the schema and reserves output space. Oversized input is rejected, not truncated. Output exhaustion and invalid responses do not become partial successes. One invalid-output regeneration is allowed; timeouts and model-loading failures are not automatically retried. The complete operation has a deadline and unknown usage metadata is null. Registry digest is observed before inference, not a cryptographic execution attestation.

## Errors and troubleshooting

Responses share `{error: {code, message, retryable, details}, request_id}`. Swagger now documents this actual envelope, including 403, 409, 422 and 503. Validation errors omit submitted input contents. Logs contain request ID/method/status/timing, not questions, claims, source excerpts or generated answers.

| Error | Meaning / action |
| --- | --- |
| storage_not_ready / 503 | Run the explicit migration command; preserve an existing database |
| storage_unavailable / 503 | Storage is locked or inaccessible; stop competing writers and check the local disk |
| revision_conflict / 409 | Reload the current version, review and resubmit with that revision |
| context_outdated / 409 | Explicitly revise against the current decision brief |
| hypothesis_limit / 409 | This increment permits three hypothesis identities per session |
| no_change / 409 | No new version was created for an identical write |
| invalid_transition / 409 | Requested lifecycle edge is not allowed |
| terminal_hypothesis / 409 | Preserve terminal history; start a new candidate/session |
| evidence_workflow_not_available / 409 | Genuine evidence/evaluation is needed before these statuses can be used |
| session_not_found or hypothesis_not_found / 404 | Missing UUID or hypothesis outside the requested session |
| invalid_request / 422 | Check typed fields, lengths and revision numbers; unknown fields are rejected |
| origin_not_allowed / 403 | Include your exact local browser origin in .env and restart |
| model_unavailable / 503 | Open Ollama and confirm its local endpoint is available |
| model_not_installed / 503 | Use the exact already-installed local model tag |
| model_load_failed / 503 | Free RAM/VRAM; retry manually |
| model_timeout / 504 | Inspect local model speed/resources; no partial answer is returned |
| model_busy / 429 | Wait for the active model operation; keep one worker |
| invalid_model_output / 502 | Structured output/citation checks failed after bounded attempts |
| model_output_truncated / 502 | Output budget exhausted; no truncated assessment accepted |
| prompt_budget_exceeded / 422 | Shorten excerpts/question rather than increasing GPU context blindly |
| model_digest_mismatch / 503 | Reconcile an intentional weight version change before updating its optional pin |

## Code structure and scope

`app/decisions/schemas.py` defines domain-independent briefs and discriminated hypothesis types; `repository.py` performs bounded transactions and revision checks; `routes.py` exposes synchronous storage endpoints off the async event loop. `app/db/database.py` owns connection policy; migrations own schema changes. The original model provider and baseline service remain separate.

This increment deliberately stops at saved typed state. There is no document ingestion, evidence retrieval, saved model execution ledger, agent orchestration, inference engine, human final-decision submission or frontend integration yet. Review the local result before the next increment.
