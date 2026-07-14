from app.core.pipeline.diagnosis.base import Diagnosis, TransformID
from app.core.pipeline.repair.transforms import coerce_amount, fix_encoding, reformat_date
from app.core.pipeline.validation import RowValidationResult


def _no_fix(hypothesis: str, reasoning: str) -> Diagnosis:
    return Diagnosis(hypothesis=hypothesis, transform=None, confidence=1.0, reasoning=reasoning, source="heuristic")


def diagnose_heuristic(result: RowValidationResult) -> Diagnosis:
    if result.valid:
        raise ValueError("Cannot diagnose a row that already passed validation")

    if result.error_type == "invalid_foreign_key":
        return _no_fix(
            "customer_id does not exist in the known-customers reference set",
            "Unresolvable foreign key has no safe automatic fix.",
        )

    field_name = result.errors[0]["loc"][0] if result.errors and result.errors[0]["loc"] else None
    raw_value = result.raw_row.get(field_name) if field_name else None

    if raw_value is None or raw_value == "":
        return _no_fix(
            f"{field_name} is missing or blank",
            "Missing required field has no safe automatic fix.",
        )

    if field_name == "amount":
        repaired = coerce_amount(result.raw_row, field_name)
        if repaired is not None:
            return Diagnosis(
                hypothesis="amount contains currency symbols or non-numeric formatting noise",
                transform=TransformID.COERCE_AMOUNT,
                confidence=0.85,
                reasoning=f"Stripping non-numeric characters yields a valid positive amount: {repaired[field_name]!r}.",
                source="heuristic",
            )

    if field_name == "order_date":
        repaired = reformat_date(result.raw_row, field_name)
        if repaired is not None:
            return Diagnosis(
                hypothesis="order_date is a real calendar date in a non-ISO format",
                transform=TransformID.REFORMAT_DATE,
                confidence=0.9,
                reasoning=f"Reparsing recovers a valid ISO date: {repaired[field_name]!r}.",
                source="heuristic",
            )

    if field_name in ("order_id", "customer_id"):
        repaired = fix_encoding(result.raw_row, field_name)
        if repaired is not None:
            return Diagnosis(
                hypothesis=f"{field_name} has a trailing non-ASCII/mojibake artifact",
                transform=TransformID.FIX_ENCODING,
                confidence=0.85,
                reasoning=f"Stripping the trailing artifact recovers a valid value: {repaired[field_name]!r}.",
                source="heuristic",
            )

    return _no_fix(
        f"{field_name} fails validation and no registered transform applies",
        "No pre-approved transform matched; declining rather than guessing.",
    )
