"""Seeds a handful of varied runs so the dashboard looks like a system that's
actually been used, instead of the empty state a fresh clone starts with.

The backend now does this automatically on startup if the database has no
runs (see app.core.demo_seed, used from app.main's lifespan), so this script
is mainly useful for seeding a local dev database without starting the
server, or for rerunning after a manual reset. Safe to run once against a
fresh database; refuses to touch anything if runs already exist -- delete
backend/data/pipeline.db and re-run this script if you want to regenerate
the demo data from scratch instead.
"""

import asyncio

from sqlalchemy import func, select

from app.core.demo_seed import seed_demo_data
from app.db.session import AsyncSessionLocal, init_db
from app.models import CustomerReference, Run
from app.synthetic.generator import known_customer_ids


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
        await seed_customers(db)

        result = await seed_demo_data(db)
        if result is None:
            existing = await db.scalar(select(func.count()).select_from(Run))
            print(f"Found {existing} existing run(s) -- refusing to seed on top of real data.")
            print("Delete backend/data/pipeline.db and re-run this script for fresh demo data.")
            return

        for run in result.runs:
            print(
                f"Run {run.id}: {run.row_count} rows -> clean={run.clean_first_pass} "
                f"healed={run.healed} quarantined={run.quarantined} status={run.status}"
            )
        for quarantine_id in result.resolved_quarantine_ids:
            print(f"Resolved quarantine row {quarantine_id}")

    print("\nDemo data seeded. Start the frontend and backend and open the dashboard.")


if __name__ == "__main__":
    asyncio.run(main())
