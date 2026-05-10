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


def _ensure_sqlite_action_runs_columns() -> None:
    if not settings.database_url.startswith("sqlite"):
        return
    inspector = inspect(engine)
    if "action_runs" not in inspector.get_table_names():
        return
    column_names = {column["name"] for column in inspector.get_columns("action_runs")}
    migrations = {
        "session_id": "ALTER TABLE action_runs ADD COLUMN session_id INTEGER",
        "host_id": "ALTER TABLE action_runs ADD COLUMN host_id INTEGER",
        "action": "ALTER TABLE action_runs ADD COLUMN action VARCHAR(100) DEFAULT '' NOT NULL",
        "category": "ALTER TABLE action_runs ADD COLUMN category VARCHAR(100) DEFAULT '' NOT NULL",
        "risk": "ALTER TABLE action_runs ADD COLUMN risk VARCHAR(32) DEFAULT 'low' NOT NULL",
        "command_preview": "ALTER TABLE action_runs ADD COLUMN command_preview TEXT DEFAULT '' NOT NULL",
        "params_json": "ALTER TABLE action_runs ADD COLUMN params_json TEXT DEFAULT '{}' NOT NULL",
        "status": "ALTER TABLE action_runs ADD COLUMN status VARCHAR(32) DEFAULT 'prepared' NOT NULL",
        "execution_enabled": "ALTER TABLE action_runs ADD COLUMN execution_enabled BOOLEAN DEFAULT 0 NOT NULL",
        "approved_at": "ALTER TABLE action_runs ADD COLUMN approved_at DATETIME",
        "rejected_at": "ALTER TABLE action_runs ADD COLUMN rejected_at DATETIME",
        "expired_at": "ALTER TABLE action_runs ADD COLUMN expired_at DATETIME",
        "approval_note": "ALTER TABLE action_runs ADD COLUMN approval_note TEXT",
        "rejection_note": "ALTER TABLE action_runs ADD COLUMN rejection_note TEXT",
        "expiration_note": "ALTER TABLE action_runs ADD COLUMN expiration_note TEXT",
        "approved_by": "ALTER TABLE action_runs ADD COLUMN approved_by VARCHAR(120)",
        "rejected_by": "ALTER TABLE action_runs ADD COLUMN rejected_by VARCHAR(120)",
        "expired_by": "ALTER TABLE action_runs ADD COLUMN expired_by VARCHAR(120)",
        "expires_at": "ALTER TABLE action_runs ADD COLUMN expires_at DATETIME",
        "created_at": "ALTER TABLE action_runs ADD COLUMN created_at DATETIME",
    }
    with engine.begin() as connection:
        for column_name, statement in migrations.items():
            if column_name not in column_names:
                connection.execute(text(statement))


def _ensure_sqlite_action_executions_columns() -> None:
    if not settings.database_url.startswith("sqlite"):
        return
    inspector = inspect(engine)
    if "action_executions" not in inspector.get_table_names():
        return
    column_names = {column["name"] for column in inspector.get_columns("action_executions")}
    migrations = {
        "run_id": "ALTER TABLE action_executions ADD COLUMN run_id INTEGER DEFAULT 0 NOT NULL",
        "host_id": "ALTER TABLE action_executions ADD COLUMN host_id INTEGER",
        "ssh_profile_id": "ALTER TABLE action_executions ADD COLUMN ssh_profile_id INTEGER",
        "action": "ALTER TABLE action_executions ADD COLUMN action VARCHAR(100) DEFAULT '' NOT NULL",
        "command_preview": "ALTER TABLE action_executions ADD COLUMN command_preview TEXT DEFAULT '' NOT NULL",
        "status": "ALTER TABLE action_executions ADD COLUMN status VARCHAR(32) DEFAULT 'running' NOT NULL",
        "exit_code": "ALTER TABLE action_executions ADD COLUMN exit_code INTEGER",
        "stdout": "ALTER TABLE action_executions ADD COLUMN stdout TEXT DEFAULT '' NOT NULL",
        "stderr": "ALTER TABLE action_executions ADD COLUMN stderr TEXT DEFAULT '' NOT NULL",
        "stdout_truncated": "ALTER TABLE action_executions ADD COLUMN stdout_truncated BOOLEAN DEFAULT 0 NOT NULL",
        "stderr_truncated": "ALTER TABLE action_executions ADD COLUMN stderr_truncated BOOLEAN DEFAULT 0 NOT NULL",
        "started_at": "ALTER TABLE action_executions ADD COLUMN started_at DATETIME",
        "finished_at": "ALTER TABLE action_executions ADD COLUMN finished_at DATETIME",
        "duration_ms": "ALTER TABLE action_executions ADD COLUMN duration_ms INTEGER",
        "error": "ALTER TABLE action_executions ADD COLUMN error TEXT",
        "error_category": "ALTER TABLE action_executions ADD COLUMN error_category VARCHAR(64)",
        "warnings_json": "ALTER TABLE action_executions ADD COLUMN warnings_json TEXT DEFAULT '[]' NOT NULL",
        "analysis_json": "ALTER TABLE action_executions ADD COLUMN analysis_json TEXT",
        "analysis_summary": "ALTER TABLE action_executions ADD COLUMN analysis_summary TEXT",
        "analysis_status": "ALTER TABLE action_executions ADD COLUMN analysis_status VARCHAR(32)",
        "analysis_attached_at": "ALTER TABLE action_executions ADD COLUMN analysis_attached_at DATETIME",
        "chat_attached_at": "ALTER TABLE action_executions ADD COLUMN chat_attached_at DATETIME",
    }
    with engine.begin() as connection:
        for column_name, statement in migrations.items():
            if column_name not in column_names:
                connection.execute(text(statement))


def init_db() -> None:
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _ensure_sqlite_chat_session_host_id()
    _ensure_sqlite_action_runs_columns()
    _ensure_sqlite_action_executions_columns()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
