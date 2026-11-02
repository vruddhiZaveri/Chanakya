# Chanakya — Frontend/backend integration 5

## What is connected

The approved dark interface now connects to the Increment 4 local backend. No new dependencies, model download or database migration are introduced.

- New Decision's final Begin Research action validates the saved brief contract, POSTs to `/sessions`, and opens `/decision/research?session=<id>` only after the API saves it. Failed requests keep the draft and show an error. A network failure after creation may leave a saved decision; check My Decisions before creating another one.
- Overview and My Decisions show database sessions, separately from browser-only saved copies. Database lists have bounded pagination; browser search/status filters still apply only to browser copies. No server deletion or server search UI is claimed.
- Research uploads original PDF/TXT/Markdown bytes, lists documents, downloads originals, and filters retrieval by selected document IDs. No checked documents means all documents.
- Retrieval uses the real lexical search API, up to three passages. It shows saved query, immutable snapshot ID, original extracted page text, page number, offsets, original-file SHA-256 and document version. Search relevance is not model confidence.
- Generate cited answer uses the existing saved-answer endpoint with a UUID idempotency key. Repeating against the same snapshot replays the saved result; retrieve again for a new snapshot/request. A key is retained in browser storage when available; the current in-memory key still works if storage is blocked.
- Saved answers show the original question/brief revision, exact cited passages, limitations, model information and explicit lack of semantic/source-authenticity verification. Markdown export contains actual answer data, cited excerpts and provenance.
- Saved answer links include `session` and `answer` IDs. Refreshing reopens the saved record; no automatic inference is triggered. Session context is retained in the six-stage navigation. Other stages remain manual/imported-output views and are not automatically executed.
- Sidebar connection status checks backend/database health only; it does not claim the model is loaded. No fabricated council conversations, probabilities or consensus are added.

## Installation

Place `Chanakya_Frontend_Backend_Integration_5.zip` in the repository root. Stop the frontend and backend terminals with Ctrl+C before applying. Keep your local Ollama application available. Apply once on top of your existing Increment 4 code.

```powershell
cd "C:\1_PLACEMENT\FINAL PROJECTS\chanakya"
$ErrorActionPreference = "Stop"
$PSNativeCommandUseErrorActionPreference = $true

git switch backend/increment-4-grounded-answers
$extractPath = Join-Path $env:TEMP ("chanakya-integration5-" + [guid]::NewGuid().ToString("N"))
Expand-Archive -LiteralPath ".\Chanakya_Frontend_Backend_Integration_5.zip" -DestinationPath $extractPath
$patchPath = Join-Path $extractPath "integration-5.patch"
git apply --check "$patchPath"
git switch -c integration/increment-5-local-research-ui
git apply "$patchPath"

npm.cmd test
npm.cmd run build

cd backend
@'
import json
from pathlib import Path
from dotenv import set_key
from app.core.config import Settings
origins = list(Settings().allowed_origins)
for origin in ["http://localhost:5174", "http://127.0.0.1:5174"]:
    if origin not in origins:
        origins.append(origin)
set_key(str(Path(".env")), "CHANAKYA_ALLOWED_ORIGINS", json.dumps(origins))
print("Local frontend origins configured.")
'@ | .\.venv\Scripts\python.exe -

.\.venv\Scripts\python.exe -m pytest -q -m "not live"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000 --no-access-log
```

Expected: 24 frontend tests, a successful production build, and 140 backend tests (2 live tests deselected). Keep the backend terminal running after `Application startup complete`.

No pip/npm dependency change is needed for an already-working installation. If node_modules is missing, run `npm.cmd ci` from the project root before frontend checks. Preserve the lockfile. No migration is needed because the database schema is unchanged from Increment 4.

The inline Python block updates only `CHANAKYA_ALLOWED_ORIGINS` in the private backend `.env`, preserving its existing allowed origins and other settings. Existing `.env` overrides otherwise take precedence over the updated defaults. Do not commit `.env`.

In a separate terminal:

```powershell
cd "C:\1_PLACEMENT\FINAL PROJECTS\chanakya"
npm.cmd run dev
```

Open http://localhost:5174/. The dev command now binds to loopback and uses port 5174 strictly. If that port is busy, stop the old Chanakya frontend in its own terminal; do not kill unrelated processes or open another project's port. Vite forwards `/api` to local port 8000 with a bounded 180-second proxy timeout. The backend retains its own 120-second model operation deadline. The preview command is configured with the same proxy.

This is local development/preview integration. A standalone static upload or hosted Site cannot access a user's laptop backend through this proxy. Nothing has been deployed or pushed by this update.

