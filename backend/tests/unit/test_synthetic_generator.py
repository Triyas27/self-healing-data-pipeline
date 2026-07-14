import pytest
from pydantic import ValidationError

from app.schemas.order import ORDER_COLUMNS, OrderIn
from app.synthetic.generator import FailureMode, generate_batch, known_customer_ids


def test_clean_batch_all_rows_pass_schema():
    batch = generate_batch(row_count=25, failure_rate=0.0, seed=1)
    assert all(f is None for f in batch.injected_failures)
    for row in batch.rows:
        order = OrderIn.model_validate(row)
        assert order.customer_id in known_customer_ids()


def test_failure_rate_bounds_rejected():
    with pytest.raises(ValueError):
        generate_batch(row_count=10, failure_rate=1.5)
    with pytest.raises(ValueError):
        generate_batch(row_count=10, failure_rate=-0.1)


def test_same_seed_is_reproducible():
    a = generate_batch(row_count=15, failure_rate=0.4, seed=42)
    b = generate_batch(row_count=15, failure_rate=0.4, seed=42)
    assert a.rows == b.rows
    assert a.injected_failures == b.injected_failures


@pytest.mark.parametrize("mode", list(FailureMode))
def test_isolated_failure_mode_only_injects_that_mode(mode):
    batch = generate_batch(row_count=20, failure_rate=1.0, failure_mode=mode, seed=7)
    assert all(f == mode for f in batch.injected_failures)


def test_schema_drift_adds_undeclared_column():
    batch = generate_batch(row_count=5, failure_rate=1.0, failure_mode=FailureMode.SCHEMA_DRIFT, seed=1)
    for row in batch.rows:
        assert set(row.keys()) - ORDER_COLUMNS


def test_type_mismatch_fails_amount_validation():
    batch = generate_batch(row_count=5, failure_rate=1.0, failure_mode=FailureMode.TYPE_MISMATCH, seed=1)
    for row in batch.rows:
        with pytest.raises(ValidationError):
            OrderIn.model_validate(row)


def test_date_format_swap_fails_date_validation():
    batch = generate_batch(row_count=5, failure_rate=1.0, failure_mode=FailureMode.DATE_FORMAT_SWAP, seed=1)
    for row in batch.rows:
        with pytest.raises(ValidationError):
            OrderIn.model_validate(row)


def test_encoding_issue_fails_order_id_validation():
    batch = generate_batch(row_count=5, failure_rate=1.0, failure_mode=FailureMode.ENCODING_ISSUE, seed=1)
    for row in batch.rows:
        with pytest.raises(ValidationError):
            OrderIn.model_validate(row)


def test_null_required_field_fails_validation():
    batch = generate_batch(row_count=5, failure_rate=1.0, failure_mode=FailureMode.NULL_REQUIRED_FIELD, seed=1)
    for row in batch.rows:
        with pytest.raises(ValidationError):
            OrderIn.model_validate(row)


def test_invalid_foreign_key_passes_schema_but_unknown_customer():
    batch = generate_batch(row_count=5, failure_rate=1.0, failure_mode=FailureMode.INVALID_FOREIGN_KEY, seed=1)
    for row in batch.rows:
        order = OrderIn.model_validate(row)
        assert order.customer_id not in known_customer_ids()
