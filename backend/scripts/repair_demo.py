from app.config import settings
from app.core.pipeline.repair.repair import repair_row
from app.core.pipeline.validation import validate_batch
from app.synthetic.generator import FailureMode, generate_batch, known_customer_ids

NON_DRIFT_MODES = [m for m in FailureMode if m != FailureMode.SCHEMA_DRIFT]


def main() -> None:
    rows = []
    for i, mode in enumerate(NON_DRIFT_MODES):
        rows.append(
            generate_batch(row_count=1, failure_rate=1.0, failure_mode=mode, seed=100 + i).rows[0]
        )

    known_ids = set(known_customer_ids())
    result = validate_batch(rows, known_ids)

    print(f"{len(result.invalid_rows)} invalid rows, running repair (max_attempts={settings.max_repair_attempts})\n")
    for row_result in result.invalid_rows:
        outcome = repair_row(row_result, known_ids, max_attempts=settings.max_repair_attempts, use_llm=False)
        status = "HEALED" if outcome.healed else f"QUARANTINED ({outcome.quarantine_reason})"
        print(f"row {row_result.row_index} [{row_result.error_type}] -> {status}")
        for i, attempt in enumerate(outcome.attempts, start=1):
            transform = attempt.diagnosis.transform.value if attempt.diagnosis.has_fix else "no_fix"
            print(f"  attempt {i}: transform={transform} confidence={attempt.diagnosis.confidence}")
        if outcome.healed:
            print(f"  final row: {outcome.final_row}")
        print()


if __name__ == "__main__":
    main()
