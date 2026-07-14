from sqlalchemy.orm import Session

from app.core.pipeline.repair.repair import RepairOutcome
from app.core.pipeline.validation import RowValidationResult
from app.models import QuarantineRow


def format_error_detail(result: RowValidationResult) -> str:
    if not result.errors:
        return "unknown error"
    return "; ".join(f"{'.'.join(str(p) for p in e['loc'])}: {e['msg']}" for e in result.errors)


def _diagnosis_history(outcome: RepairOutcome) -> list[dict]:
    history = []
    for attempt in outcome.attempts:
        history.append(
            {
                "hypothesis": attempt.diagnosis.hypothesis,
                "transform": attempt.diagnosis.transform.value if attempt.diagnosis.transform else None,
                "confidence": attempt.diagnosis.confidence,
                "reasoning": attempt.diagnosis.reasoning,
                "source": attempt.diagnosis.source,
                "row_after": attempt.row_after,
            }
        )
    return history


def persist_quarantine_row(
    db: Session, run_id: int, result: RowValidationResult, outcome: RepairOutcome
) -> QuarantineRow:
    """Persists original data, error type/detail, attempt count, and the full
    diagnosis history for a row that repair could not heal."""
    quarantine_row = QuarantineRow(
        run_id=run_id,
        original_data=result.raw_row,
        error_type=result.error_type or "unknown",
        error_detail=format_error_detail(result),
        attempt_count=len(outcome.attempts),
        diagnosis_history=_diagnosis_history(outcome),
        resolved=False,
    )
    db.add(quarantine_row)
    db.commit()
    db.refresh(quarantine_row)
    return quarantine_row


def resolve_quarantine_row(db: Session, quarantine_row_id: int) -> QuarantineRow | None:
    """Lets a human operator mark a quarantined row as resolved."""
    quarantine_row = db.get(QuarantineRow, quarantine_row_id)
    if quarantine_row is None:
        return None
    quarantine_row.resolved = True
    db.commit()
    db.refresh(quarantine_row)
    return quarantine_row


def list_quarantine_rows(
    db: Session, run_id: int | None = None, resolved: bool | None = None
) -> list[QuarantineRow]:
    query = db.query(QuarantineRow)
    if run_id is not None:
        query = query.filter(QuarantineRow.run_id == run_id)
    if resolved is not None:
        query = query.filter(QuarantineRow.resolved == resolved)
    return query.order_by(QuarantineRow.created_at.desc()).all()
