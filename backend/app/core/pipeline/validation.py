from dataclasses import dataclass, field

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.models import CustomerReference
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


def load_known_customer_ids(db: Session) -> set[str]:
    return {row.customer_id for row in db.query(CustomerReference).all()}


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


def validate_row(index: int, row: dict, known_customer_ids: set[str]) -> RowValidationResult:
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

    return RowValidationResult(row_index=index, raw_row=row, valid=True, order=order)


def validate_batch(rows: list[dict], known_customer_ids: set[str]) -> BatchValidationResult:
    """Isolates per-row failures, so one invalid row never invalidates the batch.
    Schema drift is the one batch-level gate and is checked before any row runs.
    """
    check_schema_drift(rows)
    results = [validate_row(i, row, known_customer_ids) for i, row in enumerate(rows)]
    return BatchValidationResult(results=results)
