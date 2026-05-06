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
