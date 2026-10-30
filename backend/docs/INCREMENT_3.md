# Increment 3 — local documents and traceable lexical evidence

The existing local model baseline and saved sessions/hypotheses remain intact. Version 0.3.0 adds document ingestion, extracted-page inspection, original downloads, keyword retrieval and immutable retrieval snapshots. It does not change the frontend or connect it to the API.

This is the lexical retrieval foundation. Semantic embeddings, hybrid search, source invalidation/replacement, OCR, document-grounded model execution, multi-agent reasoning and probabilistic inference remain later work. No new model download or cloud account is required.

## Install an update

Stop Uvicorn first, apply the incremental patch from the package, then run inside backend:

```powershell
$ErrorActionPreference = "Stop"
$PSNativeCommandUseErrorActionPreference = $true
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m app.db.migrate
.\.venv\Scripts\python.exe -m pytest -q -m "not live"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000 --no-access-log
```

Use the existing Python 3.12 environment. Preserve `.env`, the SQLite database and existing records. Migration 0002_evidence adds three tables without dropping or rewriting the original decision tables. It is safe to rerun. Always stop on migration errors rather than deleting an existing database. Health must report increment 3 and storage_ready true.

## Upload contract

Uploads are **raw file bytes**, not multipart forms or JSON. The filename and expected_session_revision are query parameters. Swagger documents binary bodies; the PowerShell example below is the most reliable local test.

| Input | Limit / handling |
| --- | --- |
| UTF-8 .txt | Content-Type text/plain |
| UTF-8 .md | Content-Type text/markdown; treated as text, never executed or rendered as HTML |
| Text-based .pdf | Content-Type application/pdf; requires PDF signature, unencrypted, at most 20 pages |
| Upload bytes | 1 byte through 1 MiB; enforced before parsing, including chunked input |
| Extracted text | At most 100,000 Unicode characters per document |
| Documents | At most ten immutable documents per session |
| Extraction | One active extraction per process; PDF subprocess timeout 15 seconds |
| Passages | Reproducible 500-character windows, 50-character overlap, no cross-page chunks |
| Search | Query 3–1000 characters, up to five hits, optional selection of up to ten session-owned documents |

Scanned or blank PDFs with no readable text are rejected with no_extractable_text. OCR is not implemented. Mixed PDFs expose empty page numbers so missing text is visible. Layouts and tables may extract imperfectly; inspect the original document and extracted pages. The stored original bytes are never rewritten.

PDF extraction uses a subprocess, not a public hostile-file sandbox. POSIX hosts enforce a 512 MiB process address-space ceiling; Windows does not have that RAM ceiling in this implementation. Input/page/text/timeout limits still apply there. Use trusted local PDFs in this single-user development service. Neither pypdf nor the application executes embedded document scripts or follows embedded links. No URL ingestion is provided.

## New endpoints

All paths below are under `/api/v1/sessions/{session_id}`. Session and document IDs are server-assigned UUIDs.

| Method / path | Result |
| --- | --- |
| POST /documents?filename=policy.txt&expected_session_revision=1 | Atomically saves original bytes, extracted pages and passages; returns metadata with IDs and SHA-256 |
| GET /documents | Lists the session's bounded document collection |
| GET /documents/{document_id}/content | Original bytes as an attachment, with nosniff |
| GET /documents/{document_id}/pages/{page} | Stored extracted page text, using one-based page numbers |
| POST /evidence/search | Creates a snapshot of query, brief revision, selected document versions and ranked passages |
| GET /evidence/snapshots/{snapshot_id} | Reads that immutable snapshot without repeating retrieval |

Identical byte content uploaded again within the same session returns the original metadata and IDs, without creating duplicate rows. This operation still returns 201 for compatibility with its create response. A different session gets a separate document identity. A changed file is a new immutable document in this increment; no replacement or deletion API is implemented.

## Storage and provenance

Original bytes, extracted pages, passages and snapshots live in the existing ignored local SQLite database. There is no separate vector database or external index to reconcile yet. A failed extraction saves no document; original bytes and all passages commit in one transaction. Concurrent ingestion cannot bypass the document cap.

Document metadata includes original byte hash, version UUID, media type, filename, size, page count and extraction method version. A passage includes its stable source ID, document/version/hash, page, start/end character offsets and exact text. CRLF/CR is normalized to LF and UTF-8 BOM is removed in extracted text; offsets refer to stored extracted Unicode page text, not PDF bytes or screen geometry.

