import json
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.actions.models import ActionRequest
from app.actions.policy import InvalidActionParamsError, UnknownActionError, propose_action
from app.audit.logger import log_event
from app.db import get_db
from app.execution.analysis import parse_analysis_json
from app.execution.executor import ActionExecutionBlockedError, execute_approved_action_run, warnings_from_json
from app.execution.models import ExecutionReadiness
from app.execution.resolver import resolve_action_run_readiness
from app.models import ACTION_RUN_STATUSES, ActionExecution, ActionRun, ChatSession, Host, utcnow
from app.schemas import (
    ActionExecutionListResponse,
    ActionExecutionResponse,
    ActionRunApproveRequest,
    ActionRunExpireRequest,
    ActionRunListResponse,
    ActionRunExecuteRequest,
    ActionRunPrepareRequest,
    ActionRunRejectRequest,
    ActionRunResponse,
    ExecutionReadinessResponse,
    ResolvedHostResponse,
    ResolvedSshProfileResponse,
)

router = APIRouter(prefix="/action-runs", tags=["action-runs"])

STAGE_11_WARNING = "Stage 11 prepares runs only. No command was executed."
STAGE_12_APPROVAL_WARNING = "Approval is metadata only in Stage 12. No command was executed."
NO_EXECUTION_WARNING = "No command was executed."
HISTORICAL_VALIDATION_WARNING = (
    "Stored run references an action or params that no longer validate against the current catalog. "
    "Showing stored preview only."
)
SESSION_HOST_MISMATCH_WARNING = (
    "The provided host_id differs from the chat session host context; the explicit host_id was used for this prepared run."
)
PREPARED_STATUS = "prepared"
APPROVED_STATUS = "approved"
REJECTED_STATUS = "rejected"
EXPIRED_STATUS = "expired"
EXECUTION_ENABLED = False


def _params_from_json(value: str | None) -> dict[str, object]:
    if not value:
        return {}
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _run_response(run: ActionRun, warnings: list[str] | None = None) -> ActionRunResponse:
    stored_params = _params_from_json(run.params_json)
    response_warnings = list(warnings) if warnings is not None else [STAGE_11_WARNING]
    try:
        proposal = propose_action(run.action, stored_params)
        read_only = proposal.read_only
        requires_approval = proposal.requires_approval
        params = proposal.params
    except (UnknownActionError, InvalidActionParamsError):
        read_only = True
        requires_approval = True
        params = stored_params
        if HISTORICAL_VALIDATION_WARNING not in response_warnings:
            response_warnings.append(HISTORICAL_VALIDATION_WARNING)

    return ActionRunResponse(
        id=run.id,
        session_id=run.session_id,
        host_id=run.host_id,
        action=run.action,
        category=run.category,
        risk=run.risk,
        read_only=read_only,
        requires_approval=requires_approval,
        execution_enabled=False,
        status=run.status,
        command_preview=run.command_preview,
        params=params,
        warnings=response_warnings,
        approved_at=run.approved_at,
        rejected_at=run.rejected_at,
        expired_at=run.expired_at,
        approval_note=run.approval_note,
        rejection_note=run.rejection_note,
        expiration_note=run.expiration_note,
        approved_by=run.approved_by,
        rejected_by=run.rejected_by,
        expired_by=run.expired_by,
        expires_at=run.expires_at,
        created_at=run.created_at,
    )


def _readiness_response(readiness: ExecutionReadiness) -> ExecutionReadinessResponse:
    host = None
    if readiness.host is not None:
        host = ResolvedHostResponse(
            id=readiness.host.id,
            name=readiness.host.name,
            hostname=readiness.host.hostname,
            port=readiness.host.port,
            os_family=readiness.host.os_family,
            enabled=readiness.host.enabled,
            tags=list(readiness.host.tags),
            ssh_profile_id=readiness.host.ssh_profile_id,
        )
    ssh_profile = None
    if readiness.ssh_profile is not None:
        ssh_profile = ResolvedSshProfileResponse(
            id=readiness.ssh_profile.id,
            name=readiness.ssh_profile.name,
            username=readiness.ssh_profile.username,
            auth_type=readiness.ssh_profile.auth_type,
            key_ref=readiness.ssh_profile.key_ref,
            password_ref=readiness.ssh_profile.password_ref,
            sudo_mode=readiness.ssh_profile.sudo_mode,
        )
    return ExecutionReadinessResponse(
        ready=readiness.ready,
        run_id=readiness.run_id,
        status=readiness.status,
        action=readiness.action,
        command_preview=readiness.command_preview,
        execution_enabled=False,
        host=host,
        ssh_profile=ssh_profile,
        blockers=list(readiness.blockers),
        warnings=list(readiness.warnings),
    )


