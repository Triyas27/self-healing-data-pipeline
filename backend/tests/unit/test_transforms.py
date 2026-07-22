from app.core.pipeline.repair.transforms import coerce_amount, fix_encoding, reformat_date

VALID_ROW = {
    "order_id": "ORD-000001",
    "customer_id": "CUST-0001",
    "order_date": "2026-01-01",
    "amount": "49.99",
    "currency": "USD",
    "status": "pending",
}


def test_coerce_amount_strips_currency_noise():
    row = {**VALID_ROW, "amount": "$49.99"}
    repaired = coerce_amount(row, "amount")
    assert repaired is not None
    assert repaired["amount"] == "49.99"


def test_coerce_amount_declines_unparseable_noise():
    row = {**VALID_ROW, "amount": "fifty-two"}
    assert coerce_amount(row, "amount") is None


def test_coerce_amount_is_non_destructive_on_already_clean_value():
    # a transform must never alter data that already passes validation
    assert coerce_amount(VALID_ROW, "amount") is None


def test_coerce_amount_declines_accounting_negative_notation():
    # "(49.99)" means -49.99 in accounting notation. Stripping the parens as
    # noise would silently flip the sign, which is fabrication, not a fix.
    row = {**VALID_ROW, "amount": "(49.99)"}
    assert coerce_amount(row, "amount") is None


def test_reformat_date_converts_dd_mm_yyyy_to_iso():
    row = {**VALID_ROW, "order_date": "01/07/2026"}
    repaired = reformat_date(row, "order_date")
    assert repaired is not None
    assert repaired["order_date"] == "2026-07-01"


def test_reformat_date_declines_garbage():
    row = {**VALID_ROW, "order_date": "not-a-date"}
    assert reformat_date(row, "order_date") is None


def test_reformat_date_is_non_destructive_on_already_iso_value():
    assert reformat_date(VALID_ROW, "order_date") is None


def test_fix_encoding_strips_mojibake_suffix():
    mojibake = "áéíóú".encode("utf-8").decode("latin-1")
    row = {**VALID_ROW, "order_id": f"ORD-000001{mojibake}"}
    repaired = fix_encoding(row, "order_id")
    assert repaired is not None
    assert repaired["order_id"] == "ORD-000001"


def test_fix_encoding_declines_when_nothing_to_strip():
    assert fix_encoding(VALID_ROW, "order_id") is None


def test_fix_encoding_declines_unsupported_field():
    assert fix_encoding(VALID_ROW, "amount") is None
