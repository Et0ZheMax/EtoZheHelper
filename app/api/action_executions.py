from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.execution.analysis import parse_analysis_json
from app.execution.executor import warnings_from_json
from app.models import ActionExecution
from app.schemas import ActionExecutionResponse

router = APIRouter(prefix="/action-executions", tags=["action-executions"])


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


@router.get("/{execution_id}", response_model=ActionExecutionResponse)
def get_action_execution(execution_id: int, db: Session = Depends(get_db)) -> ActionExecutionResponse:
    execution = db.get(ActionExecution, execution_id)
    if execution is None:
        raise HTTPException(status_code=404, detail="Action execution not found")
    return _execution_response(execution)
