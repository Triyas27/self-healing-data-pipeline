from datetime import datetime

from sqlalchemy import JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, utcnow


class QuarantineRow(Base):
    __tablename__ = "quarantine_rows"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("runs.id"))
    original_data: Mapped[dict] = mapped_column(JSON)
    error_type: Mapped[str]
    error_detail: Mapped[str]
    attempt_count: Mapped[int] = mapped_column(default=0)
    diagnosis_history: Mapped[list] = mapped_column(JSON, default=list)
    resolved: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
