---
type: runbook
domain: linux
tags: [linux, curl, http, tls, proxy, nginx]
risk: low
requires_root: false
---

# curl, HTTP, HTTPS, TLS диагностика

## Когда использовать

- сайт открывается в браузере странно;
- API отдаёт 500/502/403/401;
- подозрение на TLS/certificate;
- нужно проверить reverse proxy/backend;
- нужно посмотреть headers.

## Базовые проверки

```bash
curl -I http://host
curl -I https://host
curl -vk https://host
curl -sS -o /dev/null -w '%{http_code} %{time_total}\n' https://host
```

## Полезный формат curl

```bash
curl -sS -o /dev/null \
  -w 'code=%{http_code} dns=%{time_namelookup} connect=%{time_connect} tls=%{time_appconnect} total=%{time_total}\n' \
  https://host.example.local
```

Что показывает:

```text
time_namelookup   DNS time
time_connect      TCP connect time
time_appconnect   TLS handshake time
time_total        total request time
```

## Проверить конкретный Host header

Полезно для nginx virtual hosts:

```bash
curl -vk https://10.0.0.20/ -H 'Host: app.example.local'
```

## Проверить backend локально на сервере

```bash
curl -v http://127.0.0.1:8080/health
curl -v http://localhost:8080/
```

Если backend локально не отвечает, nginx 502 ожидаем.

## HTTP status logic

| Код | Значение | Частая причина |
|---:|---|---|
| 200 | OK | работает |
| 301/302 | redirect | проверь Location |
| 400 | bad request | Host/header/proxy/app |
| 401 | auth required | нет/неверный auth |
| 403 | forbidden | права, ACL, location deny |
| 404 | not found | wrong path/routing |
| 500 | app error | backend/app logs |
| 502 | bad gateway | proxy не достучался до backend |
| 503 | unavailable | backend down/maintenance |
| 504 | gateway timeout | backend долго отвечает/network |

## Проверить TLS certificate

```bash
openssl s_client -connect host.example.local:443 -servername host.example.local </dev/null
```

Коротко:

```bash
echo | openssl s_client -connect host.example.local:443 -servername host.example.local 2>/dev/null | openssl x509 -noout -issuer -subject -dates
```

## Частые TLS проблемы

```text
certificate expired
wrong hostname / SAN mismatch
self-signed not trusted
missing intermediate certificate
old TLS version/cipher
SNI mismatch
corporate proxy substitution
```

## Проверить redirect chain

```bash
curl -IL https://host.example.local
```

## Проверить JSON API

```bash
curl -sS -H 'Accept: application/json' https://host.example.local/api/health | jq .
```

Если jq нет:

```bash
python3 -m json.tool
```

## POST test

```bash
curl -v -X POST https://host.example.local/api \
  -H 'Content-Type: application/json' \
  -d '{"test": true}'
```

Не отправляй реальные токены/персональные данные во внешние сервисы.

## Senior flow для 502

```text
1. curl -vk public URL
2. nginx/access/error logs
3. проверить upstream в конфиге
4. curl backend с самого proxy
5. ss -lntp на backend host
6. app logs
7. DB/dependency logs
8. rollback/restart минимально нужного слоя
```

## Nginx логи

```bash
sudo tail -n 100 /var/log/nginx/access.log
sudo tail -n 100 /var/log/nginx/error.log
sudo journalctl -u nginx -n 100 --no-pager
```

## Комментарий в заявку

```text
Проверил HTTP/HTTPS-доступность сервиса через curl, включая DNS, TCP connect, TLS handshake и HTTP-код ответа.
Сервис возвращал <код>. Причина локализована на уровне <reverse proxy/backend/auth/TLS>.
```
