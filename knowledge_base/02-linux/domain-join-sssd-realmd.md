# Linux domain join: realmd/sssd

## Пакеты

```bash
sudo apt update
sudo apt install -y realmd sssd sssd-tools adcli samba-common-bin oddjob oddjob-mkhomedir packagekit
```

## Discover

```bash
realm discover example.local
```

## Join

```bash
sudo realm join example.local -U admin.user
realm list
```

## Проверки

```bash
realm list
id user@example.local
getent passwd user@example.local
sssctl domain-list
sssctl domain-status example.local
```

## Логи

```bash
journalctl -u sssd -n 200 --no-pager
journalctl -u realmd -n 200 --no-pager
```

## Частые проблемы

| Симптом | Причина |
|---|---|
| realm discover не видит домен | DNS/search domain/firewall/time |
| id user не работает | sssd/cache/domain config |
| sudo ругается unable to resolve host | hostname отсутствует в /etc/hosts |
| Kerberos ошибки | время, DNS SRV, realm |
| Пользователь не логинится | realm permit, PAM, home dir |

## Очистить sssd cache

```bash
sudo systemctl stop sssd
sudo rm -rf /var/lib/sss/db/*
sudo systemctl start sssd
```

## Permit group

```bash
sudo realm permit -g "linux_admins@example.local"
```

## sudoers через visudo

```bash
echo '%linux_admins@example.local ALL=(ALL) ALL' | sudo tee /etc/sudoers.d/90-linux-admins
sudo chmod 0440 /etc/sudoers.d/90-linux-admins
sudo visudo -cf /etc/sudoers.d/90-linux-admins
```
