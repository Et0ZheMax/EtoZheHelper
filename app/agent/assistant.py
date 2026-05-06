from app.agent.analyzer import analyze_output, looks_like_diagnostic_output
from app.agent.findings import AnalysisResult
from app.agent.plans import DiagnosticPlan, get_plan
from app.agent.topics import detect_topic
from app.kb.models import KnowledgeDocument, SearchResult
from app.kb.search import search_documents


class DeterministicAssistant:
    """Local deterministic assistant: no LLMs, no external APIs, no command execution."""

    def __init__(self, documents: list[KnowledgeDocument], max_results: int = 5) -> None:
        self.documents = documents
        self.max_results = max_results

    def answer(self, message: str) -> tuple[str, list[SearchResult]]:
        topic = detect_topic(message)
        plan = get_plan(topic.key)
        enhanced_query = f"{message} {topic.search_hints}".strip()
        sources = search_documents(enhanced_query, self.documents, self.max_results)

        if looks_like_diagnostic_output(message):
            analysis = analyze_output(message, topic.key)
            if analysis.findings:
                return self._format_analysis_answer(analysis, sources), sources
            return self._format_no_findings_answer(topic.key, plan, sources), sources

        return self._format_answer(topic.key, plan, sources), sources

    def _format_answer(self, topic_key: str, plan: DiagnosticPlan, sources: list[SearchResult]) -> str:
        lines: list[str] = [f"Похоже, это тема: `{topic_key}`.", ""]

        if sources:
            lines.append("Я нашёл релевантные материалы в базе:")
            lines.append("")
            for index, source in enumerate(sources, start=1):
                lines.append(f"{index}. {source.title} — `{source.path}` (score: {source.score:g})")
        else:
            lines.append("В базе не нашлось точного совпадения, поэтому даю общий безопасный план.")

        lines.extend(
            [
                "",
                "Безопасный старт диагностики:",
                "",
                "```bash",
                *plan.commands,
                "```",
                "",
                "Как читать результат:",
                "",
            ]
        )
        lines.extend(f"- {item}" for item in plan.how_to_read)
        lines.extend(["", "Что НЕ делать первым шагом:", ""])
        lines.extend(f"- {item}" for item in plan.what_not_to_do)
        lines.extend(
            [
                "",
                "Пришли обезличенный вывод команд, и я помогу построить гипотезы.",
                "Убери пароли, токены, cookies, private keys, публичные IP, домены, логины и ФИО.",
                "На этом MVP этапе приложение ничего не выполняет на хостах: команды выше — только текстовые подсказки для оператора.",
            ]
        )
        return "\n".join(lines)

    def _format_analysis_answer(self, analysis: AnalysisResult, sources: list[SearchResult]) -> str:
        lines: list[str] = [
            "Похоже, ты прислал диагностический вывод. Я нашёл такие признаки:",
            "",
            f"Detected topic: `{analysis.topic}`.",
            "",
            "## Findings",
            "",
        ]

        for finding in analysis.findings:
            icon = {"info": "ℹ️", "warning": "⚠️", "critical": "🚨"}.get(finding.severity, "•")
            lines.extend(
                [
                    f"### {icon} {finding.title}",
                    "Evidence:",
                    "```text",
                    finding.evidence,
                    "```",
                    "",
                    "Interpretation:",
                    finding.interpretation,
                    "",
                ]
            )

        lines.extend(["## Гипотезы", ""])
        if analysis.hypotheses:
            lines.extend(f"{index}. {hypothesis}" for index, hypothesis in enumerate(analysis.hypotheses, start=1))
        else:
            lines.append("1. Явных гипотез недостаточно; нужен дополнительный read-only вывод.")

        lines.extend(["", "## Следующие безопасные проверки", "", "```bash"])
        if analysis.next_checks:
            lines.extend(analysis.next_checks)
        else:
            lines.append("# Пришли ещё обезличенный вывод по теме — уточним гипотезы.")
        lines.extend(["```", ""])

        if sources:
            lines.extend(["## Релевантные материалы KB", ""])
            for index, source in enumerate(sources, start=1):
                lines.append(f"{index}. {source.title} — `{source.path}` (score: {source.score:g})")
            lines.append("")

        lines.extend(
            [
                "Пришли обезличенный вывод следующих проверок — продолжим.",
                "Я не выполняю команды и не отправляю данные наружу; команды выше — только текстовые подсказки.",
            ]
        )
        return "\n".join(lines)

    def _format_no_findings_answer(self, topic_key: str, plan: DiagnosticPlan, sources: list[SearchResult]) -> str:
        base_answer = self._format_answer(topic_key, plan, sources)
        return (
            "Похоже, ты прислал диагностический вывод, но явных известных признаков я не нашёл.\n"
            "Ниже даю безопасный topic-aware план, чтобы собрать более показательные факты.\n\n"
            f"{base_answer}"
        )
