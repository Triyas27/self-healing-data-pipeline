from pydantic import BaseModel


class HealRatePoint(BaseModel):
    run_id: int
    started_at: str
    heal_rate: float


class StatsOut(BaseModel):
    total_runs: int
    total_rows_processed: int
    total_clean_first_pass: int
    total_healed: int
    total_quarantined: int
    overall_heal_rate: float
    auto_heal_rate: float
    heal_rate_over_time: list[HealRatePoint]
    error_type_totals: dict[str, int]
    fixes_applied_totals: dict[str, int]
