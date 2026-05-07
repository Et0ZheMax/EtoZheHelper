import re
from typing import Any
from urllib.parse import urlparse

from app.actions.catalog import get_action_definition
from app.actions.models import ActionDefinition, ActionParamDefinition, ActionProposal, ActionRequest, ActionValidationResult

SAFE_NAME_RE = re.compile(r"^[A-Za-z0-9_.@:+-]{1,253}$")
SAFE_SERVICE_RE = re.compile(r"^[A-Za-z0-9_.@:+\-]+(\.service)?$")
SAFE_CONTAINER_RE = re.compile(r"^[A-Za-z0-9_.-]{1,128}$")
SAFE_PRINTER_RE = re.compile(r"^[A-Za-z0-9_.-]{1,128}$")
URL_FORBIDDEN_RE = re.compile(r"[\s'\"`;|&<>$]")

STAGE_10_WARNING = "Stage 10 does not execute actions. This is a preview only."
EXECUTION_ENABLED = False


class ActionPolicyError(ValueError):
    """Base error for action policy validation failures."""


class UnknownActionError(ActionPolicyError):
    """Raised when an action key is not allowlisted."""


class InvalidActionParamsError(ActionPolicyError):
    """Raised when supplied parameters do not match the action schema."""

    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__("; ".join(errors))


def validate_action(request: ActionRequest) -> ActionValidationResult:
    try:
        proposal = propose_action(request.action, request.params)
    except UnknownActionError as exc:
        return ActionValidationResult(valid=False, errors=[str(exc)])
    except InvalidActionParamsError as exc:
        return ActionValidationResult(valid=False, errors=exc.errors)
    return ActionValidationResult(valid=True, proposal=proposal)


def propose_action(action_key: str, params: dict[str, Any] | None = None) -> ActionProposal:
    definition = get_action_definition(action_key)
    if definition is None:
        raise UnknownActionError(f"Unknown action: {action_key}")

    safe_params = _validate_params(definition, params or {})
    return ActionProposal(
        action=definition.key,
        label=definition.label,
        category=definition.category,
        risk=definition.risk,
        read_only=definition.read_only,
        requires_approval=definition.requires_approval,
        needs_sudo=definition.needs_sudo,
        execution_enabled=EXECUTION_ENABLED,
        command_preview=definition.command_template.format(**safe_params),
        params=safe_params,
        warnings=[STAGE_10_WARNING],
    )


def _validate_params(definition: ActionDefinition, raw_params: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    safe_params: dict[str, Any] = {}
    allowed = set(definition.params_schema)

    for key in raw_params:
        if key not in allowed:
            errors.append(f"Unknown parameter for {definition.key}: {key}")

    for key, spec in definition.params_schema.items():
        has_value = key in raw_params and raw_params[key] is not None
        if not has_value:
            if spec.default is not None:
                safe_params[key] = spec.default
                continue
            if spec.required:
                errors.append(f"Missing required parameter: {key}")
            continue

        try:
            safe_params[key] = _validate_value(key, raw_params[key], spec)
        except ValueError as exc:
            errors.append(str(exc))

    if errors:
        raise InvalidActionParamsError(errors)
    return safe_params


def _validate_value(name: str, value: Any, spec: ActionParamDefinition) -> str | int:
    if spec.kind in {"port", "lines"}:
        return _validate_int(name, value, spec.minimum, spec.maximum)
    text = str(value)
    if spec.kind == "safe_name":
        return _validate_regex(name, text, SAFE_NAME_RE, "safe hostname/IP/DNS name")
    if spec.kind == "service":
        return _validate_regex(name, text, SAFE_SERVICE_RE, "safe systemd unit name")
    if spec.kind == "container":
        return _validate_regex(name, text, SAFE_CONTAINER_RE, "safe Docker container name/id")
    if spec.kind == "printer":
        return _validate_regex(name, text, SAFE_PRINTER_RE, "safe printer queue name")
    if spec.kind == "url":
        return _validate_url(name, text)
    raise ValueError(f"Unsupported parameter validator for {name}")


def _validate_regex(name: str, value: str, pattern: re.Pattern[str], description: str) -> str:
    if not pattern.fullmatch(value):
        raise ValueError(f"Invalid parameter {name}: expected {description}")
    return value


def _validate_int(name: str, value: Any, minimum: int | None, maximum: int | None) -> int:
    if isinstance(value, bool):
        raise ValueError(f"Invalid parameter {name}: expected integer")
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid parameter {name}: expected integer") from exc
    if minimum is not None and number < minimum:
        raise ValueError(f"Invalid parameter {name}: must be >= {minimum}")
    if maximum is not None and number > maximum:
        raise ValueError(f"Invalid parameter {name}: must be <= {maximum}")
    return number


def _validate_url(name: str, value: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(f"Invalid parameter {name}: expected http:// or https:// URL with host")
    if URL_FORBIDDEN_RE.search(value):
        raise ValueError(f"Invalid parameter {name}: URL contains forbidden shell metacharacters or whitespace")
    return value
