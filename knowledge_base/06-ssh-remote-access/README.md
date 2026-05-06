# SSH / Remote access

## Быстрая проверка SSH

```bash
ssh -vvv user@host
nc -vz host 22
```

## Ключи

```bash
ssh-keygen -t ed25519 -C "admin-key"
ssh-copy-id user@host
ssh user@host
```

## Config

```sshconfig
Host server1
  HostName server1.example.local
  User admin
  IdentityFile ~/.ssh/id_ed25519
  StrictHostKeyChecking accept-new
```

## Логи сервера

```bash
journalctl -u ssh -n 200 --no-pager
journalctl -u sshd -n 200 --no-pager
```
