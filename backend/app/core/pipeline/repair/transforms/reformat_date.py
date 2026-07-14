from datetime import datetime

_DATE_FORMATS = ["%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y", "%Y/%m/%d"]


def reformat_date(row: dict[str, str], field: str = "order_date") -> dict[str, str] | None:
    raw_value = row.get(field)
    if not raw_value:
        return None

    for fmt in _DATE_FORMATS:
        try:
            parsed = datetime.strptime(raw_value, fmt).date()
        except ValueError:
            continue
        repaired = dict(row)
        repaired[field] = parsed.isoformat()
        return repaired

    return None
