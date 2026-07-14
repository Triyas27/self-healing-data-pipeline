import pytest

from app.core.pipeline.diagnosis.base import TransformID
from app.core.pipeline.diagnosis.heuristic_diagnoser import diagnose_heuristic
from app.core.pipeline.validation import RowValidationResult

BASE_ROW = {
    "order_id": "ORD-000001",
    "customer_id": "CUST-0001",
    "order_date": "2026-01-01",
    "amount": "49.99",
    "currency": "USD",
    "status": "pending",
}


def _invalid_result(overrides: dict, field: str, error_type: str | None = None) -> RowValidationResult:
    row = {**BASE_ROW, **overrides}
    return RowValidationResult(
        row_index=0,
        raw_row=row,
        valid=False,
        errors=[{"loc": (field,), "msg": "invalid", "type": "value_error"}],
        error_type=error_type or f"invalid_{field}",
    )


def test_coerce_amount_when_currency_noise_present():
    result = _invalid_result({"amount": "$49.99"}, "amount")
    diagnosis = diagnose_heuristic(result)
    assert diagnosis.transform == TransformID.COERCE_AMOUNT
    assert diagnosis.source == "heuristic"


def test_no_fix_when_amount_unparseable():
    result = _invalid_result({"amount": "fifty-two"}, "amount")
    diagnosis = diagnose_heuristic(result)
    assert diagnosis.transform is None


def test_reformat_date_for_dd_mm_yyyy():
    result = _invalid_result({"order_date": "01/07/2026"}, "order_date")
    diagnosis = diagnose_heuristic(result)
    assert diagnosis.transform == TransformID.REFORMAT_DATE


def test_no_fix_for_garbage_date():
    result = _invalid_result({"order_date": "not-a-date"}, "order_date")
    diagnosis = diagnose_heuristic(result)
    assert diagnosis.transform is None


def test_fix_encoding_for_mojibake_order_id():
    mojibake = "áéíóú".encode("utf-8").decode("latin-1")
    result = _invalid_result({"order_id": f"ORD-000001{mojibake}"}, "order_id")
    diagnosis = diagnose_heuristic(result)
    assert diagnosis.transform == TransformID.FIX_ENCODING


def test_no_fix_for_blank_required_field():
    result = _invalid_result({"order_id": ""}, "order_id")
    diagnosis = diagnose_heuristic(result)
    assert diagnosis.transform is None


def test_no_fix_for_unresolvable_foreign_key():
    result = _invalid_result({"customer_id": "CUST-9999"}, "customer_id", error_type="invalid_foreign_key")
    diagnosis = diagnose_heuristic(result)
    assert diagnosis.transform is None


def test_raises_for_already_valid_row():
    result = RowValidationResult(row_index=0, raw_row={}, valid=True)
    with pytest.raises(ValueError):
        diagnose_heuristic(result)
