# Backend Increment 3 — local document and evidence foundation

Version 0.3.0 adds bounded text, Markdown and text-PDF ingestion, original document downloads, extracted-page inspection, exact passage provenance and persisted lexical retrieval snapshots. It preserves the existing local Qwen baseline and versioned session/hypothesis records. No frontend source, CSS or illustration is part of the patch.

SQLite migration 0002_evidence adds immutable documents, passages and retrieval_snapshots. Original bytes, SHA-256 hashes, extracted pages and passages commit atomically. A repeated same-byte upload within a session reuses its identity. Source IDs are stable within a document version. Every snapshot retains its original query, brief revision, corpus version IDs and ranked passages; a later upload does not alter an earlier result.

This is the lexical stage of the planned retrieval system. BM25 relevance is not confidence, credibility or proof. The implementation does not claim semantic search, source authenticity verification, entailment verification, OCR, source invalidation/replacement, research execution records or model-generated cited answers. Those require subsequent work and review. Document uploads do not change hypothesis states.

The API uses raw binary/text upload bodies rather than multipart forms. Limits are one MiB per upload, 100,000 extracted characters, 20 PDF pages, ten documents per session, one active extraction per process and a 15-second PDF subprocess timeout. Windows does not receive the POSIX subprocess RAM limit; this local development service is for trusted PDFs, not hostile uploads. Empty/scanned PDFs are rejected rather than silently marked as successful. Mixed empty pages are reported.

The existing exact local browser origins and structured error contract remain. Normal JSON endpoints retain their smaller body limit. Upload filenames cannot be paths, source files are not executed, and no URLs or external document services are fetched. Application storage remains ignored by Git. The API remains single-user and unauthenticated, bound to loopback.

Detailed routes, limitations, extraction provenance, Windows commands and an inline evidence smoke test are in `backend/docs/INCREMENT_3.md`. A fresh local model inference test is not claimed from the execution host; evidence ingestion/retrieval does not require Ollama.

Validation includes all original isolated tests plus text/PDF extraction, UTF-8 handling, size/type/page limits, subprocess timeout, extraction concurrency, deduplication, hashes, exact offsets, cross-session isolation, immutable rows, stale revisions, empty results, corpus snapshots, cap enforcement under concurrent writes, privacy logs, preservation through migration and persistence after restart. Real Uvicorn HTTP upload/search/download and snapshot survival after a server-process restart also passed on Python 3.12/Linux. Windows wheel availability was checked; native Windows execution still requires the supplied install/test steps.

Review the saved evidence and limitations on the laptop before extending this foundation with semantic retrieval, saved model executions, evidence assessment and collaborative agents. The UI is not connected to these endpoints yet.
