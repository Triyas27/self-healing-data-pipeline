from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.pipeline.quarantine import list_quarantine_rows, persist_quarantine_row, resolve_quarantine_row
from app.core.pipeline.repair.repair import repair_row
from app.core.pipeline.validation import validate_batch
from app.db.base import Base
from app.models import Run
from app.synthetic.generator import FailureMode, generate_batch, known_customer_ids


def _make_db() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def _new_run(db: Session, row_count: int = 1):
    run = Run(row_count=row_count)
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def test_persist_quarantine_row_captures_full_history():
    db = _make_db()
    run = _new_run(db)

    row = generate_batch(
        row_count=1, failure_rate=1.0, failure_mode=FailureMode.INVALID_FOREIGN_KEY, seed=1
    ).rows[0]
    result = validate_batch([row], set(known_customer_ids())).results[0]
    outcome = repair_row(result, set(known_customer_ids()), max_attempts=3, use_llm=False)
    assert outcome.healed is False

    q = persist_quarantine_row(db, run.id, result, outcome)

    assert q.id is not None
    assert q.original_data == row
    assert q.error_type == "invalid_foreign_key"
    assert q.attempt_count == 1
    assert len(q.diagnosis_history) == 1
    assert q.diagnosis_history[0]["transform"] is None
    assert q.resolved is False


def test_resolve_quarantine_row_marks_resolved():
    db = _make_db()
    run = _new_run(db)

    row = generate_batch(
        row_count=1, failure_rate=1.0, failure_mode=FailureMode.NULL_REQUIRED_FIELD, seed=1
    ).rows[0]
    result = validate_batch([row], set()).results[0]
    outcome = repair_row(result, set(), max_attempts=3, use_llm=False)
    q = persist_quarantine_row(db, run.id, result, outcome)

    assert q.resolved is False
    resolved = resolve_quarantine_row(db, q.id)
    assert resolved.resolved is True

    rows = list_quarantine_rows(db, run_id=run.id, resolved=True)
    assert len(rows) == 1


def test_resolve_missing_row_returns_none():
    db = _make_db()
    assert resolve_quarantine_row(db, 9999) is None


def test_list_quarantine_rows_filters_by_run_and_resolved_status():
    db = _make_db()
    run = _new_run(db, row_count=2)

    for i, mode in enumerate([FailureMode.NULL_REQUIRED_FIELD, FailureMode.INVALID_FOREIGN_KEY]):
        row = generate_batch(row_count=1, failure_rate=1.0, failure_mode=mode, seed=i).rows[0]
        result = validate_batch([row], set()).results[0]
        outcome = repair_row(result, set(), max_attempts=3, use_llm=False)
        persist_quarantine_row(db, run.id, result, outcome)

    all_rows = list_quarantine_rows(db, run_id=run.id)
    assert len(all_rows) == 2

    unresolved = list_quarantine_rows(db, run_id=run.id, resolved=False)
    assert len(unresolved) == 2

    resolve_quarantine_row(db, all_rows[0].id)
    resolved_rows = list_quarantine_rows(db, run_id=run.id, resolved=True)
    assert len(resolved_rows) == 1
