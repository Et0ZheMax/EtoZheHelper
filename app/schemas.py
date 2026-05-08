from datetime import datetime

import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


SAFE_HOST_RE = re.compile(r"^[A-Za-z0-9_.:-]{1,253}$")
SAFE_NAME_RE = re.compile(r"^[A-Za-z0-9_.@:+ -]{1,120}$")
SAFE_OPERATOR_RE = re.compile(r"^[A-Za-z0-9 ._@-]{1,120}$")
SAFE_USERNAME_RE = re.compile(r"^[A-Za-z0-9_.@-]{1,128}$")
SAFE_TAG_RE = re.compile(r"^[A-Za-z0-9_.@:+-]{1,64}$")
ALLOWED_AUTH_TYPES = {"key", "password", "agent", "manual"}
ALLOWED_SUDO_MODES = {"none", "prompt", "nopasswd_limited"}
SECRET_FIELD_NAMES = {"password", "private_key", "token", "secret"}
REF_FORBIDDEN_RE = re.compile(r"[\r\n;|&<>$`\"']")
PEM_MARKERS = (
    "BEGIN PRIVATE KEY",
    "BEGIN OPENSSH PRIVATE KEY",
    "BEGIN RSA PRIVATE KEY",
    "-----BEGIN",
)
TOKEN_SEPARATOR_CHARS = set("/._:@+-")


def _trim(value: str | None) -> str | None:
    if value is None:
        return value
    return str(value).strip()


def _validate_safe_text(value: str, pattern: re.Pattern[str], field_name: str) -> str:
    text = str(value).strip()
    if not text:
        raise ValueError(f"{field_name} must not be empty")
    if not pattern.fullmatch(text):
        raise ValueError(f"{field_name} contains unsupported characters")
    return text


def _normalize_tags(value: list[str] | str | None) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        candidates = [item.strip() for item in value.split(",")]
    elif isinstance(value, list):
        candidates = [str(item).strip() for item in value]
    else:
        raise ValueError("tags must be a list of strings or comma-separated string")
    tags: list[str] = []
    for tag in candidates:
        if not tag:
            continue
        if not SAFE_TAG_RE.fullmatch(tag):
            raise ValueError("tags contain unsupported characters")
        if tag not in tags:
            tags.append(tag)
    return tags


def _reject_secret_extra_fields(data: Any) -> Any:
    if isinstance(data, dict):
        forbidden = SECRET_FIELD_NAMES.intersection(data)
        if forbidden:
            names = ", ".join(sorted(forbidden))
            raise ValueError(f"Secret fields are not accepted: {names}")
    return data


def _validate_non_secret_ref(value: str | None, field_name: str, max_length: int) -> str | None:
    text = _trim(value)
    if text is None or text == "":
        return None
    if len(text) > max_length:
        raise ValueError(f"{field_name} must be at most {max_length} characters")
    if REF_FORBIDDEN_RE.search(text):
        raise ValueError(f"{field_name} contains unsupported characters")
    upper_text = text.upper()
    if any(marker in upper_text for marker in PEM_MARKERS):
        raise ValueError(f"{field_name} must be a reference, not key material")
    if len(text) > 80 and not any(separator in text for separator in TOKEN_SEPARATOR_CHARS):
        raise ValueError(f"{field_name} looks like a secret blob; store a reference label only")
    return text


class HealthResponse(BaseModel):
    status: str
    app: str


class KbStatsResponse(BaseModel):
    documents_count: int
    knowledge_base_dir: str
    domains: dict[str, int] = Field(default_factory=dict)
    types: dict[str, int] = Field(default_factory=dict)
    risks: dict[str, int] = Field(default_factory=dict)
    tags: dict[str, int] = Field(default_factory=dict)


class KbReloadResponse(BaseModel):
    status: str
    documents_count: int


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=10_000)
    session_id: int | None = None


class Source(BaseModel):
    title: str
    path: str
    score: float
    snippet: str
    metadata: dict[str, object] = Field(default_factory=dict)


