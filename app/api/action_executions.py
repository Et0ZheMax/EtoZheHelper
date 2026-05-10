from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.audit.logger import log_event
from app.db import get_db
from app.execution.analysis import analyze_execution_output, parse_analysis_json
from app.execution.executor import warnings_from_json
from app.models import ActionExecution, ActionRun, ChatMessage, ChatSession, Host, utcnow
from app.schemas import (
    ActionExecutionAnalyzeRequest,
    ActionExecutionAnalyzeResponse,
    ActionExecutionAttachRequest,
    ActionExecutionAttachResponse,
    ActionExecutionDetailResponse,
)

router = APIRouter(prefix="/action-executions", tags=["action-executions"])

MAX_CHAT_OUTPUT_CHARS = 6000
MAX_ANALYZER_INPUT_CHARS = 20000
MAX_ANALYSIS_SUMMARY_CHARS = 4000
TRUNCATED_CHAT_NOTICE = "[output truncated for chat; full output remains in execution detail]"
TRUNCATED_ANALYSIS_NOTICE = "[output truncated for analysis; full output remains in execution detail]"


def _cap_text(value: str | None, limit: int, notice: str) -> tuple[str, bool]:
    text = value or ""
    if len(text) <= limit:
        return text, False
    return text[:limit].rstrip() + f"\n\n{notice}", True


def _execution_or_404(db: Session, execution_id: int) -> ActionExecution:
    execution = db.get(ActionExecution, execution_id)
    if execution is None:
        raise HTTPException(status_code=404, detail="Action execution not found")
    return execution


def _linked_run_and_session_or_error(db: Session, execution: ActionExecution) -> tuple[ActionRun, ChatSession]:
    run = db.get(ActionRun, execution.run_id)
    if run is None:
        raise HTTPException(status_code=409, detail="Execution is not linked to an action run")
    if run.session_id is None:
        raise HTTPException(status_code=409, detail="Execution is not linked to an investigation session")
    session = db.get(ChatSession, run.session_id)
    if session is None:
        raise HTTPException(status_code=409, detail="Execution is not linked to an investigation session")
    return run, session


def _host_name(db: Session, execution: ActionExecution, run: ActionRun | None = None) -> str | None:
    if execution.host is not None:
        return execution.host.name
    host_id = execution.host_id or (run.host_id if run is not None else None)
    if host_id is None:
        return None
    host = db.get(Host, host_id)
    return host.name if host is not None else None


def _execution_response(db: Session, execution: ActionExecution) -> ActionExecutionDetailResponse:
    run = db.get(ActionRun, execution.run_id)
    return ActionExecutionDetailResponse(
        id=execution.id,
        run_id=execution.run_id,
        session_id=run.session_id if run is not None else None,
        host_id=execution.host_id,
        host_name=_host_name(db, execution, run),
        ssh_profile_id=execution.ssh_profile_id,
        action=execution.action,
        command_preview=execution.command_preview,
        status=execution.status,
        exit_code=execution.exit_code,
        stdout=execution.stdout,
        stderr=execution.stderr,
        stdout_truncated=execution.stdout_truncated,
        stderr_truncated=execution.stderr_truncated,
        started_at=execution.started_at,
        finished_at=execution.finished_at,
        duration_ms=execution.duration_ms,
        error=execution.error,
        error_category=execution.error_category,
        warnings=warnings_from_json(execution.warnings_json),
        analysis_status=execution.analysis_status,
        analysis_summary=execution.analysis_summary,
        analysis_attached_at=execution.analysis_attached_at,
        chat_attached_at=execution.chat_attached_at,
        analysis=parse_analysis_json(execution.analysis_json),
    )


def _status_for_chat(execution: ActionExecution) -> str:
    return "success" if execution.status == "completed" and execution.exit_code == 0 else execution.status


