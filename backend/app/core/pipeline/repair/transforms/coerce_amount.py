import re
from decimal import Decimal, InvalidOperation

_AMOUNT_NOISE_PATTERN = re.compile(r"[^\d.\-]")


def coerce_amount(row: dict[str, str], field: str = "amount") -> dict[str, str] | None:
    raw_value = row.get(field)
    if not raw_value:
        return None

    cleaned = _AMOUNT_NOISE_PATTERN.sub("", raw_value)
    if cleaned == raw_value:
        return None  # nothing to strip, so don't report a no-op fix

    try:
        if Decimal(cleaned) <= 0:
            return None
    except InvalidOperation:
        return None

    repaired = dict(row)
    repaired[field] = cleaned
    return repaired
