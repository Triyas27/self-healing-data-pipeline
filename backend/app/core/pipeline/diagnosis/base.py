from dataclasses import dataclass
from enum import Enum


class TransformID(str, Enum):
    """The fixed, pre-approved set of repair transforms. A Diagnosis can only
    ever reference one of these or None ("no fix"). There's no way to
    construct it from an arbitrary string."""

    COERCE_AMOUNT = "coerce_amount"
    REFORMAT_DATE = "reformat_date"
    FIX_ENCODING = "fix_encoding"


@dataclass
class Diagnosis:
    hypothesis: str
    transform: TransformID | None
    confidence: float
    reasoning: str
    source: str

    @property
    def has_fix(self) -> bool:
        return self.transform is not None
