import asyncio
import io
import time

from sqlalchemy import select

from app.core.pipeline.orchestrator import run_pipeline
from app.db.session import AsyncSessionLocal, init_db
from app.models import CustomerReference
from app.synthetic.generator import generate_batch, known_customer_ids, to_csv_string


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

        batch = generate_batch(row_count=50, failure_rate=0.3, seed=35)
        csv_text = to_csv_string(batch.rows)

        started = time.perf_counter()
        run = await run_pipeline(db, io.StringIO(csv_text), use_llm=False)
        elapsed = time.perf_counter() - started

    print(f"Run {run.id}: status={run.status}  (wall time: {elapsed:.2f}s)")
    print(f"  row_count:          {run.row_count}")
    print(f"  clean_first_pass:   {run.clean_first_pass}")
    print(f"  healed:             {run.healed}")
    print(f"  quarantined:        {run.quarantined}")
    print(f"  error_types:        {run.error_types}")
    print(f"  fixes_applied:      {run.fixes_applied}")
    print(f"  avg_time_to_heal_ms:{run.avg_time_to_heal_ms}")
    print(f"  started_at:         {run.started_at}")
    print(f"  finished_at:        {run.finished_at}")


if __name__ == "__main__":
    asyncio.run(main())
