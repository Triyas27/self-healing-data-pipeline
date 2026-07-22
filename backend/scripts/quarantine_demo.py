import asyncio
import logging
from collections import Counter

from sqlalchemy import select

from app.config import settings
from app.core.alerting import AlertPayload, send_quarantine_alert
from app.core.pipeline.quarantine import list_quarantine_rows, persist_quarantine_row, resolve_quarantine_row
from app.core.pipeline.repair.repair import repair_row
from app.core.pipeline.validation import validate_batch
from app.db.session import AsyncSessionLocal, init_db
from app.models import CustomerReference, Run
from app.synthetic.generator import FailureMode, generate_batch, known_customer_ids

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

NON_DRIFT_MODES = [m for m in FailureMode if m != FailureMode.SCHEMA_DRIFT]


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
        known_ids = set(known_customer_ids())

        run = Run(row_count=len(NON_DRIFT_MODES))
        db.add(run)
        await db.commit()
        await db.refresh(run)

        rows = [
            generate_batch(row_count=1, failure_rate=1.0, failure_mode=mode, seed=100 + i).rows[0]
            for i, mode in enumerate(NON_DRIFT_MODES)
        ]
        result = validate_batch(rows, known_ids)

        quarantined_ids = []
        for row_result in result.invalid_rows:
            outcome = await repair_row(row_result, known_ids, max_attempts=settings.max_repair_attempts, use_llm=False)
            if not outcome.healed:
                q = await persist_quarantine_row(db, run.id, row_result, outcome)
                quarantined_ids.append(q.id)

        quarantine_rows = await list_quarantine_rows(db, run_id=run.id)
        error_type_counts = Counter(q.error_type for q in quarantine_rows)
        print(f"\nPersisted {len(quarantined_ids)} quarantine rows for run {run.id}: {dict(error_type_counts)}\n")

        send_quarantine_alert(
            AlertPayload(run_id=run.id, quarantined_count=len(quarantined_ids), error_types=dict(error_type_counts))
        )

        unresolved_before = await list_quarantine_rows(db, run_id=run.id, resolved=False)
        print(f"\nUnresolved before: {len(unresolved_before)}")
        await resolve_quarantine_row(db, quarantined_ids[0])
        unresolved_after = await list_quarantine_rows(db, run_id=run.id, resolved=False)
        print(f"Unresolved after resolving row {quarantined_ids[0]}: {len(unresolved_after)}")


if __name__ == "__main__":
    asyncio.run(main())
