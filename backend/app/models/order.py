from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, utcnow


class Order(Base):
    __tablename__ = "orders"
    __table_args__ = (UniqueConstraint("run_id", "order_id", name="uq_orders_run_id_order_id"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    order_id: Mapped[str] = mapped_column(index=True)
    customer_id: Mapped[str] = mapped_column(ForeignKey("customer_reference.customer_id"))
    order_date: Mapped[date]
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    currency: Mapped[str]
    status: Mapped[str]
    run_id: Mapped[int] = mapped_column(ForeignKey("runs.id"))
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
