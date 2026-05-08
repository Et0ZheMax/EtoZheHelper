from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from app.agent.analyzer import analyze_output
from app.agent.findings import AnalysisResult, Finding

MAX_ANALYSIS_INPUT_CHARS = 64 * 1024
MAX_TEXT_FIELD_CHARS = 1000
MAX_SUMMARY_CHARS = 300
MAX_ITEMS = 20
ANALYSIS_STATUSES = {"not_applicable", "analyzed", "skipped_empty_output", "skipped_too_large", "failed"}


@dataclass(frozen=True)
class ExecutionAnalysis:
    status: str
    analysis_json: str | None
    summary: str | None


def analyze_execution_output(stdout: str, stderr: str) -> ExecutionAnalysis:
    """Analyze SSH execution output using the local deterministic analyzer only."""
    combined = f"{stdout or ''}\n{stderr or ''}"
    if not combined.strip():
        return ExecutionAnalysis(status="skipped_empty_output", analysis_json=None, summary=None)
    if len(combined) > MAX_ANALYSIS_INPUT_CHARS:
        return ExecutionAnalysis(status="skipped_too_large", analysis_json=None, summary=None)

    try:
        result = analyze_output(combined, "generic")
        payload = _analysis_to_payload(result)
        has_signal = bool(payload["findings"] or payload["hypotheses"] or payload["next_checks"])
        if not has_signal:
            return ExecutionAnalysis(
                status="not_applicable",
                analysis_json=_json_dumps({"topic": payload["topic"], "findings": [], "hypotheses": [], "next_checks": []}),
                summary="No actionable findings detected.",
            )
        return ExecutionAnalysis(status="analyzed", analysis_json=_json_dumps(payload), summary=_summary(payload))
    except Exception:
        return ExecutionAnalysis(status="failed", analysis_json=None, summary="Analysis failed safely.")


def parse_analysis_json(value: str | None) -> dict[str, Any] | None:
    if not value:
        return None
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _analysis_to_payload(result: AnalysisResult) -> dict[str, Any]:
    return {
        "topic": _cap(result.topic, 80),
        "findings": [_finding_to_payload(finding) for finding in result.findings[:MAX_ITEMS]],
        "hypotheses": [_cap(item, MAX_TEXT_FIELD_CHARS) for item in result.hypotheses[:MAX_ITEMS]],
        "next_checks": [_cap(item, MAX_TEXT_FIELD_CHARS) for item in result.next_checks[:MAX_ITEMS]],
    }


def _finding_to_payload(finding: Finding) -> dict[str, Any]:
    return {
        "severity": _cap(finding.severity, 32),
        "title": _cap(finding.title, 200),
        "evidence": _cap(finding.evidence, MAX_TEXT_FIELD_CHARS),
        "interpretation": _cap(finding.interpretation, MAX_TEXT_FIELD_CHARS),
        "next_steps": [_cap(step, MAX_TEXT_FIELD_CHARS) for step in finding.next_steps[:MAX_ITEMS]],
    }


def _summary(payload: dict[str, Any]) -> str:
    topic = str(payload.get("topic") or "generic")
    findings = payload.get("findings") if isinstance(payload.get("findings"), list) else []
    next_checks = payload.get("next_checks") if isinstance(payload.get("next_checks"), list) else []
    severity_counts: dict[str, int] = {}
    for finding in findings:
        if not isinstance(finding, dict):
            continue
        severity = str(finding.get("severity") or "info")
        severity_counts[severity] = severity_counts.get(severity, 0) + 1
    severity_text = ", ".join(f"{count} {severity}" for severity, count in sorted(severity_counts.items()))
    if not severity_text:
        severity_text = f"{len(findings)} finding" if len(findings) == 1 else f"{len(findings)} findings"
    check_text = f", {len(next_checks)} next check" + ("" if len(next_checks) == 1 else "s") if next_checks else ""
    return _cap(f"{topic}: {severity_text}{check_text}.", MAX_SUMMARY_CHARS)


def _json_dumps(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def _cap(value: object, limit: int) -> str:
    text = str(value)
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)].rstrip() + "…"
