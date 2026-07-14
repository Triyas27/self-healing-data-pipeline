from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CustomerReference(Base):
    __tablename__ = "customer_reference"

    customer_id: Mapped[str] = mapped_column(primary_key=True)
