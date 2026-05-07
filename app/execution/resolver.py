import json

from sqlalchemy.orm import Session

from app.execution.models import ExecutionReadiness, ResolvedHost, ResolvedSshProfile
from app.models import ActionRun, Host, SshProfile

APPROVED_STATUS = "approved"
SUPPORTED_AUTH_TYPES = {"agent", "key", "manual", "password"}
SUPPORTED_SUDO_MODES = {"none", "prompt", "nopasswd_limited"}
STAGE_13_WARNING = "Stage 13 does not connect over SSH and does not execute commands."
EXECUTION_DISABLED_WARNING = "Execution remains disabled in Stage 13."
NOT_APPROVED_BLOCKER = "Action run must be approved before executor readiness can be checked."
NO_HOST_BLOCKER = "Approved run has no host_id. Select a host and prepare a host-targeted run."
HOST_NOT_FOUND_BLOCKER = "Referenced host was not found."
HOST_DISABLED_BLOCKER = "Referenced host is disabled."
NO_PROFILE_BLOCKER = "Host has no SSH profile assigned."
PROFILE_NOT_FOUND_BLOCKER = "Referenced SSH profile was not found."
EMPTY_PREVIEW_BLOCKER = "Prepared run has no command preview."
SUDO_PROMPT_WARNING = "Future executor may require an interactive sudo prompt."
SUDO_NOPASSWD_LIMITED_WARNING = "Future executor must enforce a limited sudo allowlist."


def _tags_from_json(value: str | None) -> tuple[str, ...]:
    if not value:
        return ()
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return tuple(item.strip() for item in value.split(",") if item.strip())
    if not isinstance(parsed, list):
        return ()
    return tuple(str(item) for item in parsed)


def _resolved_host(host: Host) -> ResolvedHost:
    return ResolvedHost(
        id=host.id,
        name=host.name,
        hostname=host.hostname,
        port=host.port,
        os_family=host.os_family,
        enabled=host.enabled,
        tags=_tags_from_json(host.tags),
        ssh_profile_id=host.ssh_profile_id,
    )


def _resolved_profile(profile: SshProfile) -> ResolvedSshProfile:
    return ResolvedSshProfile(
        id=profile.id,
        name=profile.name,
        username=profile.username,
        auth_type=profile.auth_type,
        key_ref=profile.key_ref,
        password_ref=profile.password_ref,
        sudo_mode=profile.sudo_mode,
    )


def resolve_action_run_readiness(db: Session, run_id: int) -> ExecutionReadiness:
    run = db.get(ActionRun, run_id)
    if run is None:
        raise LookupError("Action run not found")

    blockers: list[str] = []
    warnings = [STAGE_13_WARNING]
    host_context: ResolvedHost | None = None
    profile_context: ResolvedSshProfile | None = None

    if run.execution_enabled:
        warnings.append(EXECUTION_DISABLED_WARNING)

    command_preview = (run.command_preview or "").strip()
    if not command_preview:
        blockers.append(EMPTY_PREVIEW_BLOCKER)

    if run.status != APPROVED_STATUS:
        blockers.append(NOT_APPROVED_BLOCKER)
        return ExecutionReadiness(
            ready=False,
            run_id=run.id,
            status=run.status,
            action=run.action,
            command_preview=run.command_preview or "",
            host=None,
            ssh_profile=None,
            blockers=tuple(blockers),
            warnings=tuple(warnings),
            execution_enabled=False,
        )

    if run.host_id is None:
        blockers.append(NO_HOST_BLOCKER)
    else:
        host = db.get(Host, run.host_id)
        if host is None:
            blockers.append(HOST_NOT_FOUND_BLOCKER)
        else:
            host_context = _resolved_host(host)
            if not host.enabled:
                blockers.append(HOST_DISABLED_BLOCKER)
            if host.os_family != "linux":
                blockers.append("Referenced host os_family must be linux.")
            if host.port < 1 or host.port > 65535:
                blockers.append("Referenced host port must be between 1 and 65535.")
            if host.ssh_profile_id is None:
                blockers.append(NO_PROFILE_BLOCKER)
            else:
                profile = db.get(SshProfile, host.ssh_profile_id)
                if profile is None:
                    blockers.append(PROFILE_NOT_FOUND_BLOCKER)
                else:
                    profile_context = _resolved_profile(profile)
                    if profile.auth_type not in SUPPORTED_AUTH_TYPES:
                        blockers.append("SSH profile auth_type is not supported for readiness.")
                    elif profile.auth_type == "key" and not profile.key_ref:
                        blockers.append("SSH profile key auth requires key_ref metadata.")
                    elif profile.auth_type == "password" and not profile.password_ref:
                        blockers.append("SSH profile password auth requires password_ref metadata.")

                    if profile.sudo_mode not in SUPPORTED_SUDO_MODES:
                        blockers.append("SSH profile sudo_mode is not supported for readiness.")
                    elif profile.sudo_mode == "prompt":
                        warnings.append(SUDO_PROMPT_WARNING)
                    elif profile.sudo_mode == "nopasswd_limited":
                        warnings.append(SUDO_NOPASSWD_LIMITED_WARNING)

    return ExecutionReadiness(
        ready=not blockers,
        run_id=run.id,
        status=run.status,
        action=run.action,
        command_preview=run.command_preview or "",
        host=host_context,
        ssh_profile=profile_context,
        blockers=tuple(blockers),
        warnings=tuple(warnings),
        execution_enabled=False,
    )
