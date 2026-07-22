import re
from decimal import Decimal, InvalidOperation

# Characters verified to be purely decorative around a currency amount: symbols
# and thousands/space separators. Anything else left over after stripping these
# (letters, parentheses, suffixes like "CR"/"DR") might carry real meaning --
# e.g. accounting notation for a negative value -- so it's left alone and lets
# Decimal parsing fail naturally instead of being silently discarded as noise.
_DECORATIVE_CHARS = re.compile(r"[$€£¥,\s]")


def coerce_amount(row: dict[str, str], field: str = "amount") -> dict[str, str] | None:
    raw_value = row.get(field)
    if not raw_value:
        return None

    cleaned = _DECORATIVE_CHARS.sub("", raw_value)
    if cleaned == raw_value:
        return None  # nothing recognized as decorative, so don't report a no-op fix

    try:
        amount = Decimal(cleaned)
    except InvalidOperation:
        return None  # leftover non-numeric characters -- decline rather than guess

    if amount <= 0:
        return None

    repaired = dict(row)
    repaired[field] = cleaned
    return repaired
