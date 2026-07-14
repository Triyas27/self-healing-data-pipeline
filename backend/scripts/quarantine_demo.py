import logging
from collections import Counter

from app.config import settings
from app.core.alerting import AlertPayload, send_quarantine_alert
from app.core.pipeline.quarantine import list_quarantine_rows, persist_quarantine_row, resolve_quarantine_row
from app.core.pipeline.repair.repair import repair_row
from app.core.pipeline.validation import validate_batch
from app.db.session import SessionLocal, init_db
from app.models import CustomerReference, Run
from app.synthetic.generator import FailureMode, generate_batch, known_customer_ids

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

NON_DRIFT_MODES = [m for m in FailureMode if m != FailureMode.SCHEMA_DRIFT]


def seed_customers(db) -> None:
    existing = {c.customer_id for c in db.query(CustomerReference).all()}
    for cid in known_customer_ids():
        if cid not in existing:
            db.add(CustomerReference(customer_id=cid))
    db.commit()


def main() -> None:
    init_db()
    db = SessionLocal()
    seed_customers(db)
    known_ids = set(known_customer_ids())

    run = Run(row_count=len(NON_DRIFT_MODES))
    db.add(run)
    db.commit()
    db.refresh(run)

    rows = [
        generate_batch(row_count=1, failure_rate=1.0, failure_mode=mode, seed=100 + i).rows[0]
        for i, mode in enumerate(NON_DRIFT_MODES)
    ]
    result = validate_batch(rows, known_ids)

    quarantined_ids = []
    for row_result in result.invalid_rows:
        outcome = repair_row(row_result, known_ids, max_attempts=settings.max_repair_attempts, use_llm=False)
        if not outcome.healed:
            q = persist_quarantine_row(db, run.id, row_result, outcome)
            quarantined_ids.append(q.id)

    error_type_counts = Counter(q.error_type for q in list_quarantine_rows(db, run_id=run.id))
    print(f"\nPersisted {len(quarantined_ids)} quarantine rows for run {run.id}: {dict(error_type_counts)}\n")

    send_quarantine_alert(
        AlertPayload(run_id=run.id, quarantined_count=len(quarantined_ids), error_types=dict(error_type_counts))
    )

    print(f"\nUnresolved before: {len(list_quarantine_rows(db, run_id=run.id, resolved=False))}")
    resolve_quarantine_row(db, quarantined_ids[0])
    print(f"Unresolved after resolving row {quarantined_ids[0]}: {len(list_quarantine_rows(db, run_id=run.id, resolved=False))}")


if __name__ == "__main__":
    main()
