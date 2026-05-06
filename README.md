# EtoZheHelper

EtoZheHelper — будущий внутренний инженерный помощник для troubleshooting, системного администрирования и работы с локальной Markdown-базой знаний. Stage 1 MVP intentionally работает локально и детерминированно: без внешних LLM/API, SSH, executor и удалённого управления.

## Что умеет MVP

- Поднимает FastAPI web-приложение.
- Показывает простую страницу чата на `/` через Jinja2 и vanilla JS.
- Рекурсивно читает Markdown-файлы из `knowledge_base/`.
- Парсит простую YAML-like frontmatter-секцию без PyYAML.
- Ищет по title, path, headings, tags, domain и content без embeddings и внешних API.
- Кэширует локальную Markdown KB в памяти и автоматически инвалидирует кэш по count/latest mtime Markdown-файлов.
- Даёт ручной reload базы знаний через `POST /api/kb/reload`.
- Возвращает stats по количеству документов, `domain`, `type`, `risk` и `tags` metadata.
- Формирует deterministic ответ на основе найденных документов.
- Сохраняет chat sessions и messages в SQLite.
- Пишет простые audit events.
- Имеет pytest-тесты для KB loader, search и API.

## Topic-aware assistant

Deterministic assistant теперь определяет troubleshooting-тему по ключевым словам, усиливает KB search hints для этой темы и добавляет к ответу безопасный read-only диагностический план. Поддерживаемые темы:

- `dns`;
- `port_connectivity`;
- `http_tls`;
- `nginx_502`;
- `systemd`;
- `disk_space`;
- `performance`;
- `ssh`;
- `apt_dpkg`;
- `permissions_sudo`;
- `sssd_ad`;
- `cups_printers`;
- `docker`;
- `generic`.

Команды из планов не выполняются приложением: они выводятся только как текстовые подсказки для оператора. Приложение по-прежнему не подключается по SSH, не запускает shell/executor, не вызывает внешние LLM/API и не отправляет данные наружу.


## Diagnostic output analysis

MVP умеет детерминированно анализировать вставленный пользователем обезличенный вывод команд: DNS/systemd/curl/TLS/disk/performance/SSH/Docker. Приложение не выполняет эти команды само, не подключается к хостам, не вызывает внешние LLM/API и использует только локальные правила анализа.

Diagnostic output определяется по безопасным текстовым признакам: многострочный ввод, команды вроде `resolvectl status`, `getent hosts`, `dig`, `systemctl status`, `journalctl`, `curl -I`, `df -h`, `docker ps`, а также типичные фрагменты вывода (`HTTP/`, `Active:`, `Loaded:`, `connection refused`, `No space left on device`, `Permission denied`, `Exited`). Если признаки найдены, ассистент возвращает короткие findings, гипотезы и следующие read-only проверки вместо повторения стартового плана.

## Что MVP пока НЕ умеет

- Не выполняет SSH-подключения.
- Не выполняет shell-команды и команды пользователя.
- Не запускает Ansible, Docker или Terraform.
- Не вызывает внешние LLM/API и не отправляет пользовательские данные наружу.
- Не реализует полноценный RAG, embeddings или policy engine.
- Не меняет инфраструктуру и не управляет удалёнными хостами.

Stage 1 остаётся **local-only KB assistant**: ответы строятся только по локальным Markdown-файлам и детерминированной логике приложения.

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

Из корня репозитория:

```bash
uvicorn app.main:app --reload
```

Альтернативно через helper script:

```bash
python scripts/dev_run.py
```

Пути к `static`, `templates`, default `data/` и default `knowledge_base/` вычисляются относительно файлов приложения, поэтому запуск не зависит от текущей рабочей директории так же хрупко, как раньше.

## Как открыть UI

Открой в браузере:

```text
http://127.0.0.1:8000
```

На странице есть три зоны:

1. статус базы знаний, кнопка `Reload KB`, domains/types и safety-памятка;
2. чат;
3. `Sources / Diagnostics` с `path`, `title`, `score` и `snippet` найденных документов.

