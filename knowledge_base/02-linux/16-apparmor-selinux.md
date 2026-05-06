---
type: runbook
domain: linux
tags: [linux, apparmor, selinux, permissions, security]
risk: medium
requires_root: sometimes
---

# AppArmor / SELinux

## Ubuntu/AppArmor

Проверить статус:

```bash
sudo aa-status
systemctl status apparmor
```

Логи denial:

```bash
journalctl -k | grep -i apparmor
dmesg -T | grep -i apparmor
```

## Временно перевести профиль в complain

```bash
sudo aa-complain /path/to/profile
```

Вернуть enforce:

```bash
sudo aa-enforce /path/to/profile
```

## SELinux

На Debian/Ubuntu обычно не активен, но в других дистрибутивах:

```bash
getenforce
sestatus
```

Логи:

```bash
sudo ausearch -m avc -ts recent
```

## Важно

Не отключай AppArmor/SELinux целиком первым действием.  
Сначала подтверди denial в логах.

## Симптомы

```text
permission denied, хотя UNIX-права верные;
сервис не может читать файл;
nginx/app не может писать в каталог;
docker/service странно падает при доступе к path.
```

## Senior flow

```text
1. проверить обычные права через ls/stat/namei
2. проверить логи AppArmor/SELinux
3. подтвердить denial
4. поправить профиль или путь
5. временный complain только для диагностики
6. вернуть enforce
```
