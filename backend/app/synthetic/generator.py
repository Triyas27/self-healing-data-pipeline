import csv
import io
import random
from dataclasses import dataclass, field
from datetime import date, timedelta
from enum import Enum

from app.schemas.order import ORDER_COLUMNS, Currency, OrderStatus

CUSTOMER_POOL_SIZE = 200
_CUSTOMER_POOL = [f"CUST-{i:04d}" for i in range(1, CUSTOMER_POOL_SIZE + 1)]


def known_customer_ids() -> list[str]:
    return list(_CUSTOMER_POOL)


class FailureMode(str, Enum):
    SCHEMA_DRIFT = "schema_drift"
    TYPE_MISMATCH = "type_mismatch"
    DATE_FORMAT_SWAP = "date_format_swap"
    ENCODING_ISSUE = "encoding_issue"
    NULL_REQUIRED_FIELD = "null_required_field"
    INVALID_FOREIGN_KEY = "invalid_foreign_key"


@dataclass
class SyntheticBatch:
    rows: list[dict[str, str]] = field(default_factory=list)
    injected_failures: list[FailureMode | None] = field(default_factory=list)


def _clean_row(rng: random.Random, index: int) -> dict[str, str]:
    order_date = date(2026, 1, 1) + timedelta(days=rng.randint(0, 200))
    return {
        "order_id": f"ORD-{index:06d}",
        "customer_id": rng.choice(_CUSTOMER_POOL),
        "order_date": order_date.isoformat(),
        "amount": f"{rng.uniform(5, 500):.2f}",
        "currency": rng.choice([c.value for c in Currency]),
        "status": rng.choice([s.value for s in OrderStatus]),
    }


def _inject_schema_drift(row: dict[str, str], rng: random.Random) -> dict[str, str]:
    row = dict(row)
    row["internal_notes"] = "flagged for review"
    return row


def _inject_type_mismatch(row: dict[str, str], rng: random.Random) -> dict[str, str]:
    row = dict(row)
    row["amount"] = rng.choice(["fifty-two", "N/A", "$49.99"])
    return row


def _inject_date_format_swap(row: dict[str, str], rng: random.Random) -> dict[str, str]:
    row = dict(row)
    iso = date.fromisoformat(row["order_date"])
    row["order_date"] = iso.strftime("%d/%m/%Y")
    return row


def _inject_encoding_issue(row: dict[str, str], rng: random.Random) -> dict[str, str]:
    row = dict(row)
    # Pure accented characters (no ASCII letters) so the mojibake suffix is
    # unambiguously separable from the valid order_id prefix during repair.
    mojibake = "áéíóú".encode("utf-8").decode("latin-1")
    row["order_id"] = row["order_id"] + mojibake
    return row


def _inject_null_required_field(row: dict[str, str], rng: random.Random) -> dict[str, str]:
    row = dict(row)
    field_name = rng.choice(sorted(ORDER_COLUMNS))
    row[field_name] = ""
    return row


def _inject_invalid_foreign_key(row: dict[str, str], rng: random.Random) -> dict[str, str]:
    row = dict(row)
    row["customer_id"] = f"CUST-{9000 + rng.randint(0, 999)}"
    return row


_INJECTORS = {
    FailureMode.SCHEMA_DRIFT: _inject_schema_drift,
    FailureMode.TYPE_MISMATCH: _inject_type_mismatch,
    FailureMode.DATE_FORMAT_SWAP: _inject_date_format_swap,
    FailureMode.ENCODING_ISSUE: _inject_encoding_issue,
    FailureMode.NULL_REQUIRED_FIELD: _inject_null_required_field,
    FailureMode.INVALID_FOREIGN_KEY: _inject_invalid_foreign_key,
}


def generate_batch(
    row_count: int,
    failure_rate: float = 0.0,
    failure_mode: FailureMode | None = None,
    seed: int | None = None,
) -> SyntheticBatch:
    if row_count < 0:
        raise ValueError("row_count must be non-negative")
    if not 0 <= failure_rate <= 1:
        raise ValueError("failure_rate must be between 0 and 1")

    rng = random.Random(seed)
    batch = SyntheticBatch()

    for i in range(1, row_count + 1):
        row = _clean_row(rng, i)
        if rng.random() < failure_rate:
            mode = failure_mode or rng.choice(list(FailureMode))
            row = _INJECTORS[mode](row, rng)
            batch.injected_failures.append(mode)
        else:
            batch.injected_failures.append(None)
        batch.rows.append(row)

    return batch


def to_csv_string(rows: list[dict[str, str]]) -> str:
    if not rows:
        return ""
    fieldnames = sorted({key for row in rows for key in row.keys()})
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fieldnames, restval="")
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue()
