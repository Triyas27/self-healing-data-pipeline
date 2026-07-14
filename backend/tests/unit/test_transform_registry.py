from app.core.pipeline.diagnosis.base import TransformID
from app.core.pipeline.repair.transform_registry import TRANSFORM_REGISTRY, apply_transform


def test_registry_covers_every_transform_id():
    assert set(TRANSFORM_REGISTRY.keys()) == set(TransformID)


def test_apply_transform_dispatches_to_registered_function():
    row = {"amount": "$49.99"}
    repaired = apply_transform(TransformID.COERCE_AMOUNT, row, "amount")
    assert repaired == {"amount": "49.99"}
