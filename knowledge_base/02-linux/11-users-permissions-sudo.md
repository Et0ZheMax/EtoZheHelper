---
type: runbook
domain: linux
tags: [linux, users, permissions, sudo, pam]
risk: medium
requires_root: sometimes
---

# Users, permissions, sudo

## Кто я

```bash
whoami
id
groups
```

## Пользователь

```bash
getent passwd user
id user
last user | head
```

## Группы

```bash
groups user
getent group sudo
getent group <group>
```

## sudo

```bash
sudo -l
sudo -v
```

## sudo unable to resolve host

Симптом:

```text
sudo: unable to resolve host workstation-01
```

Проверить:

```bash
hostname
cat /etc/hostname
cat /etc/hosts
```

В `/etc/hosts` должна быть строка с hostname:

```text
127.0.1.1 workstation-01
```

Исправление:

```bash
echo "127.0.1.1 $(hostname)" | sudo tee -a /etc/hosts
```

Лучше аккуратно отредактировать, чтобы не плодить дубли.

## sudoers

Всегда проверять через visudo:

```bash
sudo visudo -c
sudo visudo -cf /etc/sudoers.d/file
```

Пример:

```bash
echo '%linux_admins ALL=(ALL) ALL' | sudo tee /etc/sudoers.d/90-linux-admins
sudo chmod 0440 /etc/sudoers.d/90-linux-admins
sudo visudo -cf /etc/sudoers.d/90-linux-admins
```

## Права файлов

```bash
ls -la
stat file
namei -l /path/to/file
```

`namei -l` полезен, когда файл есть, но нет доступа из-за родительской папки.

## chmod/chown аккуратно

```bash
sudo chown user:group file
sudo chmod 0644 file
sudo chmod 0755 directory
```

Не делай `chmod -R 777`.

## PAM/auth logs

```bash
sudo tail -n 100 /var/log/auth.log
journalctl -u ssh -n 100 --no-pager
```

## Senior flow

```text
1. id пользователя
2. группы
3. sudo -l
4. права файла через namei -l
5. PAM/auth logs
6. если AD user — проверить SSSD/getent/id
```