class ActionDefinitionResponse(BaseModel):
    key: str
    label: str
    description: str
    category: str
    risk: str
    read_only: bool
    requires_approval: bool
    needs_sudo: bool
    params_schema: dict[str, dict[str, object]] = Field(default_factory=dict)


class ActionCatalogResponse(BaseModel):
    items: list[ActionDefinitionResponse]


class ActionProposalRequest(BaseModel):
    action: str = Field(min_length=1, max_length=100)
    params: dict[str, object] = Field(default_factory=dict)
    session_id: int | None = None


class ActionProposalResponse(BaseModel):
    action: str
    label: str
    category: str
    risk: str
    read_only: bool
    requires_approval: bool
    needs_sudo: bool
    execution_enabled: bool
    command_preview: str
    params: dict[str, object] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)


class ActionRunPrepareRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: int | None = None
    host_id: int | None = None
    action: str = Field(min_length=1, max_length=100)
    params: dict[str, object] = Field(default_factory=dict)


def _validate_operator(value: str) -> str:
    return _validate_safe_text(value, SAFE_OPERATOR_RE, "operator")


def _validate_note(value: str | None) -> str | None:
    text = _trim(value)
    if text is None or text == "":
        return None
    if "<" in text or ">" in text:
        raise ValueError("note must be plain text")
    return text


class ActionRunApproveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    operator: str = Field(min_length=1, max_length=120)
    note: str | None = Field(default=None, max_length=1000)
    expires_in_minutes: int | None = Field(default=None, ge=1, le=1440)

    @model_validator(mode="before")
    @classmethod
    def reject_secret_fields(cls, data: Any) -> Any:
        return _reject_secret_extra_fields(data)

    @field_validator("operator")
    @classmethod
    def validate_operator(cls, value: str) -> str:
        return _validate_operator(value)

    @field_validator("note")
    @classmethod
    def validate_note(cls, value: str | None) -> str | None:
        return _validate_note(value)


class ActionRunRejectRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    operator: str = Field(min_length=1, max_length=120)
    note: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="before")
    @classmethod
    def reject_secret_fields(cls, data: Any) -> Any:
        return _reject_secret_extra_fields(data)

    @field_validator("operator")
    @classmethod
    def validate_operator(cls, value: str) -> str:
        return _validate_operator(value)

    @field_validator("note")
    @classmethod
    def validate_note(cls, value: str | None) -> str | None:
        return _validate_note(value)


class ActionRunExpireRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    operator: str = Field(default="system", min_length=1, max_length=120)
    note: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="before")
    @classmethod
    def reject_secret_fields(cls, data: Any) -> Any:
        return _reject_secret_extra_fields(data)

    @field_validator("operator")
    @classmethod
    def validate_operator(cls, value: str) -> str:
        return _validate_operator(value)

    @field_validator("note")
    @classmethod
    def validate_note(cls, value: str | None) -> str | None:
        return _validate_note(value)


class ActionRunResponse(BaseModel):
    id: int
    session_id: int | None = None
    host_id: int | None = None
    action: str
    category: str
    risk: str
    read_only: bool
    requires_approval: bool
    execution_enabled: bool
    status: str
    command_preview: str
    params: dict[str, object] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    approved_at: datetime | None = None
    rejected_at: datetime | None = None
    expired_at: datetime | None = None
    approval_note: str | None = None
    rejection_note: str | None = None
    expiration_note: str | None = None
    approved_by: str | None = None
    rejected_by: str | None = None
    expired_by: str | None = None
    expires_at: datetime | None = None
    created_at: datetime


class ActionRunExecuteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    operator: str = Field(min_length=1, max_length=120)

    @model_validator(mode="before")
    @classmethod
    def reject_secret_fields(cls, data: Any) -> Any:
        return _reject_secret_extra_fields(data)

    @field_validator("operator")
    @classmethod
    def validate_operator(cls, value: str) -> str:
        return _validate_operator(value)


