import pytest_asyncio
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.demo_seed import seed_demo_data
from app.db.base import Base
from app.models import CustomerReference, QuarantineRow, Run
from app.synthetic.generator import known_customer_ids


@pytest_asyncio.fixture()
async def db() -> AsyncSession:
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with AsyncSession(engine, expire_on_commit=False) as session:
        for cid in known_customer_ids():
            session.add(CustomerReference(customer_id=cid))
        await session.commit()
        yield session
    await engine.dispose()


async def _count(db: AsyncSession, model) -> int:
    return await db.scalar(select(func.count()).select_from(model))


async def test_seeds_demo_runs_into_an_empty_database(db):
    assert await _count(db, Run) == 0

    result = await seed_demo_data(db)

    assert result is not None
    assert len(result.runs) == 5
    assert await _count(db, Run) == 5
    assert all(run.status in ("completed", "rejected_schema_drift") for run in result.runs)


async def test_resolves_a_couple_of_quarantine_rows_for_a_natural_mix(db):
    result = await seed_demo_data(db)

    assert len(result.resolved_quarantine_ids) == 2
    resolved_count = await db.scalar(
        select(func.count()).select_from(QuarantineRow).where(QuarantineRow.resolved.is_(True))
    )
    assert resolved_count == 2


async def test_declines_to_seed_when_a_run_already_exists(db):
    first = await seed_demo_data(db)
    assert first is not None

    second = await seed_demo_data(db)

    assert second is None
    # Still exactly the runs from the first seed -- nothing got duplicated.
    assert await _count(db, Run) == 5
