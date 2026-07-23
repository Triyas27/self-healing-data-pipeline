from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pipeline.quarantine import count_quarantine_rows, list_quarantine_rows, resolve_quarantine_row
from app.db.session import get_db
from app.models import QuarantineRow
from app.schemas.quarantine import QuarantineRowOut, QuarantineRowPage

router = APIRouter(prefix="/quarantine", tags=["quarantine"])


@router.get("", response_model=QuarantineRowPage)
async def get_quarantine_rows(
    run_id: int | None = Query(None),
    resolved: bool | None = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    total = await count_quarantine_rows(db, run_id=run_id, resolved=resolved)
    items = await list_quarantine_rows(db, run_id=run_id, resolved=resolved, limit=limit, offset=offset)
    return QuarantineRowPage(items=items, total=total)


@router.get("/{quarantine_id}", response_model=QuarantineRowOut)
async def get_quarantine_row(quarantine_id: int, db: AsyncSession = Depends(get_db)):
    row = await db.get(QuarantineRow, quarantine_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Quarantine row not found")
    return row


@router.post("/{quarantine_id}/resolve", response_model=QuarantineRowOut)
async def resolve_row(quarantine_id: int, db: AsyncSession = Depends(get_db)):
    row = await resolve_quarantine_row(db, quarantine_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Quarantine row not found")
    return row
