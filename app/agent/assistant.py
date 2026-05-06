from app.kb.models import KnowledgeDocument, SearchResult
from app.kb.search import search_documents


SAFE_COMMANDS = [
    "cat /etc/resolv.conf",
    "resolvectl status",
    "getent hosts example.local",
    "resolvectl query example.local",
    "dig example.local",
]


class DeterministicAssistant:
    """Local deterministic assistant: no LLMs, no external APIs, no command execution."""

    def __init__(self, documents: list[KnowledgeDocument], max_results: int = 5) -> None:
        self.documents = documents
        self.max_results = max_results

    def answer(self, message: str) -> tuple[str, list[SearchResult]]:
        sources = search_documents(message, self.documents, self.max_results)
        return self._format_answer(sources), sources

    def _format_answer(self, sources: list[SearchResult]) -> str:
        lines: list[str] = []
        if sources:
            lines.append("Я нашёл несколько релевантных материалов в локальной базе знаний:")
            lines.append("")
            for index, source in enumerate(sources, start=1):
                lines.append(f"{index}. {source.title} — `{source.path}` (score: {source.score:g})")
        else:
            lines.append("В локальной базе знаний пока не нашлось явных совпадений по запросу.")
            lines.append("Можно добавить Markdown-runbook в `knowledge_base/`, и я начну учитывать его в ответах.")

        lines.extend(
            [
                "",
                "Я не могу подтвердить точную причину без контекста и вывода диагностики, поэтому предлагаю безопасный старт:",
                "",
                "```bash",
                *SAFE_COMMANDS,
                "```",
                "",
                "Как читать результат:",
                "",
                "- если FQDN работает, а shortname нет — проверь search domain;",
                "- если `getent` пустой, но `dig` работает — проверь NSS/nsswitch;",
                "- если DNS-сервер не отвечает напрямую — проверь DNS service, маршрут или firewall;",
                "- если проблема не про DNS, пришли тему и обезличенные симптомы — я сопоставлю их с базой знаний.",
                "",
                "Пришли обезличенный вывод команд: убери пароли, токены, cookies, публичные IP, домены, логины и ФИО.",
                "На этом MVP этапе я ничего не выполняю на хостах и работаю только с локальной Markdown-базой.",
            ]
        )
        return "\n".join(lines)
