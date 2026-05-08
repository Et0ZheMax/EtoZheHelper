# EtoZheHelper

EtoZheHelper — будущий внутренний инженерный помощник для troubleshooting, системного администрирования и работы с локальной Markdown-базой знаний. Stage 1 MVP intentionally работает локально и детерминированно: без внешних LLM/API; Stage 14 добавляет строго ограниченный read-only SSH executor только для approved ActionRuns.

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
- Сохраняет chat sessions и messages в SQLite и показывает Investigation history в UI.
- Пишет простые audit events.
- Имеет pytest-тесты для KB loader, search и API.
- Показывает structured action proposals через Action Policy Engine без выполнения команд.
- Хранит inventory-only hosts и SSH profiles без секретов.
- Выполняет approved read-only ActionRuns по SSH agent auth только через Stage 14 executor и только после readiness check.

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


## Action Policy Engine

Stage 10 introduces structured action proposals. Actions are read-only allowlisted diagnostics with strict parameter validation. The app still does not execute commands. It only renders command previews and risk metadata.

Action catalog includes read-only diagnostics for Linux host identity, uptime/load, memory, disk and inode usage, failed systemd units, network addresses/routes/TCP probes, DNS resolver checks, HTTP/TLS curl previews, systemd status/unit/journal reads, listening ports, Docker read-only inspection, and CUPS/printer status. Every proposal has `risk: "low"`, `read_only: true`, `requires_approval: true`, and `execution_enabled: false`.

Catalog example:

```bash
curl http://127.0.0.1:8000/api/actions/catalog
```

Safe proposal example:

```bash
curl -X POST http://127.0.0.1:8000/api/actions/propose \
  -H "Content-Type: application/json" \
  -d '{"action":"systemd_status","params":{"service":"nginx"}}'
```

Unsafe values are rejected before any command preview is rendered:

```bash
curl -X POST http://127.0.0.1:8000/api/actions/propose \
  -H "Content-Type: application/json" \
  -d '{"action":"systemd_status","params":{"service":"nginx; rm -rf /"}}'
```

Validation is allowlist-only: unknown action keys are rejected; unknown parameters are rejected; service/container/printer/name parameters must match safe regular expressions; `port` must be `1..65535`; `lines` must be `20..500`; URLs must be `http://` or `https://`, include a host, and must not contain whitespace, quotes, backticks, shell metacharacters, redirects, or `$`. Command previews are built only from catalog templates, never from arbitrary user command strings.

There is intentionally no execute endpoint in Stage 10. Chat responses may include parameter-free suggested action cards such as `resolved_status`, `disk_usage`, `inode_usage`, `failed_units`, `docker_ps_all`, `docker_system_df`, `cups_status`, and `lpstat_all`; the UI renders them as plain text and does not show an execute button.

## Prepared Action Runs

Stage 11 adds Prepared Action Runs: an auditable dry-run layer between action proposals and any future executor. A prepared run is created from `session_id`, `host_id`, an allowlisted `action`, and validated `params`. The server validates the optional chat session, validates that the optional host exists and is enabled, passes the action and params through the existing Action Policy Engine, then saves only the resulting command preview.

`Prepare run` in the UI means **validate and save a preview**. It does not run the command. Prepared runs always have `status: "prepared"` and `execution_enabled: false`. The command preview is generated only by `propose_action()` from allowlisted catalog templates; arbitrary client-provided command strings are rejected by the request schema.

The API allows `host_id:null` for generic/local-preview prepared runs. The UI currently requires a selected host for clarity and to avoid accidental ambiguity. In both cases, no SSH connection or command execution occurs.

Prepare an action run:

```bash
curl -X POST http://127.0.0.1:8000/api/action-runs/prepare \
  -H "Content-Type: application/json" \
  -d '{"session_id":1,"host_id":1,"action":"systemd_status","params":{"service":"nginx"}}'
```

List prepared runs and fetch one run:

```bash
curl http://127.0.0.1:8000/api/action-runs
curl http://127.0.0.1:8000/api/action-runs/1
```

