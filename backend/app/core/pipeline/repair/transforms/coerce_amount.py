import re
from decimal import Decimal, InvalidOperation

_AMOUNT_NOISE_PATTERN = re.compile(r"[^\d.\-]")
_PAREN_NEGATIVE_PATTERN = re.compile(r"^\s*\(.+\)\s*$")


def coerce_amount(row: dict[str, str], field: str = "amount") -> dict[str, str] | None:
    raw_value = row.get(field)
    if not raw_value:
        return None

    if _PAREN_NEGATIVE_PATTERN.match(raw_value):
        # Accounting notation for a negative value, e.g. "(49.99)". Stripping the
        # parens as noise would silently flip a real negative into a positive
        # amount, which is fabrication, not a formatting fix. Decline instead.
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
