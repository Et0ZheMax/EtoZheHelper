from dataclasses import dataclass


@dataclass(frozen=True)
class ResolvedHost:
    id: int
    name: str
    hostname: str
    port: int
    os_family: str
    enabled: bool
    tags: tuple[str, ...]
    ssh_profile_id: int | None


@dataclass(frozen=True)
class ResolvedSshProfile:
    id: int
    name: str
    username: str
    auth_type: str
    key_ref: str | None
    password_ref: str | None
    sudo_mode: str


@dataclass(frozen=True)
class ExecutionReadiness:
    ready: bool
    run_id: int
    status: str
    action: str
    command_preview: str
    host: ResolvedHost | None
    ssh_profile: ResolvedSshProfile | None
    blockers: tuple[str, ...]
    warnings: tuple[str, ...]
    execution_enabled: bool = False
