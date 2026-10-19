import asyncio
import logging
import time

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.alerting import AlertPayload, send_quarantine_alert
from app.core.pipeline.diagnosis.base import Diagnosis
from app.core.pipeline.duplicates import is_exact_duplicate, load_stored_orders
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

# Label recorded in fixes_applied and the audit trail when a row turns out to be
# an exact resubmission. Deliberately not a TransformID: it repairs nothing, so
# it must never be something the LLM or heuristic can propose for a row.
DEDUPLICATE_LABEL = "deduplicate"


def _persist_audit_entry(db: AsyncSession, run_id: int, row_identifier: str, diagnosis: Diagnosis, outcome: str) -> None:
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


async def _split_exact_duplicates(db: AsyncSession, batch_result):
    """Separates rows that are plain resubmissions of an order already stored
    (every field identical) from everything else that failed validation. A
    duplicate order_id with differing content stays in the normal path, where it
    is quarantined for a human to decide which version is right."""
    duplicates = [r for r in batch_result.invalid_rows if r.error_type == "duplicate_order_id"]
    if not duplicates:
        return [], batch_result.invalid_rows

    stored = await load_stored_orders(db, {r.order.order_id for r in duplicates})
    in_batch = {r.order.order_id: r.order for r in batch_result.valid_rows}

    exact, remaining = [], []
    for result in batch_result.invalid_rows:
        if result.error_type == "duplicate_order_id":
            order_id = result.order.order_id
            candidates = [c for c in (in_batch.get(order_id), stored.get(order_id)) if c is not None]
            if any(is_exact_duplicate(result.order, c) for c in candidates):
                exact.append(result)
                continue
        remaining.append(result)
    return exact, remaining


async def _diagnose_and_repair(
    invalid_result, known_ids: set[str], use_llm: bool | None, semaphore: asyncio.Semaphore
):
    async with semaphore:
        started = time.perf_counter()
        outcome = await repair_row(
            invalid_result, known_ids, max_attempts=settings.max_repair_attempts, use_llm=use_llm
        )
        elapsed_ms = (time.perf_counter() - started) * 1000
        return outcome, elapsed_ms


async def run_pipeline(db: AsyncSession, source: CsvSource, use_llm: bool | None = None) -> Run:
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
    await db.commit()
    await db.refresh(run)

    try:
        rows = read_csv_rows(source)
    except Exception:
        run.status = "failed"
        run.finished_at = utcnow()
        await db.commit()
        raise

    run.row_count = len(rows)

    if len(rows) > settings.max_upload_rows:
        run.status = "failed"
        run.finished_at = utcnow()
        await db.commit()
        await db.refresh(run)
        raise ValueError(f"Batch has {len(rows)} rows, exceeding the {settings.max_upload_rows}-row upload cap")

    known_ids = await load_known_customer_ids(db)
    existing_order_ids = await load_existing_order_ids(db)

    try:
        batch_result = validate_batch(rows, known_ids, existing_order_ids)
    except SchemaDriftError as exc:
        run.status = "rejected_schema_drift"
        run.finished_at = utcnow()
        run.error_types = {"schema_drift": len(exc.unexpected_columns)}
        await db.commit()
        await db.refresh(run)
        logger.error("Run %s rejected: schema drift in columns %s", run.id, sorted(exc.unexpected_columns))
        return run

    exact_duplicates, rows_to_repair = await _split_exact_duplicates(db, batch_result)

    quarantined_count = 0
    error_type_counts: dict[str, int] = {}

    try:
        for valid_result in batch_result.valid_rows:
            db.add(Order(run_id=run.id, **valid_result.order.model_dump()))

        fixes_applied_counts: dict[str, int] = {}
        heal_times_ms: list[float] = []
        healed_count = 0

        # Diagnosis (the LLM call in particular) is the slow, I/O-bound step.
        # Run it concurrently across every invalid row instead of one at a
        # time. A semaphore caps how many requests are in flight together so
        # a large batch doesn't slam the LLM provider's rate limits. The
        # database session isn't touched inside repair_row, so it's safe to
        # run these concurrently and only write results back sequentially.
        semaphore = asyncio.Semaphore(settings.max_concurrent_diagnoses)
        repair_results = await asyncio.gather(
            *[
                _diagnose_and_repair(invalid_result, known_ids, use_llm, semaphore)
                for invalid_result in rows_to_repair
            ]
        )

        for invalid_result, (outcome, elapsed_ms) in zip(rows_to_repair, repair_results):
            error_type_counts[invalid_result.error_type] = error_type_counts.get(invalid_result.error_type, 0) + 1
            row_identifier = invalid_result.raw_row.get("order_id") or f"row-{invalid_result.row_index}"

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
                await persist_quarantine_row(db, run.id, invalid_result, outcome)

        for duplicate in exact_duplicates:
            error_type_counts[duplicate.error_type] = error_type_counts.get(duplicate.error_type, 0) + 1
            healed_count += 1
            fixes_applied_counts[DEDUPLICATE_LABEL] = fixes_applied_counts.get(DEDUPLICATE_LABEL, 0) + 1
            db.add(
                AuditEntry(
                    run_id=run.id,
                    row_identifier=duplicate.order.order_id,
                    hypothesis="order_id already exists with identical content",
                    transform_chosen=DEDUPLICATE_LABEL,
                    confidence=1.0,
                    reasoning="Exact resubmission of an order already in the clean data store; nothing new to insert.",
                    diagnosis_source="heuristic",
                    outcome="healed",
                )
            )

        run.clean_first_pass = len(batch_result.valid_rows)
        run.healed = healed_count
        run.quarantined = quarantined_count
        run.error_types = error_type_counts
        run.fixes_applied = fixes_applied_counts
        run.avg_time_to_heal_ms = sum(heal_times_ms) / len(heal_times_ms) if heal_times_ms else None
        run.status = "completed"
        run.finished_at = utcnow()
        await db.commit()
        await db.refresh(run)
    except Exception:
        # Whatever rows were already staged get committed along with the
        # failed status -- better to keep partial progress than lose it, and
        # the run is never left stuck at "running" with no error recorded.
        run.status = "failed"
        run.finished_at = utcnow()
        await db.commit()
        raise

    if quarantined_count > 0:
        send_quarantine_alert(
            AlertPayload(run_id=run.id, quarantined_count=quarantined_count, error_types=error_type_counts)
        )

    return run
