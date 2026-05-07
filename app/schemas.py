from datetime import datetime

import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


SAFE_HOST_RE = re.compile(r"^[A-Za-z0-9_.:-]{1,253}$")
SAFE_NAME_RE = re.compile(r"^[A-Za-z0-9_.@:+ -]{1,120}$")
SAFE_USERNAME_RE = re.compile(r"^[A-Za-z0-9_.@-]{1,128}$")
SAFE_TAG_RE = re.compile(r"^[A-Za-z0-9_.@:+-]{1,64}$")
ALLOWED_AUTH_TYPES = {"key", "password", "agent", "manual"}
ALLOWED_SUDO_MODES = {"none", "prompt", "nopasswd_limited"}
SECRET_FIELD_NAMES = {"password", "private_key", "token", "secret"}


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

    @field_validator("key_ref", "password_ref", mode="before")
    @classmethod
    def trim_refs(cls, value: str | None) -> str | None:
        return _trim(value)


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
