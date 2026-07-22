from app.core.pipeline.diagnosis.base import TransformID
from app.core.pipeline.repair.transforms import coerce_amount, fix_encoding, reformat_date

TRANSFORM_REGISTRY = {
    TransformID.COERCE_AMOUNT: coerce_amount,
    TransformID.REFORMAT_DATE: reformat_date,
    TransformID.FIX_ENCODING: fix_encoding,
}

if set(TRANSFORM_REGISTRY.keys()) != set(TransformID):
    raise RuntimeError("Every TransformID must have a registered function")


def apply_transform(transform_id: TransformID, row: dict[str, str], field: str) -> dict[str, str] | None:
    """Dispatches only to a pre-approved, registered function. There's no
    code path that executes arbitrary or generated repair logic."""
    transform_fn = TRANSFORM_REGISTRY[transform_id]
    return transform_fn(row, field)