def _base_execution_lines(db: Session, execution: ActionExecution, run: ActionRun) -> list[str]:
    host_name = _host_name(db, execution, run) or "unknown"
    exit_code = "none" if execution.exit_code is None else str(execution.exit_code)
    duration = "unknown" if execution.duration_ms is None else f"{execution.duration_ms} ms"
    command = execution.command_preview or run.command_preview or ""
    return [
        f"Host: {host_name}  ",
        f"Action: {execution.action}  ",
        f"Status: {_status_for_chat(execution)}  ",
        f"Exit code: {exit_code}  ",
        f"Duration: {duration}  ",
        f"Command preview: `{command}`",
    ]


def _attach_message(db: Session, execution: ActionExecution, run: ActionRun, payload: ActionExecutionAttachRequest) -> str:
    lines = ["### Read-only SSH check attached", "", *_base_execution_lines(db, execution, run), "", f"Operator: {payload.operator}  "]
    if payload.note:
        lines.append(f"Note: {payload.note}")
        lines.append("")
    if payload.include_stdout and execution.stdout:
        stdout, truncated = _cap_text(execution.stdout, MAX_CHAT_OUTPUT_CHARS, TRUNCATED_CHAT_NOTICE)
        lines.extend(["#### Stdout", "", "```text", stdout, "```"])
        if truncated:
            lines.append("")
    else:
        lines.append('Stdout is stored in execution detail. Use "View raw" for full output.')
    if payload.include_stdout and execution.stderr:
        stderr, _ = _cap_text(execution.stderr, MAX_CHAT_OUTPUT_CHARS, TRUNCATED_CHAT_NOTICE)
        lines.extend(["", "#### Stderr", "", "```text", stderr, "```"])
    if not execution.stdout and not execution.stderr:
        lines.append("")
        lines.append("No stdout/stderr captured for this execution.")
    return "\n".join(lines).strip()


def _bounded_analyzer_input(db: Session, execution: ActionExecution, run: ActionRun) -> tuple[str, bool]:
    host_name = _host_name(db, execution, run) or "unknown"
    raw = "\n".join(
        [
            f"Host: {host_name}",
            f"Action: {execution.action}",
            f"Command preview: {execution.command_preview or run.command_preview or ''}",
            f"Execution status: {execution.status}, exit code {execution.exit_code}",
            "",
            "STDOUT:",
            execution.stdout or "",
            "",
            "STDERR:",
            execution.stderr or "",
        ]
    )
    if len(raw) <= MAX_ANALYZER_INPUT_CHARS:
        return raw, False
    half = (MAX_ANALYZER_INPUT_CHARS - len(TRUNCATED_ANALYSIS_NOTICE) - 4) // 2
    return f"{raw[:half].rstrip()}\n\n{TRUNCATED_ANALYSIS_NOTICE}\n\n{raw[-half:].lstrip()}", True


def _analysis_message(db: Session, execution: ActionExecution, run: ActionRun, operator: str, note: str | None, truncated: bool) -> str:
    lines = [
        "### Analysis of read-only SSH check",
        "",
        *_base_execution_lines(db, execution, run),
        "",
        f"Operator: {operator}  ",
    ]
    if note:
        lines.append(f"Note: {note}")
    if truncated:
        lines.extend(["", TRUNCATED_ANALYSIS_NOTICE])

    analysis = parse_analysis_json(execution.analysis_json) or {}
    findings = analysis.get("findings") if isinstance(analysis.get("findings"), list) else []
    hypotheses = analysis.get("hypotheses") if isinstance(analysis.get("hypotheses"), list) else []
    next_checks = analysis.get("next_checks") if isinstance(analysis.get("next_checks"), list) else []

    lines.extend(["", "#### Findings"])
    if findings:
        for finding in findings:
            if not isinstance(finding, dict):
                continue
            severity = finding.get("severity") or "info"
            title = finding.get("title") or "Finding"
            lines.append(f"- {severity}: {title}")
            if finding.get("evidence"):
                lines.append(f"  Evidence: {finding['evidence']}")
            if finding.get("interpretation"):
                lines.append(f"  Interpretation: {finding['interpretation']}")
            steps = finding.get("next_steps") if isinstance(finding.get("next_steps"), list) else []
            if steps:
                lines.append("  Next checks:")
                for step in steps[:10]:
                    lines.append(f"  - {step}")
    elif execution.analysis_summary:
        lines.append(f"- {execution.analysis_summary}")
    else:
        lines.append("- No actionable findings detected.")

    if hypotheses:
        lines.extend(["", "#### Hypotheses"])
        for item in hypotheses[:10]:
            lines.append(f"- {item}")
    if next_checks:
        lines.extend(["", "#### Next safe checks"])
        for item in next_checks[:10]:
            lines.append(f"- `{item}`")
    return "\n".join(lines).strip()


