from datetime import date
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models import CustomerReference, Order, Run


def test_create_tables_and_insert_order():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as db:
        db.add(CustomerReference(customer_id="CUST-1001"))
        run = Run(row_count=1)
        db.add(run)
        db.commit()
        db.refresh(run)

        db.add(
            Order(
                order_id="ORD-000123",
                customer_id="CUST-1001",
                order_date=date(2026, 7, 1),
                amount=Decimal("49.99"),
                currency="USD",
                status="pending",
                run_id=run.id,
            )
        )
        db.commit()

        assert db.query(Order).count() == 1
