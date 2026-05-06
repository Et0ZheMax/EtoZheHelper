# Bash templates

## Строгий режим

```bash
set -Eeuo pipefail
```

## Для production-скриптов

- проверять root/sudo;
- логировать;
- делать backup конфигов;
- иметь dry-run;
- валидировать зависимости;
- не продолжать после критичных ошибок.
