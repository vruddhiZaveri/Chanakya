# Backend Increment 2 — saved decisions and typed hypotheses

## Outcome

Chanakya now saves decision contexts locally and preserves immutable brief and hypothesis histories. The existing local Qwen baseline remains available. No frontend source, CSS, route, dependency or illustration changed.

The implementation extends the architecture's `/sessions` contract rather than adding a second incompatible `/decisions` object. A session is a saved user decision context. Research runs, generated recommendations and human final decisions remain distinct future records; none is simulated here.

## Delivered

- SQLite on a local disk through SQLAlchemy 2.x Core, with a versioned Alembic migration.
- Explicit schema upgrade command; health reports schema readiness separately from model readiness.
- UUID-based sessions, bounded list/history reads and optimistic brief revisions.
- Immutable brief versions and hypothesis versions, enforced by database triggers and foreign keys.
- Six discriminated hypothesis types: factual, causal, comparative, predictive, diagnostic and normative.
- Manual hypothesis creation, content revision, predecessor links and reasoned lifecycle history.
- Session-scoped reads/writes; a hypothesis from a different session returns 404. This is data scoping, not authenticated user authorization.
- Context-outdated flags when a brief changes, with an explicit revision required before status progression.
- Three hypothesis identities per session, enforced inside serialized write transactions.
- No invented probabilities: every version reports not_assessed and null prior/posterior.
- Shared Swagger origin fix and PATCH CORS support. The error schema in OpenAPI now matches the actual API envelope.
- Windows setup and smoke commands in `backend/README.md` and `backend/scripts/smoke-storage.ps1`.

Manual lifecycle edges are proposed → under_investigation, revised → under_investigation, and under_investigation → inconclusive. Under investigation does not launch an agent. Supported/challenged/resolved transitions require the later evidence and adjudication workflow and are rejected for now. Content revisions are append-only and cannot reopen terminal hypotheses.

## Schema and consistency

The first migration creates sessions, brief_versions, hypotheses and hypothesis_versions. Session and hypothesis heads reference real current versions using deferred foreign keys. Hypothesis predecessor links must belong to the same identity and immediately prior revision. Every hypothesis version references the exact session brief revision it used.

Writes use short BEGIN IMMEDIATE transactions with foreign keys enabled per connection and bounded SQLite lock waits. WAL is enabled by the migration command. A failed transaction rolls back; concurrent clients cannot both update the same expected revision or exceed the three-hypothesis cap. Updating content or status never mutates previous rows. UTC timestamps are server-generated.

Typed content is a schema-validated API structure stored as JSON alongside relational type/status/version/ownership fields. This increment does not create an evidence link table, execution ledger or probability assessment row with invented provenance. These will be introduced by future migrations when their workflows exist.

Migration must be run explicitly with the virtual environment Python: `python -m app.db.migrate`. Missing or incompatible migration state returns storage_not_ready / 503 for saved-decision operations. No automatic schema drop, overwrite or downgrade is offered. Application data and local configuration remain ignored by Git.

## Validation

- **89 isolated tests passed; one live-model test deselected.** Original baseline regression checks remain, with the health/OpenAPI expectations updated for this increment.
- Tests cover all six types, invalid input, exact error schemas, immutable history, foreign keys, transaction rollback, stale writes, outdated brief contexts, terminal states, cross-session access, pagination, logs and simultaneous writes.
- A real Uvicorn HTTP check created a session and hypothesis, transitioned and revised it, rejected an unsupported evidence status, then restarted the server process. The saved session/hypothesis history remained intact after restart.
- Dependency installation and `pip check` passed on Python 3.12 on the Linux execution host. Windows x64/Python 3.12 binary wheel availability was checked for pinned dependencies; this is not native Windows execution.
- The Starlette HTTPX test-client deprecation warning remains. No extra HTTPX implementation was added solely to hide it.
- The user's earlier Increment 1 result confirmed actual Qwen inference in about 1.85 seconds. This host cannot access the laptop model, so a new live inference pass for Increment 2 is not claimed. Run the retained opt-in live test on the laptop.

## Boundaries and next review

This is still a loopback-only single-user development API, without authentication, document ingestion/retrieval, generated hypotheses, research jobs, multi-agent debate, numerical inference, human final-decision submission or frontend API integration. Baseline responses are not yet persisted as executions. Human-authored labels denote manual API input rather than verified identity.

Validate migration, storage restart behavior and the retained local-model test on Windows. Review the saved typed-state contract before starting the next increment: document/evidence ingestion and traceable retrieval, with proper provenance and run snapshots.
