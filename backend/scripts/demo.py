import asyncio

from pydantic import ValidationError

from app.db.session import AsyncSessionLocal, init_db
from app.models import CustomerReference, Order, Run
from app.schemas.order import OrderIn

VALID_ROW = {
    "order_id": "ORD-000123",
    "customer_id": "CUST-1001",
    "order_date": "2026-07-01",
    "amount": "49.99",
    "currency": "USD",
    "status": "pending",
}

INVALID_ROW = {**VALID_ROW, "order_id": "not-an-order-id", "currency": "XYZ"}


async def main() -> None:
    await init_db()
    async with AsyncSessionLocal() as db:
        if not await db.get(CustomerReference, "CUST-1001"):
            db.add(CustomerReference(customer_id="CUST-1001"))
            await db.commit()

        run = Run(row_count=1)
        db.add(run)
        await db.commit()
        await db.refresh(run)

        validated = OrderIn.model_validate(VALID_ROW)
        db.add(Order(run_id=run.id, **validated.model_dump()))
        await db.commit()
        print(f"Inserted valid order {validated.order_id} into run {run.id}")

    try:
        OrderIn.model_validate(INVALID_ROW)
    except ValidationError as exc:
        print("Invalid row rejected as expected:")
        for err in exc.errors():
            print(f"  {err['loc'][0]}: {err['msg']}")


if __name__ == "__main__":
    asyncio.run(main())
