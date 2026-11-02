# Increment 4 — Saved document-grounded single-agent answers

## Scope

Connect an immutable Increment 3 evidence snapshot to the existing local Qwen baseline. Save each successfully validated response together with the exact brief, complete evidence snapshot, input hash, registry model digest, prompt/configuration version, attempts, token usage when available, timing, limitations and source IDs. Existing UI, baseline, upload, retrieval and hypothesis APIs remain available. No new dependency or model download is required.

This is not the multi-agent council, hypothesis adjudication, semantic retrieval, probability engine, or final decision workflow. The frontend is still separate. Documents can contain inaccurate information; valid citation IDs do not verify factual support or document authenticity.

## API

All endpoints are under `/api/v1/sessions/{session_id}/answers`.

| Method | Path | Behavior |
| --- | --- | --- |
| POST | base path | Generate and save, or replay a previously completed request; HTTP 200 in both cases |
| GET | base path | Bounded list: limit 1–20 (default 10), offset 0–100000; deterministic answer-ID ordering |
| GET | `/{answer_id}` | Read the complete immutable saved record |

POST JSON:

```json
{
  "snapshot_id": "a-real-snapshot-UUID-from-evidence-search",
  "expected_session_revision": 1,
  "idempotency_key": "a-new-client-generated-UUID"
}
```

The three fields are required. Use `[guid]::NewGuid().ToString()` to create a key. Reuse exactly the same key, snapshot and revision when retrying a completed request. Reusing that key for different input returns 409. Replaying a historical completed request returns the old record, explicitly labelled with its brief revision; it does not regenerate against a newer brief. A new analysis needs a new key and a snapshot for the current brief.

Only the saved brief's `query` and all retrieved passage source IDs, filenames and excerpts enter the baseline prompt. The retrieval query does not replace the decision question. Other brief fields are archived for review, not automatically inserted into the model prompt in this increment. `model_input_sha256` hashes canonical JSON of this BaselineRequest, not the full system prompt or model weights. The stored prompt version identifies the existing baseline system/repair instructions.

## Limits and failure behavior

- The snapshot must belong to the session and match its current brief revision. Cross-session/unknown snapshots return 404; stale context returns 409.
- Empty snapshots return 422 `no_evidence` without a model call. More than three passages returns 422 `evidence_limit`; retrieve again with `limit=3` or less. No silent dropping/truncation.
- Existing conservative prompt-byte limits remain. Large questions/excerpts may return 422 `prompt_budget_exceeded`; reduce the question or retrieve fewer passages.
- One saved-answer operation at a time per app process. Busy operations return 429. `/baseline` and this route share the same model lock. Use a single Uvicorn worker for this local prototype; locks are not distributed.
- No database transaction remains open during inference. A brief edit while Qwen is running makes completion return 409; that output is not saved. The computation may still have used GPU time.
- Existing deadline (120 seconds), at most two validation attempts, local-only provider, telemetry validation and sanitized errors remain unchanged.
- Invalid model JSON, invented/duplicate citation IDs and unsupported no-citation success responses cannot become saved answers. A structurally valid abstention is stored with `insufficient_evidence=true`; `status=completed` means the operation completed, not that evidence was sufficient or a decision approved.
- Only successful validated completions are persisted. Failed, cancelled, interrupted and rejected runs are not a durable job ledger. No background queue, recovery scheduler or exactly-once inference guarantee across crashes is claimed. If inference finishes but saving fails, retrying may call Qwen again.
- An existing valid completion can be replayed without Ollama. Failed requests do not reserve their key.
- Saving an answer does not transition any hypothesis, assign probabilities or claim human approval. No sources are fetched from the web.
- SQLite adds immutable `saved_answers` and a supporting unique snapshot context index. Foreign keys bind each record to the matching session, brief and snapshot. UPDATE/DELETE triggers reject history changes.
- Registry digest is observed before inference; it is not execution attestation or a hash of all loaded runtime state.

## Install

Stop the backend with Ctrl+C before applying `increment-4.patch`. Apply it once to the clean, committed Increment 3 branch. No dependency changes are needed. Preserve `.env` and the existing database.

From the backend directory, an optional consistent SQLite backup can be made before migration:

```powershell
.\.venv\Scripts\python.exe -c 'from app.core.config import Settings; import sqlite3; from datetime import datetime; p=Settings().database_path; src=sqlite3.connect(str(p)); dst=sqlite3.connect(str(p.with_name("backup-before-inc4-"+datetime.now().strftime("%Y%m%d-%H%M%S")+".sqlite3"))); src.backup(dst); dst.close(); src.close(); print("Database backup complete.")'
.\.venv\Scripts\python.exe -m app.db.migrate
.\.venv\Scripts\python.exe -m pytest -q -m "not live"
```

The migration is repeatable and retains old brief/evidence records. Do not revert application code to Increment 3 while using an Increment 4 database; its readiness check expects its own schema revision. Downgrades are intentionally blocked.

