import pytest

from app.core.pipeline.validation import SchemaDriftError, validate_batch
from app.synthetic.generator import FailureMode, generate_batch, known_customer_ids


def test_clean_batch_all_rows_valid():
    batch = generate_batch(row_count=20, failure_rate=0.0, seed=1)
    result = validate_batch(batch.rows, set(known_customer_ids()))
    assert len(result.valid_rows) == 20
    assert len(result.invalid_rows) == 0


def test_one_bad_row_does_not_invalidate_batch():
    clean = generate_batch(row_count=9, failure_rate=0.0, seed=1).rows
    bad = generate_batch(
        row_count=1, failure_rate=1.0, failure_mode=FailureMode.TYPE_MISMATCH, seed=2
    ).rows
    rows = clean + bad
    result = validate_batch(rows, set(known_customer_ids()))
    assert len(result.valid_rows) == 9
    assert len(result.invalid_rows) == 1
    assert result.invalid_rows[0].error_type == "invalid_amount"


def test_schema_drift_rejects_entire_batch():
    batch = generate_batch(
        row_count=5, failure_rate=1.0, failure_mode=FailureMode.SCHEMA_DRIFT, seed=1
    )
    with pytest.raises(SchemaDriftError):
        validate_batch(batch.rows, set(known_customer_ids()))


def test_invalid_foreign_key_flagged_but_well_formatted():
    batch = generate_batch(
        row_count=5, failure_rate=1.0, failure_mode=FailureMode.INVALID_FOREIGN_KEY, seed=1
    )
    result = validate_batch(batch.rows, set(known_customer_ids()))
    assert len(result.invalid_rows) == 5
    for row_result in result.invalid_rows:
        assert row_result.error_type == "invalid_foreign_key"
        assert row_result.order is not None  # format was fine, only the FK check failed


@pytest.mark.parametrize(
    "mode,expected_error_type",
    [
        (FailureMode.TYPE_MISMATCH, "invalid_amount"),
        (FailureMode.DATE_FORMAT_SWAP, "invalid_order_date"),
        (FailureMode.NULL_REQUIRED_FIELD, None),  # touches a random field
        (FailureMode.ENCODING_ISSUE, "invalid_order_id"),
    ],
)
def test_each_failure_mode_isolated_and_classified(mode, expected_error_type):
    batch = generate_batch(row_count=5, failure_rate=1.0, failure_mode=mode, seed=1)
    result = validate_batch(batch.rows, set(known_customer_ids()))
    assert len(result.invalid_rows) == 5
    if expected_error_type:
        assert all(r.error_type == expected_error_type for r in result.invalid_rows)