Every prepared run writes an `action_run_prepared` audit event with run id, session id, host id, action, category, risk, and `execution_enabled:false`. Real SSH execution remains future work: Stage 11 still does not connect over SSH, does not invoke subprocess/shell, does not perform reachability checks, does not read private key files, and does not store secrets.

## Execution Readiness

Stage 13 added an execution readiness resolver for approved prepared runs. It resolves host and SSH profile metadata and reports whether a run is structurally ready. The readiness endpoint itself still does not connect over SSH, does not verify credentials and does not execute commands; Stage 14 execution is exposed separately at `POST /api/action-runs/{run_id}/execute`.

Check readiness for an approved prepared run:

```bash
curl http://127.0.0.1:8000/api/action-runs/1/readiness
```

Readiness is metadata validation only. The resolver checks the action run status, stored command preview, host inventory fields, assigned SSH profile metadata, auth reference presence, and sudo mode warnings. Even when `ready` is `true`, the historical `execution_enabled` field remains `false`; Stage 14 execution is gated by approval, readiness, catalog safety checks, agent auth, and `sudo_mode=none`.

The readiness endpoint explicitly performs:

- no SSH connection;
- no subprocess;
- no socket, ping, DNS, or reachability checks;
- no credential validation;
- no private key or password secret reads;
- no command execution.

## Read-only SSH Executor

Stage 14 adds the first real SSH executor, but only for approved prepared ActionRuns that pass readiness. It executes only stored command previews generated by the Action Policy Engine. There is no arbitrary command endpoint and no remediation/write actions.

Stage 14.5 improves execution observability: blocked executions return an execution id, latest executions can be reviewed from the UI, stdout/stderr can be copied, and common SSH failures are classified with safe operator-friendly messages.


### Execution output analysis

Stage 15 attaches local deterministic analysis to SSH execution output. Captured stdout/stderr is analyzed by local rules only; no external LLM/API is called. The analysis is stored with the execution and shown in the UI as findings, hypotheses and next read-only checks. Suggested checks are text only and are not executed automatically.

Analysis is skipped for empty output and for output over the safe local size cap to avoid misleading partial analysis. Stage 15 does not expand execution scope: it adds no arbitrary command UI/API, no new catalog actions, no remediation/write actions, and no new credential or sudo handling.

The executor re-checks the current action catalog before running: the action must still exist, be allowlisted, be read-only, have `risk: "low"`, and require approval. It does not reconstruct commands from current parameters; execution uses the historical `ActionRun.command_preview` stored at preparation time. Results are stored in the `action_executions` table with status, exit code, bounded stdout/stderr, truncation flags, timing, warnings, and safe error text. Audit events are written for started, completed, failed, timed out, and blocked executions.

Stage 14 supports agent auth only. Manual/key/password auth are blocked for execution until future credential handling stages:

- `auth_type="agent"`: uses SSH agent / available keys with `look_for_keys=True` and `allow_agent=True`;
- `auth_type="manual"`: blocked because manual auth is not executable in Stage 14;
- `auth_type="key"`: blocked because `key_ref` is metadata only and private key file loading is not implemented;
- `auth_type="password"`: blocked because `password_ref` is metadata only and password resolution is not implemented.

Stage 14 supports `sudo_mode=none` only. `prompt` and `nopasswd_limited` are blocked for execution in this stage. The executor does not pass sudo passwords and does not use `sudo -S`.

If execution fails with host key not trusted, connect once with system SSH from the same Windows/Linux user to add the host key to `known_hosts`.

Run an approved read-only SSH check:

```bash
curl -X POST http://127.0.0.1:8000/api/action-runs/1/execute \
  -H "Content-Type: application/json" \
  -d '{"operator":"max"}'
```

Lookup execution results:

```bash
curl http://127.0.0.1:8000/api/action-runs/1/executions
curl http://127.0.0.1:8000/api/action-executions/1
```

Execution remains intentionally constrained:

