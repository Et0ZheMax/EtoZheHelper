from datetime import datetime, timezone

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class SshProfile(Base):
    __tablename__ = "ssh_profiles"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), index=True)
    username: Mapped[str] = mapped_column(String(128))
    auth_type: Mapped[str] = mapped_column(String(32), default="manual")
    key_ref: Mapped[str | None] = mapped_column(String(500), nullable=True)
    password_ref: Mapped[str | None] = mapped_column(String(200), nullable=True)
    sudo_mode: Mapped[str] = mapped_column(String(32), default="none")
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)

    hosts: Mapped[list["Host"]] = relationship(back_populates="ssh_profile")


class Host(Base):
    __tablename__ = "hosts"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), index=True)
    hostname: Mapped[str] = mapped_column(String(253), index=True)
    port: Mapped[int] = mapped_column(Integer, default=22)
    os_family: Mapped[str] = mapped_column(String(32), default="linux")
    tags: Mapped[str | None] = mapped_column(Text, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    ssh_profile_id: Mapped[int | None] = mapped_column(ForeignKey("ssh_profiles.id"), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)

    ssh_profile: Mapped[SshProfile | None] = relationship(back_populates="hosts")


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(200), default="New chat")
    host_id: Mapped[int | None] = mapped_column(ForeignKey("hosts.id"), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)

    messages: Mapped[list["ChatMessage"]] = relationship(back_populates="session", cascade="all, delete-orphan")
    host: Mapped[Host | None] = relationship()


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("chat_sessions.id"), index=True)
    role: Mapped[str] = mapped_column(String(32), index=True)
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)

    session: Mapped[ChatSession] = relationship(back_populates="messages")


ACTION_RUN_STATUSES = {"prepared", "approved", "rejected", "expired"}


class ActionRun(Base):
    __tablename__ = "action_runs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    session_id: Mapped[int | None] = mapped_column(ForeignKey("chat_sessions.id"), nullable=True, index=True)
    host_id: Mapped[int | None] = mapped_column(ForeignKey("hosts.id"), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(100), index=True)
    category: Mapped[str] = mapped_column(String(100), index=True)
    risk: Mapped[str] = mapped_column(String(32), default="low")
    command_preview: Mapped[str] = mapped_column(Text)
    params_json: Mapped[str] = mapped_column(Text, default="{}")
    status: Mapped[str] = mapped_column(String(32), default="prepared", index=True)
    execution_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    approved_at: Mapped[datetime | None] = mapped_column(nullable=True)
    rejected_at: Mapped[datetime | None] = mapped_column(nullable=True)
    expired_at: Mapped[datetime | None] = mapped_column(nullable=True)
    approval_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    rejection_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    expiration_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    approved_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    rejected_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    expired_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)

    session: Mapped[ChatSession | None] = relationship()
    host: Mapped[Host | None] = relationship()

    @validates("status")
    def validate_status(self, key: str, value: str) -> str:
        if value not in ACTION_RUN_STATUSES:
            raise ValueError("Unsupported action run status")
        return value

    @validates("execution_enabled")
    def validate_execution_enabled(self, key: str, value: bool) -> bool:
        return False


ACTION_EXECUTION_STATUSES = {"running", "completed", "failed", "timed_out", "blocked"}


class ActionExecution(Base):
    __tablename__ = "action_executions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("action_runs.id"), index=True)
    host_id: Mapped[int | None] = mapped_column(ForeignKey("hosts.id"), nullable=True, index=True)
    ssh_profile_id: Mapped[int | None] = mapped_column(ForeignKey("ssh_profiles.id"), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(100), index=True)
    command_preview: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="running", index=True)
    exit_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    stdout: Mapped[str] = mapped_column(Text, default="")
    stderr: Mapped[str] = mapped_column(Text, default="")
    stdout_truncated: Mapped[bool] = mapped_column(Boolean, default=False)
    stderr_truncated: Mapped[bool] = mapped_column(Boolean, default=False)
    started_at: Mapped[datetime] = mapped_column(default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    warnings_json: Mapped[str] = mapped_column(Text, default="[]")
    analysis_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    analysis_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    analysis_status: Mapped[str | None] = mapped_column(String(32), nullable=True)

    run: Mapped[ActionRun] = relationship()
    host: Mapped[Host | None] = relationship()
    ssh_profile: Mapped[SshProfile | None] = relationship()

    @validates("status")
    def validate_status(self, key: str, value: str) -> str:
        if value not in ACTION_EXECUTION_STATUSES:
            raise ValueError("Unsupported action execution status")
        return value


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    event_type: Mapped[str] = mapped_column(String(100), index=True)
    details: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
