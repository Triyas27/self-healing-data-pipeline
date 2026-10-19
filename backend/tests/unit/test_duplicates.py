from app.core.pipeline.duplicates import is_exact_duplicate
from app.schemas.order import OrderIn

BASE = {
    "order_id": "ORD-000001",
    "customer_id": "CUST-0001",
    "order_date": "2026-01-01",
    "amount": "49.99",
    "currency": "USD",
    "status": "pending",
}


def _order(**overrides) -> OrderIn:
    return OrderIn.model_validate({**BASE, **overrides})


def test_identical_orders_are_exact_duplicates():
    assert is_exact_duplicate(_order(), _order())


def test_equivalent_amount_formatting_still_matches():
    assert is_exact_duplicate(_order(amount="49.99"), _order(amount="49.990"))


def test_any_differing_field_is_not_an_exact_duplicate():
    for field, value in [
        ("customer_id", "CUST-0002"),
        ("order_date", "2026-01-02"),
        ("amount", "50.00"),
        ("currency", "EUR"),
        ("status", "shipped"),
    ]:
        assert not is_exact_duplicate(_order(), _order(**{field: value})), field
