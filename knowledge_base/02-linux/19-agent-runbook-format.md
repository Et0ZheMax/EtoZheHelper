---
type: agent_format
domain: linux
tags: [agent, rag, runbook, linux]
risk: low
requires_root: false
---

# Agent runbook format for Linux

Будущий агент должен читать документы в таком формате.

## Metadata

```yaml
---
type: runbook
domain: linux
tags: [dns, resolved]
risk: low
requires_root: false
commands_safe: true
---
```

## Sections

```text
# Title
## Когда использовать
## Симптомы
## Read-only диагностика
## Интерпретация вывода
## Гипотезы
## Safe fix
## Verification
## Escalation
## Ticket comment
```

## Agent behavior

```text
1. Не предлагать destructive команды без предупреждения.
2. Всегда начинать с read-only диагностики.
3. Команды с sudo помечать.
4. Просить обезличивать вывод.
5. Давать интерпретацию каждого результата.
6. После fix давать verification.
7. После решения предлагать KB entry.
```

## Example agent response skeleton

```md
Похоже, проблема может быть на уровне DNS или TCP. Давай сначала без изменений проверим:

```bash
getent hosts service.example.local
resolvectl query service.example.local
nc -vz service.example.local 443
curl -vk https://service.example.local
```

Как читать результат:
- если getent пустой — DNS;
- если nc timeout — сеть/firewall;
- если nc OK, curl 502 — proxy/backend;
- если TLS error — сертификат/SNI.
```
