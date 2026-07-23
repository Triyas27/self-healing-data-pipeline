import app.core.pipeline.repair.repair as repair_module
from app.core.pipeline.diagnosis.base import Diagnosis, TransformID
from app.core.pipeline.repair.repair import repair_row
from app.core.pipeline.validation import RowValidationResult, validate_batch
from app.synthetic.generator import FailureMode, generate_batch, known_customer_ids


def _failing_result(mode: FailureMode, seed: int = 1) -> RowValidationResult:
    row = generate_batch(row_count=1, failure_rate=1.0, failure_mode=mode, seed=seed).rows[0]
    result = validate_batch([row], set(known_customer_ids())).results[0]
    assert not result.valid
    return result


async def test_healed_when_amount_has_currency_noise():
    row = {
        "order_id": "ORD-000001",
        "customer_id": "CUST-0001",
        "order_date": "2026-01-01",
        "amount": "$49.99",
        "currency": "USD",
        "status": "pending",
    }
    result = validate_batch([row], set(known_customer_ids())).results[0]
    outcome = await repair_row(result, set(known_customer_ids()), max_attempts=3, use_llm=False)
    assert outcome.healed is True
    assert outcome.final_row["amount"] == "49.99"
    assert len(outcome.attempts) == 1


async def test_quarantined_not_rounded_when_amount_has_excess_decimal_places():
    row = {
        "order_id": "ORD-000001",
        "customer_id": "CUST-0001",
        "order_date": "2026-01-01",
        "amount": "49.123",
        "currency": "USD",
        "status": "pending",
    }
    result = validate_batch([row], set(known_customer_ids())).results[0]
    assert not result.valid
    assert result.error_type == "invalid_amount"

    outcome = await repair_row(result, set(known_customer_ids()), max_attempts=3, use_llm=False)
    assert outcome.healed is False
    assert outcome.quarantine_reason == "no_fix"


async def test_healed_for_date_format_swap():
    result = _failing_result(FailureMode.DATE_FORMAT_SWAP)
    outcome = await repair_row(result, set(known_customer_ids()), max_attempts=3, use_llm=False)
    assert outcome.healed is True
    assert outcome.order is not None


async def test_healed_for_encoding_issue():
    result = _failing_result(FailureMode.ENCODING_ISSUE)
    outcome = await repair_row(result, set(known_customer_ids()), max_attempts=3, use_llm=False)
    assert outcome.healed is True


async def test_quarantined_no_fix_for_invalid_foreign_key():
    result = _failing_result(FailureMode.INVALID_FOREIGN_KEY)
    outcome = await repair_row(result, set(known_customer_ids()), max_attempts=3, use_llm=False)
    assert outcome.healed is False
    assert outcome.quarantine_reason == "no_fix"
    assert len(outcome.attempts) == 1


async def test_quarantined_no_fix_for_null_required_field():
    result = _failing_result(FailureMode.NULL_REQUIRED_FIELD)
    outcome = await repair_row(result, set(known_customer_ids()), max_attempts=3, use_llm=False)
    assert outcome.healed is False
    assert outcome.quarantine_reason == "no_fix"


async def test_attempts_exhausted_routes_to_quarantine(monkeypatch):
    call_count = {"n": 0}

    async def fake_diagnose(result, use_llm=None):
        call_count["n"] += 1
        return Diagnosis(
            hypothesis="h", transform=TransformID.COERCE_AMOUNT, confidence=0.5, reasoning="r", source="heuristic"
        )

    def fake_apply_transform(transform_id, row, field):
        new_row = dict(row)
        new_row[field] = row[field] + "!"
        return new_row

    def fake_validate_row(index, row, known_ids):
        return RowValidationResult(
            row_index=index,
            raw_row=row,
            valid=False,
            error_type="invalid_amount",
            errors=[{"loc": ("amount",), "msg": "still bad", "type": "value_error"}],
        )

    monkeypatch.setattr(repair_module, "diagnose", fake_diagnose)
    monkeypatch.setattr(repair_module, "apply_transform", fake_apply_transform)
    monkeypatch.setattr(repair_module, "validate_row", fake_validate_row)

    initial = RowValidationResult(
        row_index=0,
        raw_row={"amount": "bad"},
        valid=False,
        error_type="invalid_amount",
        errors=[{"loc": ("amount",), "msg": "bad", "type": "value_error"}],
    )

    outcome = await repair_row(initial, known_customer_ids=set(), max_attempts=3)
    assert outcome.healed is False
    assert outcome.quarantine_reason == "attempts_exhausted"
    assert len(outcome.attempts) == 3
    assert call_count["n"] == 3
