---
type: runbook
domain: linux
tags: [linux, dns, troubleshooting]
risk: low
requires_root: false
---

# Linux DNS quick check

## Когда использовать

Если имя не резолвится, shortname не работает или сервис открывается по IP, но не по имени.

## Безопасные команды

```bash
cat /etc/resolv.conf
resolvectl status
getent hosts example.local
resolvectl query example.local
dig example.local
```

## Как читать результат

- если FQDN работает, а shortname нет — проверить search domain;
- если `dig` работает, а `getent` нет — проверить NSS;
- если DNS-сервер не отвечает — проверить маршрут/firewall/DNS service.
