from dataclasses import dataclass, field
from typing import Any, Literal

RiskLevel = Literal["low"]
ParamType = Literal["string", "integer"]
ParamKind = Literal["safe_name", "service", "container", "printer", "url", "port", "lines"]


@dataclass(frozen=True)
class ActionParamDefinition:
    """A single allowlisted action parameter definition."""

    type: ParamType
    kind: ParamKind
    description: str
    required: bool = True
    default: Any | None = None
    minimum: int | None = None
    maximum: int | None = None

    def public_schema(self) -> dict[str, Any]:
        schema: dict[str, Any] = {
            "type": self.type,
            "required": self.required,
            "description": self.description,
        }
        if self.default is not None:
            schema["default"] = self.default
        if self.minimum is not None:
            schema["minimum"] = self.minimum
        if self.maximum is not None:
            schema["maximum"] = self.maximum
        return schema


@dataclass(frozen=True)
class ActionDefinition:
    """Allowlisted diagnostic action template. It is never executed in Stage 10."""

    key: str
    label: str
    description: str
    category: str
    command_template: str
    params_schema: dict[str, ActionParamDefinition] = field(default_factory=dict)
    risk: RiskLevel = "low"
    read_only: bool = True
    requires_approval: bool = True
    needs_sudo: bool = False

    def public_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "label": self.label,
            "description": self.description,
            "category": self.category,
            "risk": self.risk,
            "read_only": self.read_only,
            "requires_approval": self.requires_approval,
            "needs_sudo": self.needs_sudo,
            "params_schema": {key: value.public_schema() for key, value in self.params_schema.items()},
        }


@dataclass(frozen=True)
class ActionRequest:
    action: str
    params: dict[str, Any] = field(default_factory=dict)
    session_id: int | None = None


@dataclass(frozen=True)
class ActionProposal:
    action: str
    label: str
    category: str
    risk: RiskLevel
    read_only: bool
    requires_approval: bool
    needs_sudo: bool
    execution_enabled: bool
    command_preview: str
    params: dict[str, Any]
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ActionValidationResult:
    valid: bool
    proposal: ActionProposal | None = None
    errors: list[str] = field(default_factory=list)
