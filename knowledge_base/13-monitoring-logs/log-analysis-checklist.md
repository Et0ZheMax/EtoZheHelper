# Log analysis checklist

## Сначала

```text
[ ] Время проблемы известно
[ ] Timezone понятен
[ ] Есть correlation id / user / host
[ ] Проверены app logs
[ ] Проверены system logs
[ ] Проверены proxy logs
[ ] Проверены DB logs
```

## Что искать

- ERROR/FATAL/CRITICAL
- timeout
- connection refused
- permission denied
- no space left
- too many open files
- OOM
- authentication failed
- TLS/certificate
- DNS resolution failed

## Linux команды

```bash
journalctl --since "2026-05-06 10:00" --until "2026-05-06 11:00"
grep -RniE "error|failed|timeout|denied" /var/log/
```

## Docker

```bash
docker compose logs --since=1h
docker logs --since=1h <container>
```
