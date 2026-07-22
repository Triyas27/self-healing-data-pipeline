from dataclasses import dataclass, field

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import CustomerReference, Order
from app.schemas.order import ORDER_COLUMNS, OrderIn


class SchemaDriftError(Exception):
    def __init__(self, unexpected_columns: set[str]):
        self.unexpected_columns = unexpected_columns
        super().__init__(f"Unexpected columns in batch: {sorted(unexpected_columns)}")


@dataclass
class RowValidationResult:
    row_index: int
    raw_row: dict
    valid: bool
    order: OrderIn | None = None
    errors: list[dict] = field(default_factory=list)
    error_type: str | None = None


@dataclass
class BatchValidationResult:
    results: list[RowValidationResult]

    @property
    def valid_rows(self) -> list[RowValidationResult]:
        return [r for r in self.results if r.valid]

    @property
    def invalid_rows(self) -> list[RowValidationResult]:
        return [r for r in self.results if not r.valid]


async def load_known_customer_ids(db: AsyncSession) -> set[str]:
    result = await db.execute(select(CustomerReference.customer_id))
    return set(result.scalars().all())


async def load_existing_order_ids(db: AsyncSession) -> set[str]:
    result = await db.execute(select(Order.order_id))
    return set(result.scalars().all())


def check_schema_drift(rows: list[dict]) -> None:
    """Rejects the whole batch if any row carries an undeclared column."""
    all_columns: set[str] = set()
    for row in rows:
        all_columns.update(row.keys())
    unexpected = all_columns - ORDER_COLUMNS
    if unexpected:
        raise SchemaDriftError(unexpected)


def _classify_pydantic_error(errors: list[dict]) -> str:
    field_name = errors[0]["loc"][0] if errors and errors[0]["loc"] else "unknown"
    return f"invalid_{field_name}"


def validate_row(
    index: int,
    row: dict,
    known_customer_ids: set[str],
    existing_order_ids: frozenset[str] = frozenset(),
) -> RowValidationResult:
    try:
        order = OrderIn.model_validate(row)
    except ValidationError as exc:
        errors = exc.errors()
        return RowValidationResult(
            row_index=index,
            raw_row=row,
            valid=False,
            errors=errors,
            error_type=_classify_pydantic_error(errors),
        )

    if order.customer_id not in known_customer_ids:
        return RowValidationResult(
            row_index=index,
            raw_row=row,
            valid=False,
            order=order,
            errors=[
                {
                    "loc": ("customer_id",),
                    "msg": f"Unknown customer_id: {order.customer_id}",
                    "type": "referential_integrity",
                }
            ],
            error_type="invalid_foreign_key",
        )

    if order.order_id in existing_order_ids:
        return RowValidationResult(
            row_index=index,
            raw_row=row,
            valid=False,
            order=order,
            errors=[
                {
                    "loc": ("order_id",),
                    "msg": f"Duplicate order_id: {order.order_id}",
                    "type": "duplicate",
                }
            ],
            error_type="duplicate_order_id",
        )

    return RowValidationResult(row_index=index, raw_row=row, valid=True, order=order)


def validate_batch(
    rows: list[dict],
    known_customer_ids: set[str],
    existing_order_ids: frozenset[str] = frozenset(),
) -> BatchValidationResult:
    """Isolates per-row failures, so one invalid row never invalidates the batch.
    Schema drift is the one batch-level gate and is checked before any row runs.
    Also catches duplicate order_ids, both against rows already persisted from a
    prior run and against earlier rows in this same batch.
    """
    check_schema_drift(rows)

    seen_order_ids = set(existing_order_ids)
    results = []
    for i, row in enumerate(rows):
        result = validate_row(i, row, known_customer_ids, seen_order_ids)
        if result.valid:
            seen_order_ids.add(result.order.order_id)
        results.append(result)

    return BatchValidationResult(results=results)
