# Security checklists

## Базовые правила

- Не хранить секреты в коде.
- Не отправлять secrets в AI.
- Не коммитить `.env`.
- Минимальные права.
- Логи без паролей и токенов.
- Разделять prod/test/dev.
- Перед внешним доступом — reverse proxy/TLS/auth/rate limits.
