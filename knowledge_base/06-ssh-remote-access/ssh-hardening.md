# SSH hardening

## Базовые настройки

Файл:

```bash
sudo nano /etc/ssh/sshd_config
```

Рекомендации:

```text
PermitRootLogin no
PasswordAuthentication no
PubkeyAuthentication yes
MaxAuthTries 3
ClientAliveInterval 300
ClientAliveCountMax 2
```

Проверить конфиг:

```bash
sudo sshd -t
sudo systemctl reload ssh
```

## Важно

Перед отключением паролей проверь, что вход по ключу работает в отдельной сессии.