Retrieval snapshots are append-only. Later uploads do not expand an earlier snapshot. They retain the brief revision used when searching; compare it with the current session revision when revisiting an older snapshot. A new search with a stale expected_session_revision returns 409. This increment does not automatically run a model over an old snapshot.

Search uses a deterministic lexical BM25 ranking over the chosen session corpus, with a small English stopword list and no stemming, embedding or semantic reranking. Missing matches return an empty passage list rather than invented results. Scores are relevance measures, not confidence, source credibility, entailment or factual correctness. A citation belonging to a document does not establish that its text supports a model claim.

Source authenticity and semantic support remain explicitly unverified. Baseline calls still accept supplied excerpts independently; retrieval does not automatically create a recommendation, persist an agent execution or change hypothesis lifecycle status. Numerical probability fields remain untouched and null.

## Inline PowerShell smoke test

With Uvicorn running, paste into another PowerShell terminal. No downloaded .ps1 file or execution-policy change is required. This creates one synthetic test session and a temporary fixture file.

```powershell
$ErrorActionPreference = "Stop"
$api = "http://127.0.0.1:8000"
$brief = @{query="Is full deployment approved?";domain_key="education"} | ConvertTo-Json
$decision = Invoke-RestMethod "$api/api/v1/sessions" -Method Post -ContentType "application/json" -Body $brief
$sessionUrl = "$api/api/v1/sessions/$($decision.session_id)"
$policyPath = Join-Path $env:TEMP ("chanakya-policy-" + [guid]::NewGuid().ToString("N") + ".txt")
Set-Content $policyPath -Encoding utf8NoBOM -NoNewline -Value "Synthetic policy: Only a library pilot is approved. Full deployment is not approved."
$document = Invoke-RestMethod "$sessionUrl/documents?filename=policy.txt&expected_session_revision=1" -Method Post -ContentType "text/plain" -InFile $policyPath
$query = @{query="full deployment approved";expected_session_revision=1;limit=3} | ConvertTo-Json
$evidence = Invoke-RestMethod "$sessionUrl/evidence/search" -Method Post -ContentType "application/json" -Body $query
if ($evidence.passages.Count -lt 1) { throw "Expected a matching policy passage." }
$page = Invoke-RestMethod "$sessionUrl/documents/$($document.document_id)/pages/1"
$hit = $evidence.passages[0]
if ($page.text.Substring($hit.start_char, $hit.end_char - $hit.start_char) -ne $hit.excerpt) { throw "Passage offsets do not match stored text." }
$snapshotUrl = "$sessionUrl/evidence/snapshots/$($evidence.snapshot_id)"
$evidence | ConvertTo-Json -Depth 15
Write-Host "Evidence checks passed. Save this snapshot URL: $snapshotUrl"
```

Stop and restart Uvicorn, then GET `$snapshotUrl` in the same second terminal. It must return the original snapshot and passage. Retrieving evidence does not call Ollama. To retest Qwen independently, use the existing opt-in live test from the earlier guide.

## Errors

Existing structured error envelopes and local origins are retained. New codes include invalid_filename / 422, unsupported_document_type / 415, document_size_limit / 413, invalid_text_encoding / 422, invalid_pdf / 422, pdf_extraction_failed / 422, extraction_timeout / 422, extraction_busy / 429, extracted_text_limit / 422, no_extractable_text / 422, document_limit / 409, document_not_found / 404, page_not_found / 404 and snapshot_not_found / 404. Invalid selections and stale brief revisions fail instead of silently broadening the search. Existing JSON endpoints retain their smaller 16 KiB default body limit.

The API remains loopback-only and single-user without authentication. Data remains local and unencrypted. Application access logs omit request bodies, filenames, questions, extracted text and model answers. Use the provided no-access-log Uvicorn command to avoid logging URL query parameters.

## Verification and next boundary

The execution host uses Python 3.12 on Linux. The isolated tests cover original functionality, ingestion, page/offset fidelity, hashing, deduplication, cross-session access, PDF subprocess behavior, OCR absence, caps, immutable history, migration preservation and restart persistence. Real Uvicorn HTTP upload/search/download and snapshot survival after a process restart were checked separately. The existing Starlette HTTPX deprecation warning remains.

Windows x64/Python 3.12 wheel availability was checked; native Windows execution still needs the supplied commands. No new laptop Ollama test or Windows PDF extraction result is claimed from this host.

The next review should verify evidence correctness and retrieval limitations before introducing semantic retrieval, saved model executions and collaborative reasoning. The approved frontend remains unchanged.

Implementation reference: pypdf text extraction limits and OCR distinctions — https://pypdf.readthedocs.io/en/stable/user/extract-text.html