def _append_assistant_message(db: Session, session: ChatSession, content: str) -> ChatMessage:
    message = ChatMessage(session_id=session.id, role="assistant", content=content)
    session.updated_at = utcnow()
    db.add(message)
    db.add(session)
    db.commit()
    db.refresh(message)
    return message


@router.get("/{execution_id}", response_model=ActionExecutionDetailResponse)
def get_action_execution(execution_id: int, db: Session = Depends(get_db)) -> ActionExecutionDetailResponse:
    return _execution_response(db, _execution_or_404(db, execution_id))


@router.post("/{execution_id}/attach", response_model=ActionExecutionAttachResponse)
def attach_action_execution(
    execution_id: int, payload: ActionExecutionAttachRequest, db: Session = Depends(get_db)
) -> ActionExecutionAttachResponse:
    execution = _execution_or_404(db, execution_id)
    run, session = _linked_run_and_session_or_error(db, execution)
    message = _append_assistant_message(db, session, _attach_message(db, execution, run, payload))
    execution.chat_attached_at = utcnow()
    db.add(execution)
    db.commit()
    db.refresh(execution)
    log_event(
        db,
        "action_execution_attached",
        {"execution_id": execution.id, "run_id": run.id, "session_id": session.id, "message_id": message.id, "operator": payload.operator},
    )
    return ActionExecutionAttachResponse(
        execution_id=execution.id,
        session_id=session.id,
        message_id=message.id,
        chat_attached_at=execution.chat_attached_at,
    )


@router.post("/{execution_id}/analyze", response_model=ActionExecutionAnalyzeResponse)
def analyze_action_execution(
    execution_id: int, payload: ActionExecutionAnalyzeRequest, db: Session = Depends(get_db)
) -> ActionExecutionAnalyzeResponse:
    execution = _execution_or_404(db, execution_id)
    run, session = _linked_run_and_session_or_error(db, execution)
    analyzer_input, truncated = _bounded_analyzer_input(db, execution, run)
    analysis = analyze_execution_output(analyzer_input, "")
    execution.analysis_status = analysis.status
    execution.analysis_json = analysis.analysis_json
    execution.analysis_summary = (analysis.summary or "")[:MAX_ANALYSIS_SUMMARY_CHARS] or None
    execution.analysis_attached_at = utcnow()
    db.add(execution)
    db.commit()
    db.refresh(execution)

    message = _append_assistant_message(db, session, _analysis_message(db, execution, run, payload.operator, payload.note, truncated))
    log_event(
        db,
        "action_execution_analyzed",
        {
            "execution_id": execution.id,
            "run_id": run.id,
            "session_id": session.id,
            "message_id": message.id,
            "operator": payload.operator,
            "analysis_status": execution.analysis_status,
        },
    )
    return ActionExecutionAnalyzeResponse(
        execution_id=execution.id,
        session_id=session.id,
        message_id=message.id,
        analysis_attached_at=execution.analysis_attached_at,
        analysis_status=execution.analysis_status,
        analysis_summary=execution.analysis_summary,
    )
