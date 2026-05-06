---
type: runbook
domain: linux
tags: [linux, ssh, sshd, keys, remote]
risk: medium
requires_root: sometimes
---

# SSH troubleshooting

## Клиентская диагностика

```bash
ssh -vvv user@host
nc -vz host 22
```

## Разница ошибок

### Connection timed out

```text
Нет TCP ответа: сеть, firewall, wrong IP, sshd не слушает наружу.
```

### Connection refused

```text
Хост доступен, но порт закрыт или sshd не слушает.
```

### Permission denied

```text
Сеть и порт OK, проблема auth: пароль, ключ, user, PAM, AllowUsers.
```

### Host key verification failed

```text
Изменился host key или запись в known_hosts.
```

## Сервер

```bash
systemctl status ssh --no-pager
systemctl status sshd --no-pager
ss -lntp | grep ':22'
sudo sshd -t
journalctl -u ssh -n 100 --no-pager
```

## Конфиг

```bash
sudo sshd -T | less
sudo grep -Ei 'permitroot|passwordauth|pubkey|allowusers|allowgroups|port' /etc/ssh/sshd_config
```

## Ключи

На клиенте:

```bash
ls -la ~/.ssh
ssh-add -l
```

На сервере:

```bash
ls -la /home/user/.ssh
cat /home/user/.ssh/authorized_keys
```

Права:

```bash
chmod 700 ~/.ssh
chmod 600 ~/.ssh/authorized_keys
```

## known_hosts

```bash
ssh-keygen -R host.example.local
ssh-keygen -R 10.0.0.20
```

## Логи auth

```bash
sudo tail -f /var/log/auth.log
```

## fail2ban

```bash
sudo fail2ban-client status
sudo fail2ban-client status sshd
```

## Senior flow

```text
1. DNS/IP
2. TCP 22
3. sshd listening
4. server logs during attempt
5. client -vvv
6. auth method order
7. key permissions
8. PAM/AD/SSSD if domain user
```
