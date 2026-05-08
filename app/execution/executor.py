from __future__ import annotations

import json
import re
from datetime import datetime

from sqlalchemy.orm import Session

from app.actions.catalog import get_action_definition
from app.audit.logger import log_event
from app.execution.resolver import resolve_action_run_readiness
from app.execution.ssh_client import DefaultSshClient, SshClientProtocol
from app.models import ActionExecution, ActionRun, utcnow

CONNECT_TIMEOUT_SECONDS = 8
COMMAND_TIMEOUT_SECONDS = 20
MAX_STDOUT_BYTES = 64 * 1024
MAX_STDERR_BYTES = 32 * 1024
MAX_SAFE_ERROR_TEXT = 500
SECRET_LIKE_RE = re.compile(r"(?i)(password|passwd|token|secret|private[_ -]?key|-----begin)")
EXECUTION_WARNINGS = [
    "Executed over SSH using agent auth.",
    "Only approved read-only ActionRuns can be executed.",
]


class ActionExecutionBlockedError(Exception):
    def __init__(self, execution: ActionExecution, blockers: list[str]):
        super().__init__("; ".join(blockers))
        self.execution = execution
        self.blockers = blockers


def _decode_limited(data: bytes, limit: int) -> tuple[str, bool]:
    truncated = len(data) > limit
    limited = data[:limit]
    return limited.decode("utf-8", errors="replace"), truncated


def _warnings_json(warnings: list[str]) -> str:
    return json.dumps(warnings, ensure_ascii=False)


def warnings_from_json(value: str | None) -> list[str]:
    if not value:
        return []
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return []
    return [str(item) for item in parsed] if isinstance(parsed, list) else []


def _duration_ms(started_at: datetime, finished_at: datetime) -> int:
    if started_at.tzinfo is None and finished_at.tzinfo is not None:
        finished_at = finished_at.replace(tzinfo=None)
    elif started_at.tzinfo is not None and finished_at.tzinfo is None:
        started_at = started_at.replace(tzinfo=None)
    return max(0, int((finished_at - started_at).total_seconds() * 1000))


def _create_execution(db: Session, run: ActionRun, status: str, warnings: list[str]) -> ActionExecution:
    execution = ActionExecution(
        run_id=run.id,
        host_id=run.host_id,
        ssh_profile_id=run.host.ssh_profile_id if run.host is not None else None,
        action=run.action,
        command_preview=run.command_preview or "",
        status=status,
        exit_code=None,
        stdout="",
        stderr="",
        stdout_truncated=False,
        stderr_truncated=False,
        started_at=utcnow(),
        finished_at=None,
        duration_ms=None,
        error=None,
        error_category=None,
        warnings_json=_warnings_json(warnings),
    )
    db.add(execution)
    db.commit()
    db.refresh(execution)
    return execution


def _finish_execution(
    db: Session,
    execution: ActionExecution,
    status: str,
    *,
    exit_code: int | None = None,
    stdout: str = "",
    stderr: str = "",
    stdout_truncated: bool = False,
    stderr_truncated: bool = False,
    error: str | None = None,
    error_category: str | None = None,
    warnings: list[str] | None = None,
) -> ActionExecution:
    finished_at = utcnow()
    execution.status = status
    execution.exit_code = exit_code
    execution.stdout = stdout
    execution.stderr = stderr
    execution.stdout_truncated = stdout_truncated
    execution.stderr_truncated = stderr_truncated
    execution.finished_at = finished_at
    execution.duration_ms = _duration_ms(execution.started_at, finished_at)
    execution.error = error
    execution.error_category = error_category
    if warnings is not None:
        execution.warnings_json = _warnings_json(warnings)
    db.commit()
    db.refresh(execution)
    return execution


def _block(db: Session, run: ActionRun, blockers: list[str], warnings: list[str] | None = None) -> None:
    all_warnings = list(warnings or []) + blockers
    execution = _create_execution(db, run, "blocked", all_warnings)
    _finish_execution(
        db,
        execution,
        "blocked",
        error="; ".join(blockers),
        error_category="blocked",
        warnings=all_warnings,
    )
    log_event(
        db,
        "action_execution_blocked",
        {"execution_id": execution.id, "run_id": run.id, "blockers": blockers, "action": run.action},
    )
    raise ActionExecutionBlockedError(execution, blockers)


def _sanitize_error_text(text: str) -> str:
    cleaned = " ".join(str(text).replace("\r", " ").replace("\n", " ").split())
    if not cleaned:
        return "SSH execution failed."
    if SECRET_LIKE_RE.search(cleaned):
        return "SSH execution failed with a redacted error message."
    return cleaned[:MAX_SAFE_ERROR_TEXT]


def classify_ssh_error(exc: Exception) -> tuple[str, str]:
    class_name = exc.__class__.__name__.casefold()
    raw_text = str(exc).strip() or exc.__class__.__name__
    text = raw_text.casefold()

    if "badhostkey" in class_name or "hostkey" in class_name or "host key" in text or "known_hosts" in text:
        return (
            "SSH host key is not trusted. Connect once with system ssh from this user or add host key to known_hosts.",
            "host_key_rejected",
        )
    if "auth" in class_name or "authentication" in text or "permission denied" in text:
        return "SSH authentication failed. Check ssh-agent key availability and username.", "auth_failed"
    if "timeout" in class_name or "timed out" in text or "timeout" in text:
        return "SSH connection or command timed out.", "timeout"
    if "gaierror" in class_name or "name or service" in text or "temporary failure in name resolution" in text or "dns" in text:
        return "SSH connection failed. Check hostname, network path and port.", "dns_failed"
    if (
        "connection" in text
        or "refused" in text
        or "unreachable" in text
        or "no route" in text
        or "network" in text
        or "socket" in class_name
    ):
        return "SSH connection failed. Check hostname, network path and port.", "connection_failed"
    if "ssh" in class_name or "ssh" in text:
        return _sanitize_error_text(raw_text), "ssh_failed"
    return _sanitize_error_text(raw_text), "unknown"


