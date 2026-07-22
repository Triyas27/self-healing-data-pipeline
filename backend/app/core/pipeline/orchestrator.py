import logging
import time

from sqlalchemy.orm import Session

from app.config import settings
from app.core.alerting import AlertPayload, send_quarantine_alert
from app.core.pipeline.diagnosis.base import Diagnosis
from app.core.pipeline.ingestion import CsvSource, read_csv_rows
from app.core.pipeline.quarantine import persist_quarantine_row
from app.core.pipeline.repair.repair import repair_row
from app.core.pipeline.validation import (
    SchemaDriftError,
    load_existing_order_ids,
    load_known_customer_ids,
    validate_batch,
)
from app.db.base import utcnow
from app.models import AuditEntry, Order, Run

logger = logging.getLogger(__name__)


def _persist_audit_entry(db: Session, run_id: int, row_identifier: str, diagnosis: Diagnosis, outcome: str) -> None:
    db.add(
        AuditEntry(
            run_id=run_id,
            row_identifier=row_identifier,
            hypothesis=diagnosis.hypothesis,
            transform_chosen=diagnosis.transform.value if diagnosis.transform else None,
            confidence=diagnosis.confidence,
            reasoning=diagnosis.reasoning,
            diagnosis_source=diagnosis.source,
            outcome=outcome,
        )
    )


def run_pipeline(db: Session, source: CsvSource, use_llm: bool | None = None) -> Run:
    """Wires ingestion -> validation -> diagnosis -> repair -> re-validation ->
    quarantine into a single tracked run. Records one Run log entry with
    row/heal/quarantine counts, error types, fixes applied, average
    time-to-heal, and overall status, plus a per-attempt AuditEntry
    (hypothesis, transform, confidence, reasoning, source) for every repair
    decision. Every ingested row ends up in either the clean store (Order) or
    the quarantine store (QuarantineRow) -- schema-drift rejection is the sole
    exception, since the whole batch is refused before any row is processed.
    """
    run = Run(row_count=0, status="running")
    db.add(run)
    db.commit()
    db.refresh(run)

    try:
        rows = read_csv_rows(source)
    except Exception:
        run.status = "failed"
        run.finished_at = utcnow()
        db.commit()
        raise

    run.row_count = len(rows)

    if len(rows) > settings.max_upload_rows:
        run.status = "failed"
        run.finished_at = utcnow()
        db.commit()
        db.refresh(run)
        raise ValueError(f"Batch has {len(rows)} rows, exceeding the {settings.max_upload_rows}-row upload cap")

    known_ids = load_known_customer_ids(db)
    existing_order_ids = load_existing_order_ids(db)

    try:
        batch_result = validate_batch(rows, known_ids, existing_order_ids)
    except SchemaDriftError as exc:
        run.status = "rejected_schema_drift"
        run.finished_at = utcnow()
        run.error_types = {"schema_drift": len(exc.unexpected_columns)}
        db.commit()
        db.refresh(run)
        logger.error("Run %s rejected: schema drift in columns %s", run.id, sorted(exc.unexpected_columns))
        return run

    quarantined_count = 0
    error_type_counts: dict[str, int] = {}

    try:
        for valid_result in batch_result.valid_rows:
            db.add(Order(run_id=run.id, **valid_result.order.model_dump()))

        fixes_applied_counts: dict[str, int] = {}
        heal_times_ms: list[float] = []
        healed_count = 0

        for invalid_result in batch_result.invalid_rows:
            error_type_counts[invalid_result.error_type] = error_type_counts.get(invalid_result.error_type, 0) + 1
            row_identifier = invalid_result.raw_row.get("order_id") or f"row-{invalid_result.row_index}"

            started = time.perf_counter()
            outcome = repair_row(
                invalid_result, known_ids, max_attempts=settings.max_repair_attempts, use_llm=use_llm
            )
            elapsed_ms = (time.perf_counter() - started) * 1000

            for i, attempt in enumerate(outcome.attempts):
                is_last = i == len(outcome.attempts) - 1
                if outcome.healed and is_last:
                    label = "healed"
                elif not attempt.diagnosis.has_fix:
                    label = "no_fix"
                else:
                    label = "still_invalid"
                _persist_audit_entry(db, run.id, row_identifier, attempt.diagnosis, label)
                if attempt.diagnosis.has_fix:
                    key = attempt.diagnosis.transform.value
                    fixes_applied_counts[key] = fixes_applied_counts.get(key, 0) + 1

            if outcome.healed:
                healed_count += 1
                heal_times_ms.append(elapsed_ms)
                db.add(Order(run_id=run.id, **outcome.order.model_dump()))
            else:
                quarantined_count += 1
                persist_quarantine_row(db, run.id, invalid_result, outcome)

        run.clean_first_pass = len(batch_result.valid_rows)
        run.healed = healed_count
        run.quarantined = quarantined_count
        run.error_types = error_type_counts
        run.fixes_applied = fixes_applied_counts
        run.avg_time_to_heal_ms = sum(heal_times_ms) / len(heal_times_ms) if heal_times_ms else None
        run.status = "completed"
        run.finished_at = utcnow()
        db.commit()
        db.refresh(run)
    except Exception:
        # Whatever rows were already processed get committed along with the
        # failed status -- better to keep partial progress than lose it, and
        # the run is never left stuck at "running" with no error recorded.
        run.status = "failed"
        run.finished_at = utcnow()
        db.commit()
        raise

    if quarantined_count > 0:
        send_quarantine_alert(
            AlertPayload(run_id=run.id, quarantined_count=quarantined_count, error_types=error_type_counts)
        )

    return run
