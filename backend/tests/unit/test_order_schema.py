from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas.order import OrderIn

BASE_ROW = {
    "order_id": "ORD-000123",
    "customer_id": "CUST-1001",
    "order_date": "2026-07-01",
    "amount": "49.99",
    "currency": "USD",
    "status": "pending",
}


def test_valid_row_passes():
    order = OrderIn.model_validate(BASE_ROW)
    assert order.amount == Decimal("49.99")


@pytest.mark.parametrize(
    "field,value",
    [
        ("order_id", "12345"),
        ("customer_id", "1001"),
        ("order_date", "not-a-date"),
        ("amount", "-5.00"),
        ("amount", "0"),
        ("amount", "49.123"),
        ("currency", "ZZZ"),
        ("status", "unknown"),
    ],
)
def test_invalid_row_rejected(field, value):
    row = {**BASE_ROW, field: value}
    with pytest.raises(ValidationError):
        OrderIn.model_validate(row)


def test_amount_rejects_more_than_two_decimal_places():
    row = {**BASE_ROW, "amount": "49.123"}
    with pytest.raises(ValidationError) as exc_info:
        OrderIn.model_validate(row)
    errors = exc_info.value.errors()
    assert errors[0]["type"] == "decimal_max_places"
    assert errors[0]["loc"] == ("amount",)
