---
type: policy
domain: linux
tags: [linux, safe-fix, backup, rollback]
risk: low
requires_root: false
---

# Safe fix patterns

## Backup перед правкой

```bash
sudo cp -a /etc/service/config.conf /etc/service/config.conf.bak.$(date +%F-%H%M%S)
```

## Validate перед restart

```bash
sudo nginx -t
sudo sshd -t
sudo visudo -c
```

## Reload вместо restart

Если сервис поддерживает reload и изменение конфигурации безопасно:

```bash
sudo systemctl reload nginx
```

Если reload не помогает:

```bash
sudo systemctl restart nginx
```

## Dry-run

Для скриптов:

```bash
./script.sh --dry-run
```

Для Ansible:

```bash
ansible-playbook playbook.yml --check --diff
```

## Ограничить scope

```bash
ansible-playbook playbook.yml --limit host1
```

## Rollback

```bash
sudo cp -a config.conf.bak.TIMESTAMP config.conf
sudo systemctl restart service
```

## Проверка после исправления

```bash
systemctl is-active service
journalctl -u service -n 50 --no-pager
ss -lntp | grep ':PORT'
curl -I http://localhost:PORT
```

## Что не делать первым действием

```text
- reboot server
- chmod -R 777
- rm -rf без проверки переменных
- docker system prune --volumes
- delete lock-файл apt без проверки процесса
- отключать firewall/AppArmor целиком
- править production конфиг без backup
```
