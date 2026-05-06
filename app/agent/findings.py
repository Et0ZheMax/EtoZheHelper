from dataclasses import dataclass


@dataclass(frozen=True)
class Finding:
    """A deterministic diagnostic signal extracted from user-provided command output."""

    severity: str  # info | warning | critical
    title: str
    evidence: str
    interpretation: str
    next_steps: tuple[str, ...]


@dataclass(frozen=True)
class AnalysisResult:
    """Deterministic analysis result for pasted, sanitized diagnostic output."""

    topic: str
    findings: tuple[Finding, ...]
    hypotheses: tuple[str, ...]
    next_checks: tuple[str, ...]