Start the backend in a dedicated terminal and keep it running:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000 --no-access-log
```

## Real local-model end-to-end check

Keep Ollama open with the installed `qwen2.5:3b`. In a separate PowerShell terminal, paste this inline block (no execution-policy change needed):

```powershell
$ErrorActionPreference = "Stop"
$api = "http://127.0.0.1:8000"
$health = Invoke-RestMethod "$api/api/v1/health"
if (-not $health.storage_ready -or $health.increment -ne 4) {
    throw "Start the migrated Increment 4 backend first."
}
$brief = @{ query = "Is full deployment approved?"; domain_key = "education" } | ConvertTo-Json
$decision = Invoke-RestMethod "$api/api/v1/sessions" -Method Post -ContentType "application/json" -Body $brief
$sessionUrl = "$api/api/v1/sessions/$($decision.session_id)"
$policyPath = Join-Path $env:TEMP ("chanakya-policy-" + [guid]::NewGuid().ToString("N") + ".txt")
Set-Content -LiteralPath $policyPath -Encoding utf8NoBOM -NoNewline -Value "Synthetic policy: Only a library pilot is approved. Full deployment is not approved."
try {
    $document = Invoke-RestMethod "$sessionUrl/documents?filename=policy.txt&expected_session_revision=1" -Method Post -ContentType "text/plain" -InFile $policyPath
}
finally {
    Remove-Item -LiteralPath $policyPath -ErrorAction SilentlyContinue
}
$query = @{ query = "full deployment approved"; expected_session_revision = 1; limit = 1 } | ConvertTo-Json
$snapshot = Invoke-RestMethod "$sessionUrl/evidence/search" -Method Post -ContentType "application/json" -Body $query
if ($snapshot.passages.Count -ne 1) { throw "Expected one policy passage." }
$answerRequest = @{
    snapshot_id = $snapshot.snapshot_id
    expected_session_revision = 1
    idempotency_key = [guid]::NewGuid().ToString()
} | ConvertTo-Json
# This is a real call to your local Qwen model.
$answer = Invoke-RestMethod "$sessionUrl/answers" -Method Post -ContentType "application/json" -Body $answerRequest -TimeoutSec 180
if ($answer.response.assessment.insufficient_evidence) { throw "The model abstained. Share its response for inspection." }
if ($answer.response.assessment.source_ids.Count -ne 1 -or $answer.response.assessment.source_ids[0] -cne $snapshot.passages[0].source_id) {
    throw "Expected the supplied policy passage to be cited."
}
# Repeating a completed request returns the same saved answer, without another inference.
$replay = Invoke-RestMethod "$sessionUrl/answers" -Method Post -ContentType "application/json" -Body $answerRequest -TimeoutSec 180
if ($replay.answer_id -ne $answer.answer_id) { throw "Replay did not return the original answer." }
$answerUrl = "$sessionUrl/answers/$($answer.answer_id)"
$loaded = Invoke-RestMethod $answerUrl
if ($loaded.response.assessment.answer -cne $answer.response.assessment.answer) { throw "Saved answer differs." }
$checkPath = Join-Path $env:TEMP "chanakya-answer-restart-check.json"
@{
    answer_url = $answerUrl
    answer_id = $answer.answer_id
    answer_text = $answer.response.assessment.answer
    source_id = $snapshot.passages[0].source_id
} | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $checkPath -Encoding utf8
$answer | ConvertTo-Json -Depth 20
Write-Host "Saved-answer checks passed. Read the answer above and verify it says full deployment is not approved."
Write-Host "After restarting the backend, run the restart check in the guide."
```

The assertions check structure, references, persistence and replay. Read the returned answer to assess its meaning; these checks do not establish general model accuracy.

Restart the backend, wait for `Application startup complete`, then run this in any other terminal:

```powershell
$ErrorActionPreference = "Stop"
$check = Get-Content -LiteralPath (Join-Path $env:TEMP "chanakya-answer-restart-check.json") -Raw | ConvertFrom-Json
$saved = Invoke-RestMethod $check.answer_url
if ($saved.answer_id -ne $check.answer_id -or $saved.response.assessment.answer -cne $check.answer_text) {
    throw "Saved answer differs after restart."
}
if ($saved.response.assessment.source_ids -cnotcontains $check.source_id) {
    throw "Saved citation differs after restart."
}
Write-Host "Saved answer and citation survived the backend restart."
```

## Opt-in live tests

The regular suite uses controlled model responses; it does not call a real model. Two live tests are available (the original baseline plus the new upload/retrieve/generate/save/replay path). They use an isolated temporary database, not your saved project decisions:

```powershell
$env:CHANAKYA_RUN_LIVE_TESTS = "1"
try {
    .\.venv\Scripts\python.exe -m pytest -q -m live -s
}
finally {
    Remove-Item Env:CHANAKYA_RUN_LIVE_TESTS -ErrorAction SilentlyContinue
}
```

## Validation

139 non-live tests passed on Linux/Python 3.12 using the existing pinned dependencies. This includes source provenance, idempotent replay, restart reads, session isolation, malformed input, invalid citations, abstention, empty/excess evidence, oversized prompts, timeout recovery, concurrent model capacity, context changes during inference, append-only storage and upgrade from Increment 3. The two live tests need execution on the user's Ollama machine; they were not run in the build environment. Existing Starlette/httpx deprecation warning remains; no dependency churn is introduced.
