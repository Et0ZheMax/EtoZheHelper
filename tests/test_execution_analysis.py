from pathlib import Path

import app.execution.analysis as execution_analysis
from app.agent.findings import AnalysisResult
from app.execution.analysis import MAX_ANALYSIS_INPUT_CHARS, analyze_execution_output


SYSTEMD_FAILED_OUTPUT = """systemctl status nginx --no-pager
Loaded: loaded (/lib/systemd/system/nginx.service; enabled)
Active: failed (Result: exit-code)
Failed to start A high performance web server.
"""


DISK_FULL_OUTPUT = """df -h
Filesystem      Size  Used Avail Use% Mounted on
/dev/sda1        20G   20G     0 100% /
"""


def test_empty_stdout_stderr_returns_skipped_empty_output():
    result = analyze_execution_output("  ", "\n")

    assert result.status == "skipped_empty_output"
    assert result.analysis_json is None
    assert result.summary is None


def test_oversized_output_returns_skipped_too_large():
    result = analyze_execution_output("a" * (MAX_ANALYSIS_INPUT_CHARS + 1), "")

    assert result.status == "skipped_too_large"
    assert result.analysis_json is None
    assert result.summary is None


def test_known_systemd_failed_output_returns_analyzed_and_summary():
    result = analyze_execution_output(SYSTEMD_FAILED_OUTPUT, "")

    assert result.status == "analyzed"
    assert result.analysis_json is not None
    assert result.summary is not None
    assert "systemd" in result.summary
    assert "service failed" in result.analysis_json


def test_known_disk_full_output_returns_analyzed():
    result = analyze_execution_output(DISK_FULL_OUTPUT, "")

    assert result.status == "analyzed"
    assert result.analysis_json is not None
    assert "disk" in result.analysis_json.lower()
    assert "100%" in result.analysis_json


def test_analyzer_exception_returns_failed_safely_without_traceback(monkeypatch):
    def raise_error(message, topic_key="generic"):
        raise RuntimeError("boom with traceback details")

    monkeypatch.setattr(execution_analysis, "analyze_output", raise_error)

    result = analyze_execution_output(SYSTEMD_FAILED_OUTPUT, "")

    assert result.status == "failed"
    assert result.analysis_json is None
    assert result.summary == "Analysis failed safely."
    assert "Traceback" not in result.summary
    assert "boom" not in result.summary


def test_not_applicable_when_analyzer_returns_no_signals(monkeypatch):
    monkeypatch.setattr(
        execution_analysis,
        "analyze_output",
        lambda message, topic_key="generic": AnalysisResult(topic="generic", findings=(), hypotheses=(), next_checks=()),
    )

    result = analyze_execution_output("unrecognized but non-empty", "")

    assert result.status == "not_applicable"
    assert result.analysis_json is not None
    assert result.summary == "No actionable findings detected."


def test_no_external_llm_or_api_imports_added_to_execution_analysis():
    text = Path("app/execution/analysis.py").read_text(encoding="utf-8").lower()

    forbidden = ["openai", "requests", "httpx", "urllib", "socket", "langchain", "anthropic"]
    for token in forbidden:
        assert token not in text


def test_no_forbidden_execution_calls_in_execution_modules():
    combined = "\n".join(Path(path).read_text(encoding="utf-8") for path in Path("app/execution").glob("*.py"))

    forbidden = ["os.system", "subprocess", "shell=True"]
    for token in forbidden:
        assert token not in combined
