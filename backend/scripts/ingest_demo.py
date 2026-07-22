import asyncio

from sqlalchemy import select

from app.core.pipeline.validation import SchemaDriftError, load_known_customer_ids, validate_batch
from app.db.session import AsyncSessionLocal, init_db
from app.models import CustomerReference
from app.synthetic.generator import FailureMode, generate_batch, known_customer_ids

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
        known_ids = await load_known_customer_ids(db)

    print("== Scenario A: mixed per-row failures, batch still processed ==")
    rows = generate_batch(row_count=8, failure_rate=0.0, seed=1).rows
    for i, mode in enumerate(NON_DRIFT_MODES):
        rows.append(
            generate_batch(row_count=1, failure_rate=1.0, failure_mode=mode, seed=100 + i).rows[0]
        )

    result = validate_batch(rows, known_ids)
    print(f"{len(result.valid_rows)} valid, {len(result.invalid_rows)} invalid")
    for r in result.invalid_rows:
        print(f"  row {r.row_index}: {r.error_type}")

    print("\n== Scenario B: schema drift rejects the whole batch ==")
    drift_rows = generate_batch(
        row_count=5, failure_rate=1.0, failure_mode=FailureMode.SCHEMA_DRIFT, seed=1
    ).rows
    try:
        validate_batch(drift_rows, known_ids)
    except SchemaDriftError as exc:
        print(f"  Batch rejected: {exc}")


if __name__ == "__main__":
    asyncio.run(main())
