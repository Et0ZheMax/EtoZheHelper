---
type: runbook
domain: linux
tags: [linux, systemd, service, unit]
risk: medium
requires_root: sometimes
---

# systemd service debug

## Когда использовать

- сервис failed;
- сервис не стартует после reboot;
- restart loop;
- unit masked;
- service запускается вручную, но не через systemd;
- env/config проблема.

## Read-only диагностика

```bash
systemctl status <service> --no-pager
systemctl cat <service>
systemctl show <service> --no-pager
journalctl -u <service> -n 200 --no-pager
journalctl -u <service> --since "1 hour ago" --no-pager
```

## Проверить failed units

```bash
systemctl --failed
```

## Проверить unit file

```bash
systemctl cat <service>
systemctl list-unit-files | grep <service>
```

## Частые состояния

```text
active (running)       работает
active (exited)        одноразовый сервис завершился успешно
failed                 упал
activating             стартует/зависает
deactivating           останавливается
masked                 запрещён symlink на /dev/null
```

## Unit masked

```bash
systemctl status <service>
sudo systemctl unmask <service>
sudo systemctl enable --now <service>
```

## Daemon reload

После изменения unit-файлов:

```bash
sudo systemctl daemon-reload
sudo systemctl restart <service>
```

## Проверка ExecStart

```bash
systemctl cat <service>
ls -l /path/from/ExecStart
sudo -u <user_from_unit> /path/from/ExecStart
```

Если сервис запускается от отдельного пользователя, проверь права и env.

## EnvironmentFile

В unit может быть:

```ini
EnvironmentFile=/etc/default/app
```

Проверить:

```bash
ls -l /etc/default/app
sudo cat /etc/default/app
```

Не публикуй содержимое env наружу без очистки секретов.

## Port conflict

```bash
ss -lntp | grep ':PORT'
```

Если порт занят другим процессом — сервис не стартанёт.

## Config validation examples

```bash
sudo nginx -t
sudo apachectl configtest
sudo sshd -t
sudo named-checkconf
sudo visudo -c
```

## Restart policy loop

```bash
systemctl show <service> -p Restart -p NRestarts
journalctl -u <service> -n 200 --no-pager
```

## Reset failed state

```bash
sudo systemctl reset-failed <service>
```

Это не чинит причину, только сбрасывает состояние failed.

## Safe fix pattern

```text
1. systemctl status
2. journalctl
3. systemctl cat
4. validate config
5. backup config
6. minimal edit
7. daemon-reload if unit changed
8. restart/reload
9. verify logs and port
```

## Комментарий в заявку

```text
Проверил состояние systemd-сервиса, unit-файл и журнал запуска.
Причина сбоя связана с <конфигом/env/портом/правами/зависимостью>.
После исправления сервис запущен, статус active, ошибки в журнале не повторяются.
```
