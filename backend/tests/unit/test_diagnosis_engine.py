import app.core.pipeline.diagnosis.engine as engine_module
from app.core.pipeline.diagnosis.base import TransformID
from app.core.pipeline.diagnosis.engine import diagnose
from app.core.pipeline.diagnosis.llm_diagnoser import LLMDiagnosisError
from app.core.pipeline.validation import RowValidationResult


def _row_result() -> RowValidationResult:
    row = {
        "order_id": "ORD-000001",
        "customer_id": "CUST-0001",
        "order_date": "2026-01-01",
        "amount": "$49.99",
        "currency": "USD",
        "status": "pending",
    }
    return RowValidationResult(
        row_index=0,
        raw_row=row,
        valid=False,
        error_type="invalid_amount",
        errors=[{"loc": ("amount",), "msg": "bad", "type": "value_error"}],
    )


def test_uses_heuristic_directly_when_llm_disabled():
    diagnosis = diagnose(_row_result(), use_llm=False)
    assert diagnosis.source == "heuristic"
    assert diagnosis.transform == TransformID.COERCE_AMOUNT


def test_falls_back_to_heuristic_when_llm_raises(monkeypatch):
    def _boom(result):
        raise LLMDiagnosisError("simulated failure")

    monkeypatch.setattr(engine_module, "diagnose_llm", _boom)
    diagnosis = diagnose(_row_result(), use_llm=True)
    assert diagnosis.source == "heuristic"
    assert diagnosis.transform == TransformID.COERCE_AMOUNT


def test_uses_llm_result_when_it_succeeds(monkeypatch):
    from app.core.pipeline.diagnosis.base import Diagnosis

    def _fake_llm(result):
        return Diagnosis(
            hypothesis="llm hypothesis",
            transform=TransformID.COERCE_AMOUNT,
            confidence=0.99,
            reasoning="llm reasoning",
            source="llm",
        )

    monkeypatch.setattr(engine_module, "diagnose_llm", _fake_llm)
    diagnosis = diagnose(_row_result(), use_llm=True)
    assert diagnosis.source == "llm"
