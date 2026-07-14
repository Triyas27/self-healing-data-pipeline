from app.core.pipeline.diagnosis import diagnose
from app.core.pipeline.validation import validate_batch
from app.synthetic.generator import FailureMode, generate_batch, known_customer_ids

NON_DRIFT_MODES = [m for m in FailureMode if m != FailureMode.SCHEMA_DRIFT]


def main() -> None:
    rows = []
    for i, mode in enumerate(NON_DRIFT_MODES):
        rows.append(
            generate_batch(row_count=1, failure_rate=1.0, failure_mode=mode, seed=100 + i).rows[0]
        )

    result = validate_batch(rows, set(known_customer_ids()))

    print(f"{len(result.invalid_rows)} invalid rows, diagnosing each (heuristic mode)\n")
    for row_result in result.invalid_rows:
        diagnosis = diagnose(row_result, use_llm=False)
        outcome = diagnosis.transform.value if diagnosis.has_fix else "NO FIX"
        print(f"row {row_result.row_index} [{row_result.error_type}]")
        print(f"  hypothesis: {diagnosis.hypothesis}")
        print(f"  outcome:    {outcome}  (confidence={diagnosis.confidence})")
        print(f"  reasoning:  {diagnosis.reasoning}\n")


if __name__ == "__main__":
    main()
