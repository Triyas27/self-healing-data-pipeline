import json
from types import SimpleNamespace

import pytest

from app.core.pipeline.diagnosis.base import TransformID
from app.core.pipeline.diagnosis.llm_diagnoser import LLMDiagnosisError, diagnose_llm
from app.core.pipeline.validation import RowValidationResult


class FakeGroqClient:
    def __init__(self, content: str):
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))
        self._content = content

    async def _create(self, **kwargs):
        message = SimpleNamespace(content=self._content)
        choice = SimpleNamespace(message=message)
        return SimpleNamespace(choices=[choice])


class BrokenGroqClient:
    @staticmethod
    async def _raise(**kwargs):
        raise RuntimeError("network down")

    chat = SimpleNamespace(completions=SimpleNamespace(create=_raise))


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


async def test_valid_llm_response_parses_to_diagnosis():
    payload = json.dumps(
        {
            "hypothesis": "amount has a currency symbol",
            "transform": "coerce_amount",
            "confidence": 0.9,
            "reasoning": "stripping $ yields 49.99",
        }
    )
    diagnosis = await diagnose_llm(_row_result(), client=FakeGroqClient(payload))
    assert diagnosis.transform == TransformID.COERCE_AMOUNT
    assert diagnosis.source == "llm"


async def test_no_fix_response_maps_to_none_transform():
    payload = json.dumps(
        {
            "hypothesis": "unclear",
            "transform": "no_fix",
            "confidence": 0.6,
            "reasoning": "cannot safely repair",
        }
    )
    diagnosis = await diagnose_llm(_row_result(), client=FakeGroqClient(payload))
    assert diagnosis.transform is None


async def test_unknown_transform_is_rejected_structurally():
    payload = json.dumps(
        {
            "hypothesis": "x",
            "transform": "delete_row",
            "confidence": 0.9,
            "reasoning": "y",
        }
    )
    with pytest.raises(LLMDiagnosisError):
        await diagnose_llm(_row_result(), client=FakeGroqClient(payload))


async def test_malformed_json_raises_llm_diagnosis_error():
    with pytest.raises(LLMDiagnosisError):
        await diagnose_llm(_row_result(), client=FakeGroqClient("not json at all"))


async def test_out_of_range_confidence_rejected():
    payload = json.dumps(
        {"hypothesis": "x", "transform": "no_fix", "confidence": 1.5, "reasoning": "y"}
    )
    with pytest.raises(LLMDiagnosisError):
        await diagnose_llm(_row_result(), client=FakeGroqClient(payload))


async def test_client_exception_raises_llm_diagnosis_error():
    with pytest.raises(LLMDiagnosisError):
        await diagnose_llm(_row_result(), client=BrokenGroqClient())