UI остаётся lightweight: Jinja2, CSS и vanilla JS, без React/Next.js/npm.

## KB cache и reload

Knowledge base загружается через простой in-memory cache. Cache key основан на resolved `knowledge_base_dir`, а актуальность проверяется по количеству Markdown-файлов и latest `mtime`. Если Markdown-файлы изменились, следующий stats/chat запрос перечитает KB. Для ручного сброса кэша используй API reload или кнопку `Reload KB` в UI.

Если один Markdown-файл не удалось прочитать, loader пропускает его и продолжает загрузку остальных документов. Пустая KB не ломает chat: assistant вернёт безопасный ответ без sources.

## Как проверить API

Health:

```bash
curl http://127.0.0.1:8000/api/health
```

Stats:

```bash
curl http://127.0.0.1:8000/api/kb/stats
```

Пример ответа stats:

```json
{
  "documents_count": 123,
  "knowledge_base_dir": "/absolute/path/to/knowledge_base",
  "domains": {
    "linux": 21,
    "windows": 5
  },
  "types": {
    "runbook": 10,
    "cheatsheet": 8
  },
  "risks": {
    "low": 10,
    "medium": 2
  },
  "tags": {
    "dns": 5,
    "linux": 12
  }
}
```

Manual KB reload:

```bash
curl -X POST http://127.0.0.1:8000/api/kb/reload
```

Пример ответа reload:

```json
{
  "status": "reloaded",
  "documents_count": 123
}
```

Пример chat-запроса:

```bash
curl -X POST http://127.0.0.1:8000/api/chat \
  -H 'Content-Type: application/json' \
  -d '{"message":"Не работает DNS на Ubuntu","session_id":null}'
```

Если передать несуществующий `session_id`, `/api/chat` вернёт `404`.

## Как запустить тесты и проверки

```bash
pytest
```

Полная проверка после чистой установки:

```bash
pip install -e ".[dev]"
pytest
uvicorn app.main:app --reload
```

