import io

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

import app.core.pipeline.orchestrator as orchestrator_module
from app.config import settings
from app.core.pipeline.orchestrator import run_pipeline
from app.db.base import Base
from app.models import AuditEntry, CustomerReference, Order, QuarantineRow, Run
from app.synthetic.generator import FailureMode, generate_batch, known_customer_ids, to_csv_string


def _make_db() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = Session(engine)
    for cid in known_customer_ids():
        db.add(CustomerReference(customer_id=cid))
    db.commit()
    return db


def _make_failing_row(mode: FailureMode, index: int, seed: int) -> dict:
    # generate_batch(row_count=1, ...) always starts its internal index at 1, so
    # every single-row batch defaults to order_id="ORD-000001". Reassign a unique
    # id per row, except where the corruption under test lives in order_id itself
    # (encoding_issue) or the field is blank (null_required_field may have picked
    # order_id) -- reassigning would silently undo the failure being tested.
    row = generate_batch(row_count=1, failure_rate=1.0, failure_mode=mode, seed=seed).rows[0]
    unique_id = f"ORD-{900000 + index:06d}"
    if mode == FailureMode.ENCODING_ISSUE:
        row["order_id"] = row["order_id"].replace("ORD-000001", unique_id, 1)
    elif row.get("order_id") == "ORD-000001":
        row["order_id"] = unique_id
    return row


def test_full_run_every_row_lands_in_clean_or_quarantine_store():
    db = _make_db()

    clean_rows = generate_batch(row_count=6, failure_rate=0.0, seed=1).rows
    failing_rows = [
        _make_failing_row(mode, i, seed=100 + i)
        for i, mode in enumerate(m for m in FailureMode if m != FailureMode.SCHEMA_DRIFT)
    ]
    csv_text = to_csv_string(clean_rows + failing_rows)

    run = run_pipeline(db, io.StringIO(csv_text), use_llm=False)

    assert run.status == "completed"
    assert run.row_count == len(clean_rows) + len(failing_rows)
    # every ingested row ends up in the clean store or the quarantine store
    assert run.clean_first_pass + run.healed + run.quarantined == run.row_count

    order_count = db.query(Order).filter(Order.run_id == run.id).count()
    quarantine_count = db.query(QuarantineRow).filter(QuarantineRow.run_id == run.id).count()
    assert order_count == run.clean_first_pass + run.healed
    assert quarantine_count == run.quarantined
    assert order_count + quarantine_count == run.row_count

    # every repair decision should be recorded
    audit_count = db.query(AuditEntry).filter(AuditEntry.run_id == run.id).count()
    assert audit_count >= len(failing_rows)

    assert run.healed > 0
    assert run.quarantined > 0
    assert run.avg_time_to_heal_ms is not None
    assert run.fixes_applied


def test_schema_drift_rejects_whole_batch_without_raising():
    db = _make_db()
    drift_rows = generate_batch(
        row_count=5, failure_rate=1.0, failure_mode=FailureMode.SCHEMA_DRIFT, seed=1
    ).rows
    csv_text = to_csv_string(drift_rows)

    run = run_pipeline(db, io.StringIO(csv_text), use_llm=False)

    assert run.status == "rejected_schema_drift"
    assert db.query(Order).filter(Order.run_id == run.id).count() == 0
    assert db.query(QuarantineRow).filter(QuarantineRow.run_id == run.id).count() == 0


def test_ingestion_failure_marks_run_failed_and_reraises():
    db = _make_db()
    with pytest.raises(FileNotFoundError):
        run_pipeline(db, "does-not-exist.csv", use_llm=False)

    failed_run = db.query(Run).order_by(Run.id.desc()).first()
    assert failed_run.status == "failed"


def test_all_clean_batch_has_zero_healed_and_quarantined():
    db = _make_db()
    clean_rows = generate_batch(row_count=10, failure_rate=0.0, seed=2).rows
    csv_text = to_csv_string(clean_rows)

    run = run_pipeline(db, io.StringIO(csv_text), use_llm=False)

    assert run.status == "completed"
    assert run.clean_first_pass == 10
    assert run.healed == 0
    assert run.quarantined == 0
    assert run.avg_time_to_heal_ms is None


def test_reuploading_the_same_batch_quarantines_the_duplicates():
    db = _make_db()
    clean_rows = generate_batch(row_count=5, failure_rate=0.0, seed=3).rows
    csv_text = to_csv_string(clean_rows)

    first_run = run_pipeline(db, io.StringIO(csv_text), use_llm=False)
    assert first_run.clean_first_pass == 5

    second_run = run_pipeline(db, io.StringIO(csv_text), use_llm=False)
    assert second_run.status == "completed"
    assert second_run.clean_first_pass == 0
    assert second_run.quarantined == 5
    assert second_run.error_types == {"duplicate_order_id": 5}


def test_row_count_over_cap_marks_run_failed(monkeypatch):
    db = _make_db()
    monkeypatch.setattr(settings, "max_upload_rows", 3)
    rows = generate_batch(row_count=5, failure_rate=0.0, seed=1).rows
    csv_text = to_csv_string(rows)

    with pytest.raises(ValueError, match="exceeding"):
        run_pipeline(db, io.StringIO(csv_text), use_llm=False)

    failed_run = db.query(Run).order_by(Run.id.desc()).first()
    assert failed_run.status == "failed"
    assert failed_run.row_count == 5


def test_unexpected_exception_during_repair_marks_run_failed_not_stuck(monkeypatch):
    db = _make_db()
    rows = generate_batch(
        row_count=3, failure_rate=1.0, failure_mode=FailureMode.INVALID_FOREIGN_KEY, seed=1
    ).rows
    csv_text = to_csv_string(rows)

    def _boom(*args, **kwargs):
        raise RuntimeError("simulated crash mid-repair")

    monkeypatch.setattr(orchestrator_module, "repair_row", _boom)

    with pytest.raises(RuntimeError, match="simulated crash"):
        run_pipeline(db, io.StringIO(csv_text), use_llm=False)

    crashed_run = db.query(Run).order_by(Run.id.desc()).first()
    assert crashed_run.status == "failed"
    assert crashed_run.finished_at is not None
