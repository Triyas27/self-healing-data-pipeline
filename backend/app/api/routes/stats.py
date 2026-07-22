from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models import Run
from app.schemas.stats import HealRatePoint, StatsOut

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("", response_model=StatsOut)
async def get_stats(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Run).where(Run.status == "completed").order_by(Run.id.asc()))
    runs = result.scalars().all()

    total_rows = sum(r.row_count for r in runs)
    total_clean = sum(r.clean_first_pass for r in runs)
    total_healed = sum(r.healed for r in runs)
    total_quarantined = sum(r.quarantined for r in runs)

    overall_heal_rate = (total_clean + total_healed) / total_rows if total_rows else 0.0
    needed_repair = total_healed + total_quarantined
    auto_heal_rate = total_healed / needed_repair if needed_repair else 0.0

    heal_rate_over_time = [
        HealRatePoint(
            run_id=r.id,
            started_at=r.started_at.isoformat(),
            heal_rate=(r.clean_first_pass + r.healed) / r.row_count if r.row_count else 0.0,
        )
        for r in runs
    ]

    return StatsOut(
        total_runs=len(runs),
        total_rows_processed=total_rows,
        total_clean_first_pass=total_clean,
        total_healed=total_healed,
        total_quarantined=total_quarantined,
        overall_heal_rate=overall_heal_rate,
        auto_heal_rate=auto_heal_rate,
        heal_rate_over_time=heal_rate_over_time,
    )