## Browser walkthrough with real Qwen

1. Keep backend and frontend terminals running, with Ollama open.
2. Choose New Decision. Enter `Is full deployment approved?`.
3. Context is optional. Choose Custom domain, enter `Education`, then continue to the plan and Begin Research.
4. In the new research workspace, upload `synthetic-policy.txt` from the extracted ZIP.
5. Leave the default search query, or enter `full deployment approved`; choose Retrieve evidence.
6. Inspect the returned passage and original extracted page. Choose Generate cited answer and allow up to two minutes.
7. Expect an advisory answer saying full deployment is not approved, citing the uploaded passage. Read the actual answer: a passing schema/citation check does not prove semantic correctness.
8. Export the answer if useful. Refresh: the exact saved answer should reopen without another Qwen call.
9. Open My Decisions, select the database session and its saved answer. Browser-only copies remain separately labelled.
10. Restart the backend in its own terminal, wait for startup, then refresh/reopen the answer to confirm laptop persistence.

Browser attachments from the earlier context step remain browser-only until individually uploaded using the research panel's Upload to decision action. Unsupported formats/oversized attachments are not silently converted, cropped or discarded. Existing browser attachment handling (up to 10 MB, additional formats) remains available for manual views; the backend upload contract is narrower: PDF/TXT/Markdown, up to 1 MiB, 10 documents, PDFs up to 20 pages, no OCR.

The saved brief's question and retrieved excerpts form the current model input. Objective/constraints/specifications are archived and shown but are not automatically added to the model prompt by Increment 4. New Decision enforces the real server bounds (question <=2000, objective <=1000, up to 10 lines of <=400 characters for constraints/success criteria). Existing browser drafts with longer fields are retained and receive an explicit validation error before saving.

## Errors and recovery

- Backend offline/proxy 500: start the backend on 127.0.0.1:8000, then use Refresh/Retry. Browser drafts are retained.
- `origin_not_allowed`: run the origin configuration block from the backend folder and restart it. Do not use wildcard origins.
- Empty retrieval: try terms from the document or upload relevant evidence. Generate is disabled until passages exist.
- Context/prompt budget: reduce the question or use a narrower document filter; no silent truncation is added.
- Model busy/timeout/invalid output: errors display without creating a fake answer. Retry with the same snapshot. The backend controls validation and retry policy.
- Stale revision 409: Reload saved research and retrieve again against the current brief. Previously saved answers remain explicitly historical.
- Navigating away does not cancel server inference. No background job monitoring or automatic request resumption is claimed.
- Unsaved retrieval selections reset on page refresh. Saved answer links and their evidence persist. Server-side deletion, in-place brief editing, council execution and probability scoring are not part of this integration.

## Validation and limits

- Production build passed after restoring the shipping Vite configuration.
- 24 frontend tests passed: existing model behavior plus brief mapping and limits, document contract, actual-data export, UUID fallback, API error/cancellation handling, raw bytes and encoding, and idempotency payload preservation.
- 140 non-live backend tests passed, including acceptance of both loopback frontend origins on 5174 and all existing stored-answer behavior. Two opt-in live tests remain unchanged from Increment 4, which the user already ran successfully.
- Browser checks used controlled API fixtures because the managed browser preview cannot reach the separate Python execution process. Verified saved-session opening, evidence retrieval, provenance, cited-answer display and reopen on refresh, plus offline API error presentation. This found and fixed missing randomUUID support on HTTP previews. The fixture plugin and fixture data were removed and are not shipped.
- The real API upload/retrieval/answer path was separately exercised using controlled model output; no fresh real Qwen execution or Windows browser verification was performed in this build environment.
- Responsive CSS stacks the research columns below 850px; separate mobile viewport/device verification remains pending.
- The existing Starlette/httpx deprecation warning remains; no dependency substitution is introduced.

## Commit after laptop verification

```powershell
cd "C:\1_PLACEMENT\FINAL PROJECTS\chanakya"
git add src package.json vite.config.ts tsconfig.test.json tests/local-backend.test.mjs backend/app/core/config.py backend/tests/test_api.py backend/README.md docs/FRONTEND_BACKEND_INTEGRATION_5.md README.md
git --no-pager diff --cached --stat
git commit -m "Connect dark research UI to local document and answer APIs"
git push -u origin integration/increment-5-local-research-ui
```

Do not add ZIPs, private `.env`, databases, original-artwork backups or other unrelated files. If Increment 4 changes are still uncommitted, preserve them and commit/review that backend checkpoint separately; never reset or discard them.