def _validate_action_is_executable(action_key: str) -> list[str]:
    definition = get_action_definition(action_key)
    if definition is None:
        return ["Action is no longer present in the allowlisted catalog."]
    blockers: list[str] = []
    if not definition.read_only:
        blockers.append("Action is no longer marked read-only in the allowlisted catalog.")
    if definition.risk != "low":
        blockers.append("Action is no longer low risk in the allowlisted catalog.")
    if not definition.requires_approval:
        blockers.append("Action no longer requires approval in the allowlisted catalog.")
    return blockers


def execute_approved_action_run(
    db: Session,
    run_id: int,
    operator: str,
    ssh_client: SshClientProtocol | None = None,
) -> ActionExecution:
    run = db.get(ActionRun, run_id)
    if run is None:
        raise LookupError("Action run not found")

    if run.status != "approved":
        _block(db, run, [f"Action run must be approved before execution. Current status: {run.status}."])

    readiness = resolve_action_run_readiness(db, run_id)
    if not readiness.ready:
        _block(db, run, list(readiness.blockers), list(readiness.warnings))
    if readiness.host is None or readiness.ssh_profile is None:
        _block(db, run, ["Readiness did not resolve host and SSH profile metadata."])

    action_blockers = _validate_action_is_executable(run.action)
    if action_blockers:
        _block(db, run, action_blockers, list(readiness.warnings))

    if readiness.ssh_profile.auth_type == "manual":
        _block(db, run, ["Manual auth is not executable in Stage 14. Use agent auth or a future interactive connector."])
    if readiness.ssh_profile.auth_type == "key":
        _block(db, run, ["Key auth execution is not implemented in Stage 14 because key_ref is metadata only."])
    if readiness.ssh_profile.auth_type == "password":
        _block(db, run, ["Password auth execution is not implemented in Stage 14 because password_ref is metadata only."])
    if readiness.ssh_profile.auth_type != "agent":
        _block(db, run, ["Only SSH agent auth is executable in Stage 14."])

    if readiness.ssh_profile.sudo_mode == "prompt":
        _block(db, run, ["Interactive sudo prompt is not supported in Stage 14."])
    if readiness.ssh_profile.sudo_mode == "nopasswd_limited":
        _block(db, run, ["NOPASSWD limited sudo execution is not implemented in Stage 14."])
    if readiness.ssh_profile.sudo_mode != "none":
        _block(db, run, ["Only sudo_mode=none is executable in Stage 14."])

    command = run.command_preview or ""
    warnings = EXECUTION_WARNINGS + list(readiness.warnings)
    execution = _create_execution(db, run, "running", warnings)
    log_event(
        db,
        "action_execution_started",
        {
            "execution_id": execution.id,
            "run_id": run.id,
            "host_id": readiness.host.id,
            "ssh_profile_id": readiness.ssh_profile.id,
            "action": run.action,
            "operator": operator,
        },
    )

    client = ssh_client or DefaultSshClient()
    try:
        result = client.run_command(
            hostname=readiness.host.hostname,
            port=readiness.host.port,
            username=readiness.ssh_profile.username,
            command=command,
            connect_timeout=CONNECT_TIMEOUT_SECONDS,
            command_timeout=COMMAND_TIMEOUT_SECONDS,
        )
    except Exception as exc:
        error, error_category = classify_ssh_error(exc)
        execution = _finish_execution(
            db, execution, "failed", error=error, error_category=error_category, warnings=warnings
        )
        log_event(
            db,
            "action_execution_failed",
            {
                "execution_id": execution.id,
                "run_id": run.id,
                "action": run.action,
                "error": error,
                "error_category": execution.error_category,
            },
        )
        return execution

    stdout, stdout_truncated = _decode_limited(result.stdout, MAX_STDOUT_BYTES)
    stderr, stderr_truncated = _decode_limited(result.stderr, MAX_STDERR_BYTES)
    final_warnings = list(warnings)
    if stdout_truncated:
        final_warnings.append(f"stdout exceeded {MAX_STDOUT_BYTES} bytes and was truncated.")
    if stderr_truncated:
        final_warnings.append(f"stderr exceeded {MAX_STDERR_BYTES} bytes and was truncated.")

    if result.timed_out:
        status = "timed_out"
        event_type = "action_execution_timed_out"
        error = f"SSH command timed out after {COMMAND_TIMEOUT_SECONDS} seconds."
        error_category = "timeout"
    elif result.exit_code == 0:
        status = "completed"
        event_type = "action_execution_completed"
        error = None
        error_category = None
    else:
        status = "failed"
        event_type = "action_execution_failed"
        error = None
        error_category = None

    execution = _finish_execution(
        db,
        execution,
        status,
        exit_code=result.exit_code,
        stdout=stdout,
        stderr=stderr,
        stdout_truncated=stdout_truncated,
        stderr_truncated=stderr_truncated,
        error=error,
        error_category=error_category,
        warnings=final_warnings,
    )
    log_event(
        db,
        event_type,
        {
            "execution_id": execution.id,
            "run_id": run.id,
            "action": run.action,
            "exit_code": execution.exit_code,
            "duration_ms": execution.duration_ms,
            "error_category": execution.error_category,
        },
    )
    return execution
