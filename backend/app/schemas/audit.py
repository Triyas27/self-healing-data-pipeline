from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AuditEntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    run_id: int
    row_identifier: str
    hypothesis: str | None
    transform_chosen: str | None
    confidence: float | None
    reasoning: str | None
    diagnosis_source: str
    outcome: str
    created_at: datetime