- no arbitrary command API or shell textbox;
- no local command execution;
- no subprocess-based SSH;
- no interactive shell or streaming terminal;
- no remediation/write actions, restarts, reboots, package changes, firewall changes, file editing, Ansible, Terraform, or Docker Compose execution.

## Approval Queue

Stage 12 adds approval metadata for prepared action runs. Operators can approve, reject, or expire a prepared run. Approval itself does not execute anything and `execution_enabled` remains false. In Stage 14, approved runs may be executed only through the separate read-only SSH executor after readiness and safety checks pass.

Allowed approval queue statuses are `prepared`, `approved`, `rejected`, and `expired`. A run can be approved only from `prepared`; rejected from `prepared` or `approved`; and expired from `prepared` or `approved`. Once a run is `rejected` or `expired`, it cannot be approved again.

Approval, rejection, and expiration notes are stored separately: `approval_note` for approve, `rejection_note` for reject, and `expiration_note` for expire. If an approved run is later rejected or expired, the original approval metadata is preserved.

Approve a prepared run for possible future read-only execution:

```bash
curl -X POST http://127.0.0.1:8000/api/action-runs/1/approve \
  -H "Content-Type: application/json" \
  -d '{"operator":"max","note":"Approved for future read-only execution","expires_in_minutes":60}'
```

Reject a prepared or approved run:

```bash
curl -X POST http://127.0.0.1:8000/api/action-runs/1/reject \
  -H "Content-Type: application/json" \
  -d '{"operator":"max","note":"Wrong host"}'
```

Expire a prepared or approved run:

```bash
curl -X POST http://127.0.0.1:8000/api/action-runs/1/expire \
  -H "Content-Type: application/json" \
  -d '{"operator":"max","note":"Expired manually"}'
```

Stage 12 is metadata and audit only: it adds no command execution, no SSH, no executor, no credential checks, and no background task runner. Approval means only that an operator approved the stored preview for possible future execution.

## Diagnostic output analysis

MVP умеет детерминированно анализировать вставленный пользователем обезличенный вывод команд: DNS/systemd/curl/TLS/disk/performance/SSH/Docker. Приложение не выполняет эти команды само, не подключается к хостам, не вызывает внешние LLM/API и использует только локальные правила анализа.

Diagnostic output определяется по безопасным текстовым признакам: многострочный ввод, команды вроде `resolvectl status`, `getent hosts`, `dig`, `systemctl status`, `journalctl`, `curl -I`, `df -h`, `docker ps`, а также типичные фрагменты вывода (`HTTP/`, `Active:`, `Loaded:`, `connection refused`, `No space left on device`, `Permission denied`, `Exited`). Если признаки найдены, ассистент возвращает короткие findings, гипотезы и следующие read-only проверки вместо повторения стартового плана.


## Host Inventory and SSH Profiles

Stage 10.5 adds inventory-only host and SSH profile management. The app stores host metadata and non-secret auth references. Inventory endpoints do not connect to hosts, verify credentials, or execute commands; Stage 14 SSH execution is only available from approved ActionRuns through the dedicated execute endpoint.

Create an SSH profile metadata record:

```bash
curl -X POST http://127.0.0.1:8000/api/ssh-profiles \
  -H "Content-Type: application/json" \
  -d '{"name":"support-default","username":"support","auth_type":"agent","sudo_mode":"none"}'
```

Create a host inventory record:

```bash
curl -X POST http://127.0.0.1:8000/api/hosts \
  -H "Content-Type: application/json" \
  -d '{"name":"app01","hostname":"app01.example.local","tags":["nginx","prod"],"ssh_profile_id":1}'
```

List inventory records:

```bash
curl http://127.0.0.1:8000/api/hosts
curl http://127.0.0.1:8000/api/ssh-profiles
```

Unsafe host data is rejected:

```bash
curl -X POST http://127.0.0.1:8000/api/hosts \
  -H "Content-Type: application/json" \
  -d '{"name":"bad","hostname":"app01;whoami","password":"secret"}'
```

