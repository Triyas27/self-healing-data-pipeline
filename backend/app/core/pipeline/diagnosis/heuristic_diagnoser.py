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

    if result.error_type == "duplicate_order_id":
        return _no_fix(
            "order_id already exists in the clean data store from a previous run",
            "Duplicate orders aren't auto-resolved; a human should decide whether "
            "this is a resubmission or a genuine conflict.",
        )

    # A row can fail on more than one field at once. Check every current error
    # instead of only the first, so a fixable field isn't skipped just because
    # an unrelated, unfixable field happens to fail first.
    blank_field = None
    for error in result.errors:
        field_name = error["loc"][0] if error["loc"] else None
        raw_value = result.raw_row.get(field_name) if field_name else None

        if raw_value is None or raw_value == "":
            if blank_field is None:
                blank_field = field_name
            continue

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

    if blank_field is not None:
        return _no_fix(
            f"{blank_field} is missing or blank",
            "Missing required field has no safe automatic fix.",
        )

    field_names = ", ".join(e["loc"][0] for e in result.errors if e["loc"])
    return _no_fix(
        f"{field_names} fails validation and no registered transform applies",
        "No pre-approved transform matched; declining rather than guessing.",
    )
