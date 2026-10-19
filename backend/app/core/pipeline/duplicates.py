from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Order
from app.schemas.order import OrderIn

# Keeps each IN (...) clause under SQLite's bound-parameter limit.
_ID_CHUNK_SIZE = 500


def is_exact_duplicate(incoming: OrderIn, stored: OrderIn | Order) -> bool:
    """True when every field matches, i.e. a plain resubmission of an order that
    is already stored. Same order_id with any differing field is a genuine
    conflict instead, which only a human can resolve."""
    return (
        incoming.order_id == stored.order_id
        and incoming.customer_id == stored.customer_id
        and incoming.order_date == stored.order_date
        and incoming.amount == stored.amount
        and incoming.currency == stored.currency
        and incoming.status == stored.status
    )


async def load_stored_orders(db: AsyncSession, order_ids: set[str]) -> dict[str, Order]:
    stored: dict[str, Order] = {}
    ids = sorted(order_ids)
    for start in range(0, len(ids), _ID_CHUNK_SIZE):
        chunk = ids[start : start + _ID_CHUNK_SIZE]
        result = await db.execute(select(Order).where(Order.order_id.in_(chunk)))
        for order in result.scalars().all():
            stored[order.order_id] = order
    return stored
