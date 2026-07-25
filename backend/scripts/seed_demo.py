"""Seeds a handful of varied runs so the dashboard looks like a system that's
actually been used, instead of the empty state a fresh clone starts with.

Safe to run once against a fresh database. Refuses to touch anything if runs
already exist -- delete backend/data/pipeline.db and re-run this script if
you want to regenerate the demo data from scratch instead.
"""

import asyncio
import io

from sqlalchemy import func, select

from app.core.pipeline.orchestrator import run_pipeline
from app.core.pipeline.quarantine import list_quarantine_rows, resolve_quarantine_row
from app.db.session import AsyncSessionLocal, init_db
from app.models import CustomerReference, Run
from app.synthetic.generator import FailureMode, generate_batch, known_customer_ids, to_csv_string

# Deliberately curated, not random: each run's row_count is bigger than the
# ones before it, so most of its rows land on order_id indices no earlier run
# has already claimed. The synthetic generator always numbers rows from 1
# within a batch, so triggering several runs against the same database makes
# later runs increasingly likely to collide on duplicate_order_id -- ordering
# it this way keeps that a minor flavor of the data instead of dominating it.
RUNS = [
    dict(row_count=30, failure_rate=0.2, failure_mode=FailureMode.TYPE_MISMATCH, seed=1),
    dict(row_count=15, failure_rate=0.3, failure_mode=FailureMode.INVALID_FOREIGN_KEY, seed=9),
    dict(row_count=60, failure_rate=0.15, failure_mode=FailureMode.DATE_FORMAT_SWAP, seed=2),
    dict(row_count=90, failure_rate=0.12, failure_mode=FailureMode.ENCODING_ISSUE, seed=3),
    dict(row_count=300, failure_rate=0.1, failure_mode=FailureMode.TYPE_MISMATCH, seed=4),
]


async def seed_customers(db) -> None:
    result = await db.execute(select(CustomerReference.customer_id))
    existing = set(result.scalars().all())
    for cid in known_customer_ids():
        if cid not in existing:
            db.add(CustomerReference(customer_id=cid))
    await db.commit()


async def main() -> None:
    await init_db()
    async with AsyncSessionLocal() as db:
        existing_runs = await db.scalar(select(func.count()).select_from(Run))
        if existing_runs:
            print(f"Found {existing_runs} existing run(s) -- refusing to seed on top of real data.")
            print("Delete backend/data/pipeline.db and re-run this script for fresh demo data.")
            return

        await seed_customers(db)

        for params in RUNS:
            batch = generate_batch(**params)
            csv_text = to_csv_string(batch.rows)
            run = await run_pipeline(db, io.StringIO(csv_text), use_llm=False)
            print(
                f"Run {run.id}: {run.row_count} rows -> clean={run.clean_first_pass} "
                f"healed={run.healed} quarantined={run.quarantined} status={run.status}"
            )

        # Resolve a couple of rows so the quarantine page shows a natural mix
        # of resolved/unresolved instead of everything sitting untouched.
        unresolved = await list_quarantine_rows(db, resolved=False, limit=2)
        for row in unresolved:
            await resolve_quarantine_row(db, row.id)
            print(f"Resolved quarantine row {row.id}")

    print("\nDemo data seeded. Start the frontend and backend and open the dashboard.")


if __name__ == "__main__":
    asyncio.run(main())
