# Troubleshooting Core

Базовая методика диагностики для любых сервисов.

## Модель слоёв

```text
User -> Client/App -> OS -> Network -> DNS -> Auth -> Service -> Database -> Storage -> External dependency
```

Всегда пытайся понять, на каком слое проблема.

## Главные вопросы

1. Что именно не работает?
2. У кого не работает: один пользователь, группа, все?
3. Когда началось?
4. Что менялось перед проблемой?
5. Воспроизводится ли стабильно?
6. Есть ли workaround?
7. Какие логи подтверждают проблему?
8. Что проверено и что исключено?

## Быстрая классификация

| Симптом | Возможный слой |
|---|---|
| Не открывается сайт | DNS, сеть, reverse proxy, app, TLS |
| Логин не проходит | AD/LDAP, Kerberos, права, время, пароль |
| Медленно работает | CPU/RAM/disk, сеть, DB, lock, очередь |
| Ошибка 500 | App/backend/config/dependency |
| Ошибка 403 | Authz/ACL/group/policy |
| Ошибка timeout | Network/firewall/service down |
| Disk full | Storage/log rotation/temp/backups |
| Service failed | systemd/config/permissions/dependency |

## Принцип безопасного исправления

- Перед правкой конфигов: backup.
- Перед массовым действием: dry-run.
- Перед удалением: список объектов + подтверждение.
- После изменения: проверка сервиса и логов.
- После аварии: короткий RCA.
