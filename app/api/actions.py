from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.actions.catalog import list_action_definitions
from app.actions.models import ActionRequest
from app.actions.policy import InvalidActionParamsError, UnknownActionError, propose_action
from app.audit.logger import log_event
from app.db import get_db
from app.models import ChatSession
from app.schemas import ActionCatalogResponse, ActionDefinitionResponse, ActionProposalRequest, ActionProposalResponse

router = APIRouter(prefix="/actions", tags=["actions"])


def _proposal_response(proposal) -> ActionProposalResponse:
    return ActionProposalResponse(
        action=proposal.action,
        label=proposal.label,
        category=proposal.category,
        risk=proposal.risk,
        read_only=proposal.read_only,
        requires_approval=proposal.requires_approval,
        needs_sudo=proposal.needs_sudo,
        execution_enabled=proposal.execution_enabled,
        command_preview=proposal.command_preview,
        params=proposal.params,
        warnings=proposal.warnings,
    )


@router.get("/catalog", response_model=ActionCatalogResponse)
def action_catalog() -> ActionCatalogResponse:
    return ActionCatalogResponse(
        items=[ActionDefinitionResponse(**definition.public_dict()) for definition in list_action_definitions()]
    )


@router.post("/propose", response_model=ActionProposalResponse)
def action_propose(payload: ActionProposalRequest, db: Session = Depends(get_db)) -> ActionProposalResponse:
    if payload.session_id is not None and db.get(ChatSession, payload.session_id) is None:
        raise HTTPException(status_code=404, detail="Chat session not found")
    try:
        request = ActionRequest(action=payload.action, params=payload.params, session_id=payload.session_id)
        proposal = propose_action(request.action, request.params)
    except UnknownActionError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except InvalidActionParamsError as exc:
        raise HTTPException(status_code=422, detail=exc.errors) from exc

    log_event(
        db,
        "action_proposed",
        {
            "session_id": payload.session_id,
            "action": proposal.action,
            "category": proposal.category,
            "risk": proposal.risk,
            "read_only": proposal.read_only,
            "execution_enabled": proposal.execution_enabled,
        },
    )
    return _proposal_response(proposal)
