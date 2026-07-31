import io
from dataclasses import dataclass, field

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pipeline.orchestrator import run_pipeline
from app.core.pipeline.quarantine import list_quarantine_rows, resolve_quarantine_row
from app.models import Run
from app.synthetic.generator import FailureMode, generate_batch, to_csv_string

# Deliberately curated, not random: each run's row_count is bigger than the
# ones before it, so most of its rows land on order_id indices no earlier run
# has already claimed. The synthetic generator always numbers rows from 1
# within a batch, so triggering several runs against the same database makes
# later runs increasingly likely to collide on duplicate_order_id -- ordering
# it this way keeps that a minor flavor of the data instead of dominating it.
DEMO_RUNS = [
    dict(row_count=30, failure_rate=0.2, failure_mode=FailureMode.TYPE_MISMATCH, seed=1),
    dict(row_count=15, failure_rate=0.3, failure_mode=FailureMode.INVALID_FOREIGN_KEY, seed=9),
    dict(row_count=60, failure_rate=0.15, failure_mode=FailureMode.DATE_FORMAT_SWAP, seed=2),
    dict(row_count=90, failure_rate=0.12, failure_mode=FailureMode.ENCODING_ISSUE, seed=3),
    dict(row_count=300, failure_rate=0.1, failure_mode=FailureMode.TYPE_MISMATCH, seed=4),
]


@dataclass
class SeedResult:
    runs: list[Run] = field(default_factory=list)
    resolved_quarantine_ids: list[int] = field(default_factory=list)


async def seed_demo_data(db: AsyncSession) -> SeedResult | None:
    """Seeds the curated demo runs (and resolves a couple of quarantine rows,
    for a natural-looking mix) if the database has no runs yet. Assumes the
    known-customers reference set is already seeded. Returns None without
    touching anything if any run already exists.
    """
    existing_runs = await db.scalar(select(func.count()).select_from(Run))
    if existing_runs:
        return None

    result = SeedResult()
    for params in DEMO_RUNS:
        batch = generate_batch(**params)
        csv_text = to_csv_string(batch.rows)
        run = await run_pipeline(db, io.StringIO(csv_text), use_llm=False)
        result.runs.append(run)

    unresolved = await list_quarantine_rows(db, resolved=False, limit=2)
    for row in unresolved:
        await resolve_quarantine_row(db, row.id)
        result.resolved_quarantine_ids.append(row.id)

    return result
