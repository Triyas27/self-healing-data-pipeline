import re

from app.schemas.order import CUSTOMER_ID_PATTERN, ORDER_ID_PATTERN

_ID_CHAR = re.compile(r"[A-Za-z0-9]")
_FIELD_PATTERNS = {"order_id": ORDER_ID_PATTERN, "customer_id": CUSTOMER_ID_PATTERN}


def _strip_trailing_non_id_chars(value: str) -> str:
    i = len(value)
    while i > 0 and not _ID_CHAR.match(value[i - 1]):
        i -= 1
    return value[:i]


def fix_encoding(row: dict[str, str], field: str) -> dict[str, str] | None:
    if field not in _FIELD_PATTERNS:
        return None

    raw_value = row.get(field)
    if not raw_value:
        return None

    candidate = _strip_trailing_non_id_chars(raw_value)
    if candidate == raw_value or not _FIELD_PATTERNS[field].match(candidate):
        return None

    repaired = dict(row)
    repaired[field] = candidate
    return repaired