API-тесты используют временную SQLite database и временную Markdown knowledge base, чтобы не писать данные в project `data/eto_zhe_helper.db`.

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
DATABASE_URL=sqlite:////absolute/path/to/repo/data/eto_zhe_helper.db
KNOWLEDGE_BASE_DIR=/absolute/path/to/repo/knowledge_base
MAX_SEARCH_RESULTS=5
```

Default SQLite path формируется через POSIX-style path, чтобы корректно работать и на Windows, и на Linux/macOS.

Для локальной настройки скопируй `.env.example` в `.env` и измени значения при необходимости. Не коммить `.env`.

## Данные и audit

SQLite создаётся автоматически при старте по пути `data/eto_zhe_helper.db` относительно корня репозитория, если `DATABASE_URL` не переопределён. В БД создаются таблицы:

- `chat_sessions`;
- `chat_messages`;
- `audit_events`.

При добавлении user/assistant messages у chat session обновляется `updated_at`. Audit events пишутся best-effort и не должны ломать основной сценарий чата.

## Ограничения Stage 1

Stage 1 намеренно не содержит SSH, shell executor, remote execution, Ansible/Docker/Terraform execution, внешних LLM/API и отправки пользовательских данных наружу. Любые команды в ответах — это текстовые подсказки для оператора, а не действия приложения.

## План следующих этапов

1. Добавить нормализацию и полноценное индексирование KB.
2. Добавить embeddings/RAG в локальном или контролируемом режиме.
3. Спроектировать policy engine для безопасных диагностических действий.
4. Добавить executor только как явно разрешённый и аудитируемый слой.
5. Расширить UI: история сессий, загрузка диагностического вывода, фильтры sources.
6. Добавить GUI wrapper для локального desktop-сценария.

## Импорт большой Markdown knowledge base

Для подготовки большой локальной базы вроде `IT-Playbook-Max` добавлен безопасный importer `scripts/import_kb.py`. Скрипт работает только с локальной файловой системой, не вызывает shell, не выполняет файлы из источника/архива и копирует только Markdown (`.md`). Скрытые пути и небезопасные/нецелевые файлы вроде `.env`, `.key`, `.pem`, `.p12`, `.sqlite`, `.db`, `.zip` и любые non-Markdown файлы игнорируются.

Импорт из папки с сохранением относительной структуры:

```bash
python scripts/import_kb.py --source /path/to/IT-Playbook-Max --target knowledge_base
```

Dry-run перед реальной синхронизацией:

```bash
python scripts/import_kb.py --source /path/to/IT-Playbook-Max --target knowledge_base --prefix imported/IT-Playbook-Max --dry-run
```

Реальный импорт в подпапку через `--prefix`:

```bash
python scripts/import_kb.py --source /path/to/IT-Playbook-Max --target knowledge_base --prefix imported/IT-Playbook-Max
```

Импорт из zip-архива:

```bash
python scripts/import_kb.py --zip /path/to/IT-Playbook-Max.zip --target knowledge_base --prefix imported/IT-Playbook-Max
```

Zip import защищён от zip slip/path traversal: записи с абсолютными путями или `..` не распаковываются и не могут записать файлы вне `--target`. Архив не исполняется и не распаковывается целиком: importer читает только разрешённые `.md` entries и пишет их в target/prefix.

Importer больше не имеет отдельного `--overwrite`: одинаковые файлы считаются `skipped`, отличающиеся существующие `.md` обновляются и считаются `updated`, отсутствующие считаются `copied`. Importer печатает summary по итогам работы:

```text
copied: 10
updated: 2
skipped: 30
ignored: 5
errors: 0
```

## KB Browser API

Список документов доступен через:

```bash
curl "http://127.0.0.1:8000/api/kb/documents?domain=linux&limit=10"
```

Параметры списка:

- `q` — локальный текстовый поиск;
- `domain` — фильтр по frontmatter `domain`;
- `doc_type` — фильтр по frontmatter `type`;
- `risk` — фильтр по frontmatter `risk`;
- `tag` — фильтр по одному tag;
- `limit` и `offset` — пагинация.

Пример detail-запроса:

```bash
curl "http://127.0.0.1:8000/api/kb/document?path=README.md"
```

`/api/kb/document` принимает только KB-relative path уже загруженного Markdown-документа. Абсолютные пути, `../` traversal и неизвестные документы возвращают `404`; абсолютные server filesystem paths наружу не раскрываются.

## KB Browser в UI

На `/` в левой панели есть блок `KB Browser`: search input, фильтры `domain`, `type`, `risk`, `tag` и кнопка `Search`. Правая панель разделена на `Sources from last answer` и `KB Browser`. Результаты browser показывают title, KB-relative path, domain/type/risk, tags и snippet. Клик по документу открывает detail как plain text; содержимое вставляется через `textContent`, Markdown не рендерится как HTML.

После `Reload KB` UI обновляет stats и filter options. Chat behavior и источники последнего ответа остаются прежними.

## Улучшения локального поиска

Локальный поиск остаётся deterministic и dependency-free: без embeddings, внешнего search engine и внешних LLM/API. Query нормализуется через casefold/tokenization для русских и английских слов, применяется небольшой synonyms/hints map (`dns`, `порт`, `nginx`, `место`, `docker`), snippets ограничены примерно 400 символами и стараются попадать в релевантную heading-section.

## Security notes для KB import/browser

- Нет SSH, shell execution, remote execution и запуска пользовательских команд.
- Нет Ansible/Docker/Terraform execution.
- Нет внешних LLM/API и отправки данных наружу.
- Importer копирует только `.md` и игнорирует hidden/suspicious/non-Markdown файлы.
- Zip import блокирует path traversal и не пишет вне target.
- Document API читает только документы, уже загруженные из KB, и не раскрывает server absolute paths.
- UI вставляет document content и snippets как plain text, без unsanitized HTML rendering.
