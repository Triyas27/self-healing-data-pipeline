# Architecture

## Config & deployment
`backend/app/config.py`, `.env.example`, `Dockerfile`, `docker-compose.yml`

All config (DB connection, LLM credentials, repair attempt caps, alerting endpoints) comes from environment variables. SQLite by default, and switching to Postgres is just changing `DATABASE_URL`, no code changes needed.

## Data layer
`backend/app/models/` (SQLAlchemy: orders, runs, quarantine, audit)
`backend/app/schemas/` (Pydantic: field format, value ranges, enums)
`backend/app/db/` (session/engine factory, swappable SQLite/Postgres)

## Synthetic data generator
`backend/app/synthetic/generator.py`

Generates batches of fake orders with a configurable row count and failure rate. Can also inject one specific failure mode in isolation (schema drift, type mismatch, date format swap, encoding issue, null required field, invalid FK) so you can test one failure class at a time instead of random noise.

## Ingestion & validation
`backend/app/core/pipeline/ingestion.py`, `validation.py`

Reads a CSV from an upload, a file path, or an already-generated batch. Normalizes column names and strips whitespace, then validates format/range/enums and cross-references customer IDs against the known set. An unexpected column in the CSV rejects the whole batch (schema drift); a bad value in an otherwise-fine row is isolated so it doesn't take the rest of the batch down with it.

## Diagnosis
`backend/app/core/pipeline/diagnosis/base.py` (shared types)
`llm_diagnoser.py` (Groq), `heuristic_diagnoser.py` (deterministic fallback)

For each invalid row, comes up with a hypothesis and proposes at most one repair, picked from a small fixed registry, or explicitly declines if nothing safe applies. The "no fix" path is enforced by the type system (a diagnosis can only ever reference a real registered transform or none), not just by asking the LLM nicely. If the LLM call fails or returns something unparseable, it falls back to the heuristic automatically.

## Repair & transform registry
`backend/app/core/pipeline/repair/transform_registry.py`
`backend/app/core/pipeline/repair/transforms/` (one auditable function per fixable failure class, no arbitrary or generated code ever runs)

Applies the proposed fix, re-validates, and repeats up to a configurable attempt cap before giving up and routing to quarantine. Transforms are non-destructive on data that's already valid, which is verified by tests.

## Quarantine & alerting
`backend/app/core/pipeline/quarantine.py`
`backend/app/core/alerting/` (log/Slack/email behind a common interface)

Quarantined rows keep the original data, error type/detail, attempt count, and full diagnosis history. A log alert always fires when a run produces quarantine; Slack/email are best-effort extras that won't break a run if they fail. Operators can mark a row resolved.

## Orchestration & logging
`backend/app/core/pipeline/orchestrator.py`

Wires ingestion → validation → diagnosis → repair → re-validation → quarantine into one tracked run. Every row ends up in either the clean store or quarantine, never dropped. Records one summary entry per run (row counts, error types, fixes applied, avg time-to-heal, status) plus a per-attempt audit trail (hypothesis, transform, confidence, reasoning, source). Works fine offline with no LLM key configured, it just uses the heuristic path.

## API
`backend/app/api/routes/` (health, runs, quarantine, stats)

Health check, trigger a run (synthetic or uploaded CSV), list/retrieve run history, list/filter/resolve quarantined rows, aggregate stats.

## Dashboard
`frontend/src/pages/`, `frontend/src/components/`, `frontend/src/api/`

Totals, heal rate, auto-heal rate, quarantine count, a heal-rate-over-time chart, and a quarantine browser with expandable diagnosis history filterable by resolved status.

## Testing
`backend/tests/unit/` (one module per failure mode, transform, and diagnostic path)
`backend/tests/integration/` (end-to-end pipeline and API runs)

Everything runs without network access or an API key. The LLM diagnoser is tested against a fake client, so the whole suite is fast and deterministic.

## Known limitations

- **No authentication.** Every API route is open — there's no login, API key, or session. This is a deliberate scope cut, not an oversight: the project has no real users or hosted deployment, so account management would be boilerplate that doesn't demonstrate anything the pipeline itself doesn't already cover. A single shared API key behind a FastAPI dependency would be the minimal fix if this ever needed to run somewhere reachable by more than one person.
- **Both Docker containers run as root.** Neither `backend/Dockerfile` nor `frontend/Dockerfile` creates or switches to an unprivileged user, so the process inside each container has root privileges within the container. Same reasoning as auth: these images only ever run locally via `docker-compose` for a demo, never on shared or internet-facing infrastructure, so the actual blast radius of skipping this is zero right now. The fix is a few lines per Dockerfile (`useradd` + `USER` in the backend image, and nginx's own unprivileged mode or a non-root base in the frontend image) if this ever needed to run somewhere that mattered.