def _execution_response(execution: ActionExecution) -> ActionExecutionResponse:
    return ActionExecutionResponse(
        id=execution.id,
        run_id=execution.run_id,
        host_id=execution.host_id,
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
        analysis=parse_analysis_json(execution.analysis_json),
    )


def _run_or_404(db: Session, run_id: int) -> ActionRun:
    run = db.get(ActionRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Action run not found")
    return run


def _ensure_status(run: ActionRun, allowed: set[str], action_label: str) -> None:
    if run.status not in allowed:
        allowed_text = ", ".join(sorted(allowed))
        raise HTTPException(
            status_code=409,
            detail=f"Action run cannot be {action_label} from status '{run.status}'. Allowed from: {allowed_text}.",
        )


def _force_no_execution(run: ActionRun) -> None:
    run.execution_enabled = EXECUTION_ENABLED


@router.post("/prepare", response_model=ActionRunResponse)
def prepare_action_run(payload: ActionRunPrepareRequest, db: Session = Depends(get_db)) -> ActionRunResponse:
    session = None
    if payload.session_id is not None:
        session = db.get(ChatSession, payload.session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="Chat session not found")

    host = None
    if payload.host_id is not None:
        host = db.get(Host, payload.host_id)
        if host is None:
            raise HTTPException(status_code=404, detail="Host not found")
        if not host.enabled:
            raise HTTPException(status_code=422, detail="Host is disabled")

    try:
        request = ActionRequest(action=payload.action, params=payload.params, session_id=payload.session_id)
        proposal = propose_action(request.action, request.params)
    except UnknownActionError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except InvalidActionParamsError as exc:
        raise HTTPException(status_code=422, detail=exc.errors) from exc

    warnings = [STAGE_11_WARNING]
    if session is not None and payload.host_id is not None and session.host_id is not None and session.host_id != payload.host_id:
        warnings.append(SESSION_HOST_MISMATCH_WARNING)

    run = ActionRun(
        session_id=payload.session_id,
        host_id=payload.host_id,
        action=proposal.action,
        category=proposal.category,
        risk=proposal.risk,
        command_preview=proposal.command_preview,
        params_json=json.dumps(proposal.params, ensure_ascii=False, sort_keys=True),
        status=PREPARED_STATUS,
        execution_enabled=EXECUTION_ENABLED,
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    log_event(
        db,
        "action_run_prepared",
        {
            "run_id": run.id,
            "session_id": run.session_id,
            "host_id": run.host_id,
            "action": run.action,
            "category": run.category,
            "risk": run.risk,
            "execution_enabled": run.execution_enabled,
        },
    )
    return _run_response(run, warnings=warnings)


@router.post("/{run_id}/approve", response_model=ActionRunResponse)
def approve_action_run(
    run_id: int, payload: ActionRunApproveRequest, db: Session = Depends(get_db)
) -> ActionRunResponse:
    run = _run_or_404(db, run_id)
    _ensure_status(run, {PREPARED_STATUS}, "approved")
    now = utcnow()
    run.status = APPROVED_STATUS
    run.approved_at = now
    run.approved_by = payload.operator
    run.approval_note = payload.note
    run.expires_at = now + timedelta(minutes=payload.expires_in_minutes) if payload.expires_in_minutes is not None else None
    _force_no_execution(run)
    db.commit()
    db.refresh(run)
    log_event(
        db,
        "action_run_approved",
        {
            "run_id": run.id,
            "operator": payload.operator,
            "expires_at": run.expires_at.isoformat() if run.expires_at else None,
            "execution_enabled": run.execution_enabled,
        },
    )
    return _run_response(run, warnings=[STAGE_12_APPROVAL_WARNING])


@router.post("/{run_id}/reject", response_model=ActionRunResponse)
def reject_action_run(
    run_id: int, payload: ActionRunRejectRequest, db: Session = Depends(get_db)
) -> ActionRunResponse:
    run = _run_or_404(db, run_id)
    _ensure_status(run, {PREPARED_STATUS, APPROVED_STATUS}, "rejected")
    run.status = REJECTED_STATUS
    run.rejected_at = utcnow()
    run.rejected_by = payload.operator
    run.rejection_note = payload.note
    _force_no_execution(run)
    db.commit()
    db.refresh(run)
    log_event(
        db,
        "action_run_rejected",
        {"run_id": run.id, "operator": payload.operator, "execution_enabled": run.execution_enabled},
    )
    return _run_response(run, warnings=[NO_EXECUTION_WARNING])


@router.post("/{run_id}/expire", response_model=ActionRunResponse)
def expire_action_run(
    run_id: int, payload: ActionRunExpireRequest, db: Session = Depends(get_db)
) -> ActionRunResponse:
    run = _run_or_404(db, run_id)
    _ensure_status(run, {PREPARED_STATUS, APPROVED_STATUS}, "expired")
    run.status = EXPIRED_STATUS
    run.expired_at = utcnow()
    run.expired_by = payload.operator
    run.expiration_note = payload.note
    _force_no_execution(run)
    db.commit()
    db.refresh(run)
    log_event(
        db,
        "action_run_expired",
        {"run_id": run.id, "operator": payload.operator, "execution_enabled": run.execution_enabled},
    )
    return _run_response(run, warnings=[NO_EXECUTION_WARNING])


@router.get("", response_model=ActionRunListResponse)
def list_action_runs(
    session_id: int | None = Query(default=None),
    host_id: int | None = Query(default=None),
    status: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> ActionRunListResponse:
    if status is not None and status not in ACTION_RUN_STATUSES:
        raise HTTPException(status_code=422, detail="Unsupported action run status")
    query = db.query(ActionRun)
    if session_id is not None:
        query = query.filter(ActionRun.session_id == session_id)
    if host_id is not None:
        query = query.filter(ActionRun.host_id == host_id)
    if status is not None:
        query = query.filter(ActionRun.status == status)
    total = query.count()
    runs = query.order_by(ActionRun.created_at.desc(), ActionRun.id.desc()).offset(offset).limit(limit).all()
    return ActionRunListResponse(
        items=[_run_response(run) for run in runs],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{run_id}/readiness", response_model=ExecutionReadinessResponse)
def get_action_run_readiness(run_id: int, db: Session = Depends(get_db)) -> ExecutionReadinessResponse:
    try:
        readiness = resolve_action_run_readiness(db, run_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="Action run not found") from exc

    run = db.get(ActionRun, readiness.run_id)
    host_id = run.host_id if run else None
    ssh_profile_id = None
    if readiness.ssh_profile is not None:
        ssh_profile_id = readiness.ssh_profile.id
    elif readiness.host is not None:
        ssh_profile_id = readiness.host.ssh_profile_id

    log_event(
        db,
        "action_run_readiness_checked",
        {
            "run_id": readiness.run_id,
            "ready": readiness.ready,
            "status": readiness.status,
            "host_id": host_id,
            "ssh_profile_id": ssh_profile_id,
            "blockers_count": len(readiness.blockers),
            "execution_enabled": False,
        },
    )
    return _readiness_response(readiness)


@router.post("/{run_id}/execute", response_model=ActionExecutionResponse)
def execute_action_run(
    run_id: int, payload: ActionRunExecuteRequest, db: Session = Depends(get_db)
) -> ActionExecutionResponse:
    try:
        execution = execute_approved_action_run(db, run_id, payload.operator)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="Action run not found") from exc
    except ActionExecutionBlockedError as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "execution_id": exc.execution.id,
                "status": "blocked",
                "blockers": exc.blockers,
                "message": "Execution was blocked before SSH connection.",
            },
        ) from exc
    return _execution_response(execution)


@router.get("/{run_id}/executions", response_model=ActionExecutionListResponse)
def list_action_run_executions(
    run_id: int,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> ActionExecutionListResponse:
    _run_or_404(db, run_id)
    query = db.query(ActionExecution).filter(ActionExecution.run_id == run_id)
    total = query.count()
    executions = query.order_by(ActionExecution.started_at.desc(), ActionExecution.id.desc()).offset(offset).limit(limit).all()
    return ActionExecutionListResponse(
        items=[_execution_response(execution) for execution in executions],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{run_id}", response_model=ActionRunResponse)
def get_action_run(run_id: int, db: Session = Depends(get_db)) -> ActionRunResponse:
    return _run_response(_run_or_404(db, run_id))
