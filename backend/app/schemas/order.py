import re
from datetime import date
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, Field, field_validator

ORDER_ID_PATTERN = re.compile(r"^ORD-[A-Za-z0-9]{6,}$")
CUSTOMER_ID_PATTERN = re.compile(r"^CUST-[A-Za-z0-9]{4,}$")


class Currency(str, Enum):
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    CAD = "CAD"
    AUD = "AUD"
    JPY = "JPY"


class OrderStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class OrderIn(BaseModel):
    order_id: str
    customer_id: str
    order_date: date
    amount: Decimal = Field(gt=0)
    currency: Currency
    status: OrderStatus

    @field_validator("order_id")
    @classmethod
    def validate_order_id(cls, v: str) -> str:
        if not ORDER_ID_PATTERN.match(v):
            raise ValueError(f"order_id must match {ORDER_ID_PATTERN.pattern}")
        return v

    @field_validator("customer_id")
    @classmethod
    def validate_customer_id(cls, v: str) -> str:
        if not CUSTOMER_ID_PATTERN.match(v):
            raise ValueError(f"customer_id must match {CUSTOMER_ID_PATTERN.pattern}")
        return v


ORDER_COLUMNS = set(OrderIn.model_fields.keys())
