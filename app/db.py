from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    pass


def _ensure_sqlite_parent(database_url: str) -> None:
    if not database_url.startswith("sqlite:///"):
        return
    db_path = database_url.removeprefix("sqlite:///")
    if db_path and db_path != ":memory:":
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)


settings = get_settings()
_ensure_sqlite_parent(settings.database_url)
connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False, future=True)


def _ensure_sqlite_chat_session_host_id() -> None:
    if not settings.database_url.startswith("sqlite"):
        return
    inspector = inspect(engine)
    if "chat_sessions" not in inspector.get_table_names():
        return
    column_names = {column["name"] for column in inspector.get_columns("chat_sessions")}
    if "host_id" in column_names:
        return
    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE chat_sessions ADD COLUMN host_id INTEGER"))


def init_db() -> None:
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _ensure_sqlite_chat_session_host_id()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
