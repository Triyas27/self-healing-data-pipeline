import io

from app.core.pipeline.ingestion import read_csv_rows
from app.core.pipeline.validation import validate_batch
from app.synthetic.generator import FailureMode, generate_batch, known_customer_ids, to_csv_string

NON_DRIFT_MODES = [m for m in FailureMode if m != FailureMode.SCHEMA_DRIFT]


def test_mixed_failure_classes_isolated_per_row_end_to_end():
    rows: list[dict] = generate_batch(row_count=10, failure_rate=0.0, seed=1).rows

    for i, mode in enumerate(NON_DRIFT_MODES):
        failing_row = generate_batch(
            row_count=1, failure_rate=1.0, failure_mode=mode, seed=100 + i
        ).rows[0]
        rows.append(failing_row)

    csv_text = to_csv_string(rows)
    ingested = read_csv_rows(io.StringIO(csv_text))

    result = validate_batch(ingested, set(known_customer_ids()))

    assert len(result.valid_rows) == 10
    assert len(result.invalid_rows) == len(NON_DRIFT_MODES)
