# Increment 4 — Saved document-grounded answers

Links existing evidence snapshots to the local Qwen baseline and saves validated answers, original brief/evidence context, model metadata and limitations. Adds idempotent completed-request replay and immutable history. Does not alter frontend, hypothesis status or probability state.

Current API, limits, migration and inline PowerShell checks: [backend guide](../backend/docs/INCREMENT_4.md).

Validation: 139 non-live tests passed on Linux/Python 3.12; two real-model tests are provided for the local Ollama machine. No new dependencies. Citation existence is checked; factual support and source authenticity remain unverified. Failed/interrupted runs are not persisted as a job ledger.
