import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.db.base import Base

if settings.database_url.startswith("sqlite:///") and ":memory:" not in settings.database_url:
    db_dir = os.path.dirname(settings.database_url.removeprefix("sqlite:///"))
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    from app import models  # noqa: F401 registers model metadata

    Base.metadata.create_all(bind=engine)
