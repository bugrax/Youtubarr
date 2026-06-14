"""Database engine and session helpers."""
import os
from collections.abc import Iterator

from sqlmodel import Session, SQLModel, create_engine

from .config import get_settings

_settings = get_settings()
os.makedirs(os.path.dirname(_settings.db_path) or ".", exist_ok=True)

engine = create_engine(
    f"sqlite:///{_settings.db_path}",
    connect_args={"check_same_thread": False},
)


def init_db() -> None:
    # Import models so SQLModel registers the tables before create_all.
    from . import models  # noqa: F401
    SQLModel.metadata.create_all(engine)


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session
