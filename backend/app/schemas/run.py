from datetime import datetime

from pydantic import BaseModel, ConfigDict


class RunSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    started_at: datetime
    finished_at: datetime | None
    row_count: int
    clean_first_pass: int
    healed: int
    quarantined: int
    error_types: dict[str, int]
    fixes_applied: dict[str, int]
    avg_time_to_heal_ms: float | None
    status: str
