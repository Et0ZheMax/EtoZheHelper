# EtoZheHelper

EtoZheHelper — будущий внутренний инженерный помощник для troubleshooting, системного администрирования и работы с локальной Markdown-базой знаний. Stage 1 MVP intentionally работает локально и детерминированно: без внешних LLM/API, SSH, executor и удалённого управления.

## Что умеет MVP

- Поднимает FastAPI web-приложение.
- Показывает простую страницу чата на `/` через Jinja2 и vanilla JS.
- Рекурсивно читает Markdown-файлы из `knowledge_base/`.
- Парсит простую YAML-like frontmatter-секцию без PyYAML.
- Ищет по title, path, headings, tags, domain и content без embeddings и внешних API.
- Формирует deterministic ответ на основе найденных документов.
- Сохраняет chat sessions и messages в SQLite.
- Пишет простые audit events.
- Имеет pytest-тесты для KB loader, search и API.

## Что MVP пока НЕ умеет

- Не выполняет SSH-подключения.
- Не выполняет shell-команды и команды пользователя.
- Не запускает Ansible, Docker или Terraform.
- Не вызывает внешние LLM/API и не отправляет пользовательские данные наружу.
- Не реализует полноценный RAG, embeddings или policy engine.
- Не меняет инфраструктуру и не управляет удалёнными хостами.

## Установка зависимостей

```bash
python -m venv .venv
```

Linux/macOS:

```bash
source .venv/bin/activate
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Установка проекта и dev-зависимостей:

```bash
pip install -e ".[dev]"
```

## Запуск приложения

```bash
uvicorn app.main:app --reload
```

Альтернативно:

```bash
python scripts/dev_run.py
```

## Как открыть UI

Открой в браузере:

```text
http://127.0.0.1:8000
```

На странице есть три зоны: статус базы знаний и safety-памятка, чат, а также `Sources / Diagnostics` для найденных документов.

## Как проверить API

```bash
curl http://127.0.0.1:8000/api/health
curl http://127.0.0.1:8000/api/kb/stats
```

Пример chat-запроса:

```bash
curl -X POST http://127.0.0.1:8000/api/chat \
  -H 'Content-Type: application/json' \
  -d '{"message":"Не работает DNS на Ubuntu","session_id":null}'
```

## Как запустить тесты

```bash
pytest
```

## Как положить Markdown-базу знаний

Клади `.md` файлы в каталог `knowledge_base/`. Подкаталоги поддерживаются, скрытые файлы и папки игнорируются.

Пример frontmatter:

```md
---
type: runbook
domain: linux
tags: [dns, resolved]
risk: low
requires_root: false
---

# Linux DNS quick check

## Когда использовать

Описание симптома и безопасной диагностики.
```

Поддерживаемые поля документа: `type`, `domain`, `tags`, `risk`, `requires_root`. Если frontmatter отсутствует, документ всё равно будет загружен, а title будет взят из первого `# Heading` или имени файла.

## Конфигурация

Приложение запускается без `.env`. Безопасные defaults:

```env
APP_NAME=EtoZheHelper
APP_ENV=dev
DATABASE_URL=sqlite:///./data/eto_zhe_helper.db
KNOWLEDGE_BASE_DIR=./knowledge_base
MAX_SEARCH_RESULTS=5
```

Для локальной настройки скопируй `.env.example` в `.env` и измени значения при необходимости. Не коммить `.env`.

## Данные и audit

SQLite создаётся автоматически при старте по пути `data/eto_zhe_helper.db`. В БД создаются таблицы:

- `chat_sessions`;
- `chat_messages`;
- `audit_events`.

Audit events пишутся best-effort и не должны ломать основной сценарий чата.

## План следующих этапов

1. Добавить нормализацию и кэширование индекса KB.
2. Добавить embeddings/RAG в локальном или контролируемом режиме.
3. Спроектировать policy engine для безопасных диагностических действий.
4. Добавить executor только как явно разрешённый и аудитируемый слой.
5. Расширить UI: история сессий, загрузка диагностического вывода, фильтры sources.
6. Добавить GUI wrapper для локального desktop-сценария.
