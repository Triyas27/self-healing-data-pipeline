from dataclasses import dataclass, field

from app.core.pipeline.diagnosis import Diagnosis, diagnose
from app.core.pipeline.repair.transform_registry import apply_transform
from app.core.pipeline.validation import RowValidationResult, validate_row
from app.schemas.order import OrderIn


@dataclass
class RepairAttempt:
    diagnosis: Diagnosis
    row_before: dict
    row_after: dict | None
    revalidation: RowValidationResult | None


@dataclass
class RepairOutcome:
    healed: bool
    final_row: dict
    order: OrderIn | None
    attempts: list[RepairAttempt] = field(default_factory=list)
    quarantine_reason: str | None = None  # "no_fix" | "attempts_exhausted"


def repair_row(
    result: RowValidationResult,
    known_customer_ids: set[str],
    max_attempts: int,
    use_llm: bool | None = None,
) -> RepairOutcome:
    """Re-validates after each repair attempt to confirm whether it worked.
    Caps attempts at a configurable maximum; exhausted rows route to quarantine.
    """
    if result.valid:
        raise ValueError("Cannot repair a row that already passed validation")

    current_result = result
    attempts: list[RepairAttempt] = []

    for _ in range(max_attempts):
        diagnosis = diagnose(current_result, use_llm=use_llm)

        if not diagnosis.has_fix:
            attempts.append(
                RepairAttempt(
                    diagnosis=diagnosis, row_before=current_result.raw_row, row_after=None, revalidation=None
                )
            )
            return RepairOutcome(
                healed=False,
                final_row=current_result.raw_row,
                order=None,
                attempts=attempts,
                quarantine_reason="no_fix",
            )

        field_name = (
            current_result.errors[0]["loc"][0]
            if current_result.errors and current_result.errors[0]["loc"]
            else None
        )
        repaired_row = apply_transform(diagnosis.transform, current_result.raw_row, field_name)

        if repaired_row is None:
            attempts.append(
                RepairAttempt(
                    diagnosis=diagnosis, row_before=current_result.raw_row, row_after=None, revalidation=None
                )
            )
            return RepairOutcome(
                healed=False,
                final_row=current_result.raw_row,
                order=None,
                attempts=attempts,
                quarantine_reason="no_fix",
            )

        revalidated = validate_row(current_result.row_index, repaired_row, known_customer_ids)
        attempts.append(
            RepairAttempt(
                diagnosis=diagnosis, row_before=current_result.raw_row, row_after=repaired_row, revalidation=revalidated
            )
        )

        if revalidated.valid:
            return RepairOutcome(healed=True, final_row=repaired_row, order=revalidated.order, attempts=attempts)

        current_result = revalidated

    return RepairOutcome(
        healed=False,
        final_row=current_result.raw_row,
        order=None,
        attempts=attempts,
        quarantine_reason="attempts_exhausted",
    )
