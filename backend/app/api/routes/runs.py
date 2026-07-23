import logging

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pipeline.orchestrator import run_pipeline
from app.db.session import get_db
from app.models import AuditEntry, Run
from app.schemas.audit import AuditEntryOut
from app.schemas.run import RunPage, RunSummary
from app.synthetic.generator import FailureMode, generate_batch

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/runs", tags=["runs"])


@router.post("/trigger", response_model=RunSummary)
async def trigger_run(
    file: UploadFile | None = File(None),
    row_count: int = Query(50, ge=1, le=10000),
    failure_rate: float = Query(0.2, ge=0.0, le=1.0),
    failure_mode: FailureMode | None = Query(None),
    seed: int | None = Query(None),
    use_llm: bool | None = Query(
        None, description="Force LLM (true) or heuristic (false) diagnosis; omit for the configured default"
    ),
    db: AsyncSession = Depends(get_db),
):
    if file is not None:
        source = file.file
    else:
        batch = generate_batch(row_count=row_count, failure_rate=failure_rate, failure_mode=failure_mode, seed=seed)
        source = batch.rows

    try:
        run = await run_pipeline(db, source, use_llm=use_llm)
    except ValueError as exc:
        # Deliberately raised by the pipeline for a specific, actionable
        # reason (e.g. the upload-row cap) -- safe and useful to show as-is.
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        # Anything else is an unexpected internal failure. Log the real
        # exception server-side but don't echo its text to the client --
        # it could contain implementation details that shouldn't leak.
        logger.exception("Unexpected error processing batch")
        raise HTTPException(status_code=422, detail="Failed to process batch.") from exc

    return run


@router.get("", response_model=RunPage)
async def list_runs(
    limit: int = Query(20, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    total = await db.scalar(select(func.count()).select_from(Run))
    result = await db.execute(select(Run).order_by(Run.id.desc()).limit(limit).offset(offset))
    return RunPage(items=list(result.scalars().all()), total=total or 0)


@router.get("/{run_id}", response_model=RunSummary)
async def get_run(run_id: int, db: AsyncSession = Depends(get_db)):
    run = await db.get(Run, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


@router.get("/{run_id}/audit", response_model=list[AuditEntryOut])
async def get_run_audit(run_id: int, db: AsyncSession = Depends(get_db)):
    run = await db.get(Run, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    result = await db.execute(
        select(AuditEntry).where(AuditEntry.run_id == run_id).order_by(AuditEntry.row_identifier, AuditEntry.id)
    )
    return result.scalars().all()
