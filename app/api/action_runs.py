import json

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.actions.models import ActionRequest
from app.actions.policy import InvalidActionParamsError, UnknownActionError, propose_action
from app.audit.logger import log_event
from app.db import get_db
from app.models import ActionRun, ChatSession, Host
from app.schemas import ActionRunListResponse, ActionRunPrepareRequest, ActionRunResponse

router = APIRouter(prefix="/action-runs", tags=["action-runs"])

STAGE_11_WARNING = "Stage 11 prepares runs only. No command was executed."
HISTORICAL_VALIDATION_WARNING = (
    "Stored run references an action or params that no longer validate against the current catalog. "
    "Showing stored preview only."
)
SESSION_HOST_MISMATCH_WARNING = (
    "The provided host_id differs from the chat session host context; the explicit host_id was used for this prepared run."
)
PREPARED_STATUS = "prepared"
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
        status=PREPARED_STATUS,
        command_preview=run.command_preview,
        params=params,
        warnings=response_warnings,
        created_at=run.created_at,
    )


def _run_or_404(db: Session, run_id: int) -> ActionRun:
    run = db.get(ActionRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Action run not found")
    return run


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


@router.get("", response_model=ActionRunListResponse)
def list_action_runs(
    session_id: int | None = Query(default=None),
    host_id: int | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> ActionRunListResponse:
    query = db.query(ActionRun)
    if session_id is not None:
        query = query.filter(ActionRun.session_id == session_id)
    if host_id is not None:
        query = query.filter(ActionRun.host_id == host_id)
    total = query.count()
    runs = query.order_by(ActionRun.created_at.desc(), ActionRun.id.desc()).offset(offset).limit(limit).all()
    return ActionRunListResponse(
        items=[_run_response(run) for run in runs],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{run_id}", response_model=ActionRunResponse)
def get_action_run(run_id: int, db: Session = Depends(get_db)) -> ActionRunResponse:
    return _run_response(_run_or_404(db, run_id))
