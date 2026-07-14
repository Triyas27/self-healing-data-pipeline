from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from app.core.pipeline.orchestrator import run_pipeline
from app.db.session import get_db
from app.models import Run
from app.schemas.run import RunSummary
from app.synthetic.generator import FailureMode, generate_batch

router = APIRouter(prefix="/runs", tags=["runs"])


@router.post("/trigger", response_model=RunSummary)
def trigger_run(
    file: UploadFile | None = File(None),
    row_count: int = Query(50, ge=1, le=10000),
    failure_rate: float = Query(0.2, ge=0.0, le=1.0),
    failure_mode: FailureMode | None = Query(None),
    seed: int | None = Query(None),
    use_llm: bool | None = Query(
        None, description="Force LLM (true) or heuristic (false) diagnosis; omit for the configured default"
    ),
    db: Session = Depends(get_db),
):
    if file is not None:
        source = file.file
    else:
        batch = generate_batch(row_count=row_count, failure_rate=failure_rate, failure_mode=failure_mode, seed=seed)
        source = batch.rows

    try:
        run = run_pipeline(db, source, use_llm=use_llm)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Failed to process batch: {exc}") from exc

    return run


@router.get("", response_model=list[RunSummary])
def list_runs(limit: int = Query(50, ge=1, le=500), db: Session = Depends(get_db)):
    return db.query(Run).order_by(Run.id.desc()).limit(limit).all()


@router.get("/{run_id}", response_model=RunSummary)
def get_run(run_id: int, db: Session = Depends(get_db)):
    run = db.get(Run, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return run
