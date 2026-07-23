from datetime import datetime

from pydantic import BaseModel, ConfigDict


class QuarantineRowOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    run_id: int
    original_data: dict
    error_type: str
    error_detail: str
    attempt_count: int
    diagnosis_history: list[dict]
    resolved: bool
    created_at: datetime


class QuarantineRowPage(BaseModel):
    items: list[QuarantineRowOut]
    total: int