No passwords/private keys/tokens are stored. Fields with secret-looking names are rejected by request schemas. `key_ref` and `password_ref` are reference labels only; the app rejects PEM-like material, shell metacharacters, newlines and token-like blobs in those reference fields. The app does not read key files and does not validate credentials by connecting.

The UI has a minimal `Hosts` panel that can add host metadata via prompts and select a current host context for the investigation. Selected host context is persisted on the chat session as metadata only, and is displayed next to action cards, but actions are still previews only and execution remains disabled.

## Что MVP пока НЕ умеет

- Не выполняет SSH-подключения.
- Не выполняет shell-команды и команды пользователя.
- Не подключается к hosts из inventory и не проверяет SSH credentials.
- Не запускает Ansible, Docker или Terraform.
- Не вызывает внешние LLM/API и не отправляет пользовательские данные наружу.
- Не реализует полноценный RAG, embeddings или executor для выполнения действий.
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

1. статус базы знаний, список `Investigations`, кнопка `Reload KB`, domains/types и safety-памятка;
2. чат с заголовком текущей investigation, кнопками `Rename` и `Delete`;
3. `Sources / Diagnostics` с `path`, `title`, `score` и `snippet` найденных документов.

UI остаётся lightweight: Jinja2, CSS и vanilla JS, без React/Next.js/npm.

## Investigation history

EtoZheHelper stores local troubleshooting sessions in SQLite. UI allows creating, opening, renaming and deleting investigations. Each chat message is stored locally; do not paste secrets/tokens/private keys.

Investigation history endpoints:

```bash
curl http://127.0.0.1:8000/api/chat/sessions

curl -X POST http://127.0.0.1:8000/api/chat/session \
  -H "Content-Type: application/json" \
  -d '{"title":"Test investigation"}'

curl http://127.0.0.1:8000/api/chat/session/1

curl -X PATCH http://127.0.0.1:8000/api/chat/session/1 \
  -H "Content-Type: application/json" \
  -d '{"title":"Renamed investigation"}'

curl -X DELETE http://127.0.0.1:8000/api/chat/session/1
```

Session API actions write best-effort audit events for create/open/rename/delete. Deleting an investigation removes its related `chat_messages` before removing the `chat_sessions` row. Existing `POST /api/chat` still accepts `session_id:null` to create a new session and appends messages to an existing session when `session_id` is provided.

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

Chat session API:

- `GET /api/chat/sessions?limit=50&offset=0` — список investigations, новые по `updated_at` первыми;
- `GET /api/chat/session/{session_id}` — metadata и история сообщений;
- `POST /api/chat/session` — создать investigation, пустой title заменяется на `New investigation`;
- `PATCH /api/chat/session/{session_id}` — переименовать investigation, title trim/max 120;
- `DELETE /api/chat/session/{session_id}` — удалить investigation и связанные messages.

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
- `hosts`;
- `ssh_profiles`;
- `audit_events`.

При добавлении user/assistant messages у chat session обновляется `updated_at`. Audit events пишутся best-effort и не должны ломать основной сценарий чата.

## Ограничения Stage 10.5

Stage 10.5 намеренно не содержит SSH connect, shell executor, remote execution, local command execution, reachability checks, Ansible/Docker/Terraform execution, внешних LLM/API и отправки пользовательских данных наружу. Host Inventory и SSH Profiles хранят только metadata/non-secret references. Selected host context is persisted as metadata only. It is not used for execution in this stage. Любые команды и action cards в ответах — это только previews/текстовые подсказки для оператора, а не действия приложения.

## План следующих этапов

1. Добавить нормализацию и полноценное индексирование KB.
2. Добавить embeddings/RAG в локальном или контролируемом режиме.
3. Расширять Action Policy Engine новыми read-only allowlisted действиями.
4. Добавить executor только в будущем как явно разрешённый и аудитируемый слой.
5. Расширить UI: загрузка диагностического вывода и фильтры sources.
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
