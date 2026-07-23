# Self-Healing Data Pipeline

[![CI](https://github.com/Triyas27/self-healing-data-pipeline/actions/workflows/ci.yml/badge.svg)](https://github.com/Triyas27/self-healing-data-pipeline/actions/workflows/ci.yml)

A system that ingests messy real-world order data, validates it against a defined schema, and automatically diagnoses and repairs a fixed set of known failure classes before falling back to human-reviewed quarantine.

Full requirements: [Self-Healing-Pipeline-Requirements.docx](Self-Healing-Pipeline-Requirements.docx)

## Stack

- **Backend**: FastAPI, SQLAlchemy (SQLite by default, Postgres via config), Groq SDK
- **Frontend**: React + Vite dashboard
- **Deployment**: Docker / docker-compose

## How it's put together

- **Data layer**: SQLAlchemy models for orders, runs, quarantine, and audit history, plus a Pydantic schema that validates format, ranges, and enums on the way in.
- **Synthetic data generator**: produces batches of fake orders with a configurable failure rate, or a single named failure type for isolated testing.
- **Ingestion & validation**: reads a CSV (upload, path, or generated batch), normalizes it, and checks it against the schema and the known-customers list. Bad rows get isolated instead of failing the whole batch, unless the CSV itself has an unexpected column, in which case the whole thing gets rejected.
- **Diagnosis**: an LLM call (Groq) or a deterministic heuristic fallback figures out what's wrong with a row and proposes a fix from a small fixed set of transforms, or says it can't be fixed. No fabricated values, ever.
- **Repair & quarantine**: applies the fix, re-validates, and retries up to a cap. Anything that can't be healed goes to quarantine with the full history of what was tried.
- **Orchestration**: ties all of the above into one tracked run and logs stats as it goes.
- **API + dashboard**: FastAPI backend, React frontend, for triggering runs and browsing what happened.

See [docs/architecture.md](docs/architecture.md) for more detail on each piece.

## Getting Started

```bash
# backend
cd backend
cp .env.example .env
pip install -r requirements.txt
uvicorn app.main:app --reload

# frontend
cd frontend
npm install
npm run dev
```

## License

[MIT](LICENSE)
