from datetime import datetime

from sqlalchemy import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, utcnow


class Run(Base):
    __tablename__ = "runs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    started_at: Mapped[datetime] = mapped_column(default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(default=None)
    row_count: Mapped[int] = mapped_column(default=0)
    clean_first_pass: Mapped[int] = mapped_column(default=0)
    healed: Mapped[int] = mapped_column(default=0)
    quarantined: Mapped[int] = mapped_column(default=0)
    error_types: Mapped[dict] = mapped_column(JSON, default=dict)
    fixes_applied: Mapped[dict] = mapped_column(JSON, default=dict)
    avg_time_to_heal_ms: Mapped[float | None] = mapped_column(default=None)
    status: Mapped[str] = mapped_column(default="running")
