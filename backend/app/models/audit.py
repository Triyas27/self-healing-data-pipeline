from datetime import datetime

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, utcnow


class AuditEntry(Base):
    __tablename__ = "audit_entries"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("runs.id"))
    row_identifier: Mapped[str]
    hypothesis: Mapped[str | None] = mapped_column(default=None)
    transform_chosen: Mapped[str | None] = mapped_column(default=None)
    confidence: Mapped[float | None] = mapped_column(default=None)
    reasoning: Mapped[str | None] = mapped_column(default=None)
    diagnosis_source: Mapped[str]
    outcome: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