class ActionExecutionResponse(BaseModel):
    id: int
    run_id: int
    host_id: int | None = None
    ssh_profile_id: int | None = None
    action: str
    command_preview: str
    status: str
    exit_code: int | None = None
    stdout: str
    stderr: str
    stdout_truncated: bool
    stderr_truncated: bool
    started_at: datetime
    finished_at: datetime | None = None
    duration_ms: int | None = None
    error: str | None = None
    error_category: str | None = None
    warnings: list[str] = Field(default_factory=list)
    analysis_status: str | None = None
    analysis_summary: str | None = None
    analysis: dict[str, object] | None = None


class ActionExecutionListResponse(BaseModel):
    items: list[ActionExecutionResponse]
    total: int
    limit: int
    offset: int


class ActionRunListResponse(BaseModel):
    items: list[ActionRunResponse]
    total: int
    limit: int
    offset: int


class ResolvedHostResponse(BaseModel):
    id: int
    name: str
    hostname: str
    port: int
    os_family: str
    enabled: bool
    tags: list[str] = Field(default_factory=list)
    ssh_profile_id: int | None = None


class ResolvedSshProfileResponse(BaseModel):
    id: int
    name: str
    username: str
    auth_type: str
    key_ref: str | None = None
    password_ref: str | None = None
    sudo_mode: str


class ExecutionReadinessResponse(BaseModel):
    ready: bool
    run_id: int
    status: str
    action: str
    command_preview: str
    execution_enabled: bool
    host: ResolvedHostResponse | None = None
    ssh_profile: ResolvedSshProfileResponse | None = None
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class ChatResponse(BaseModel):
    session_id: int
    answer: str
    sources: list[Source]
    actions: list[ActionProposalResponse] = Field(default_factory=list)


class KbDocumentSummary(BaseModel):
    path: str
    title: str
    domain: str | None = None
    doc_type: str | None = None
    risk: str | None = None
    tags: list[str] = Field(default_factory=list)
    snippet: str


class KbDocumentListResponse(BaseModel):
    items: list[KbDocumentSummary]
    total: int
    limit: int
    offset: int


class KbDocumentDetailResponse(BaseModel):
    path: str
    title: str
    content: str
    metadata: dict[str, object] = Field(default_factory=dict)
    headings: list[str] = Field(default_factory=list)


class ChatSessionSummary(BaseModel):
    id: int
    title: str
    created_at: datetime
    updated_at: datetime
    host_id: int | None = None
    messages_count: int
    preview: str


class ChatSessionListResponse(BaseModel):
    items: list[ChatSessionSummary]
    total: int
    limit: int
    offset: int


class ChatMessageResponse(BaseModel):
    id: int
    role: str
    content: str
    created_at: datetime


class ChatSessionDetailResponse(BaseModel):
    id: int
    title: str
    created_at: datetime
    updated_at: datetime
    host_id: int | None = None
    messages: list[ChatMessageResponse]


class ChatSessionCreateRequest(BaseModel):
    title: str | None = Field(default=None, max_length=120)

    @field_validator("title", mode="before")
    @classmethod
    def trim_title(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return str(value).strip()


class ChatSessionUpdateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=120)

    @field_validator("title", mode="before")
    @classmethod
    def trim_title(cls, value: str) -> str:
        return str(value).strip()


class ChatSessionResponse(BaseModel):
    id: int
    title: str
    created_at: datetime
    updated_at: datetime
    host_id: int | None = None


class ChatSessionHostUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    host_id: int | None = None


class ChatSessionDeleteResponse(BaseModel):
    status: str
    id: int


class DeleteResponse(BaseModel):
    status: str
    id: int


class HostBaseRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    hostname: str | None = None
    port: int | None = None
    os_family: str | None = None
    tags: list[str] = Field(default_factory=list)
    enabled: bool | None = None
    notes: str | None = None
    ssh_profile_id: int | None = None

    @model_validator(mode="before")
    @classmethod
    def reject_secret_fields(cls, data: Any) -> Any:
        return _reject_secret_extra_fields(data)

    @field_validator("name", mode="before")
    @classmethod
    def validate_name(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return _validate_safe_text(value, SAFE_NAME_RE, "name")

    @field_validator("hostname", mode="before")
    @classmethod
    def validate_hostname(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return _validate_safe_text(value, SAFE_HOST_RE, "hostname")

    @field_validator("port")
    @classmethod
    def validate_port(cls, value: int | None) -> int | None:
        if value is None:
            return value
        if value < 1 or value > 65535:
            raise ValueError("port must be between 1 and 65535")
        return value

    @field_validator("os_family", mode="before")
    @classmethod
    def validate_os_family(cls, value: str | None) -> str | None:
        if value is None:
            return value
        text = str(value).strip().casefold()
        if text != "linux":
            raise ValueError("os_family must be linux")
        return "linux"

    @field_validator("tags", mode="before")
    @classmethod
    def validate_tags(cls, value: list[str] | str | None) -> list[str]:
        return _normalize_tags(value)

    @field_validator("notes", mode="before")
    @classmethod
    def trim_notes(cls, value: str | None) -> str | None:
        return _trim(value)


class HostCreateRequest(HostBaseRequest):
    name: str
    hostname: str
    port: int = 22
    os_family: str = "linux"
    enabled: bool = True


class HostUpdateRequest(HostBaseRequest):
    pass


class HostResponse(BaseModel):
    id: int
    name: str
    hostname: str
    port: int
    os_family: str
    tags: list[str] = Field(default_factory=list)
    enabled: bool
    notes: str | None = None
    ssh_profile_id: int | None = None
    created_at: datetime
    updated_at: datetime


class HostListResponse(BaseModel):
    items: list[HostResponse]
    total: int
    limit: int
    offset: int


class SshProfileBaseRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    username: str | None = None
    auth_type: str | None = None
    key_ref: str | None = None
    password_ref: str | None = None
    sudo_mode: str | None = None

    @model_validator(mode="before")
    @classmethod
    def reject_secret_fields(cls, data: Any) -> Any:
        return _reject_secret_extra_fields(data)

    @field_validator("name", mode="before")
    @classmethod
    def validate_name(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return _validate_safe_text(value, SAFE_NAME_RE, "name")

    @field_validator("username", mode="before")
    @classmethod
    def validate_username(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return _validate_safe_text(value, SAFE_USERNAME_RE, "username")

    @field_validator("auth_type", mode="before")
    @classmethod
    def validate_auth_type(cls, value: str | None) -> str | None:
        if value is None:
            return value
        text = str(value).strip().casefold()
        if text not in ALLOWED_AUTH_TYPES:
            raise ValueError("auth_type must be one of key, password, agent, manual")
        return text

    @field_validator("sudo_mode", mode="before")
    @classmethod
    def validate_sudo_mode(cls, value: str | None) -> str | None:
        if value is None:
            return value
        text = str(value).strip().casefold()
        if text not in ALLOWED_SUDO_MODES:
            raise ValueError("sudo_mode must be one of none, prompt, nopasswd_limited")
        return text

    @field_validator("key_ref", mode="before")
    @classmethod
    def validate_key_ref(cls, value: str | None) -> str | None:
        return _validate_non_secret_ref(value, "key_ref", 500)

    @field_validator("password_ref", mode="before")
    @classmethod
    def validate_password_ref(cls, value: str | None) -> str | None:
        return _validate_non_secret_ref(value, "password_ref", 200)


class SshProfileCreateRequest(SshProfileBaseRequest):
    name: str
    username: str
    auth_type: str
    sudo_mode: str = "none"


class SshProfileUpdateRequest(SshProfileBaseRequest):
    pass


class SshProfileResponse(BaseModel):
    id: int
    name: str
    username: str
    auth_type: str
    key_ref: str | None = None
    password_ref: str | None = None
    sudo_mode: str
    created_at: datetime
    updated_at: datetime


class SshProfileListResponse(BaseModel):
    items: list[SshProfileResponse]
    total: int
    limit: int
    offset: int
