---
type: runbook
domain: linux
tags: [linux, port, tcp, connectivity, ss, nc]
risk: low
requires_root: false
---

# Проверка портов и TCP connectivity

## Когда использовать

- сервис “не открывается”;
- приложение пишет connection refused/timeout;
- нужно понять, слушает ли порт;
- нужно проверить доступность порта с клиента;
- подозрение на firewall/routing/service down.

## Локально: кто слушает порт

```bash
ss -tulpn
ss -lntp
ss -lntp | grep ':443'
ss -lntp | grep ':8080'
```

Расшифровка:

```text
LISTEN 0 511 0.0.0.0:80     -> слушает на всех IPv4 интерфейсах
LISTEN 0 511 127.0.0.1:8080 -> доступно только локально
LISTEN 0 511 [::]:443       -> IPv6/all, зависит от sysctl
```

## Проверить конкретный порт с клиента

```bash
nc -vz host.example.local 443
nc -vz 10.0.0.20 8080
timeout 5 bash -c '</dev/tcp/host.example.local/443' && echo OK || echo FAIL
```

## Разница ошибок

### Connection refused

```text
TCP дошёл до хоста, но порт закрыт или сервис не слушает.
```

Проверить:

```bash
ss -lntp | grep ':PORT'
systemctl status <service>
journalctl -u <service> -n 100 --no-pager
```

### Timeout

```text
Пакеты не получают ответа: firewall, routing, service drop, security group, wrong IP.
```

Проверить:

```bash
ip r
ping -c 3 host
traceroute host
nc -vz -w 3 host port
sudo tcpdump -ni any host <ip> and port <port>
```

### No route to host

```text
Нет маршрута или ICMP reject/firewall.
```

Проверить:

```bash
ip r
ip rule
ip route get <ip>
```

## Проверить порт на удалённом сервере через SSH

```bash
ssh user@server 'ss -lntp | grep ":443" || true'
```

## Проверить с двух сторон

На сервере:

```bash
sudo tcpdump -ni any port 443
```

На клиенте:

```bash
nc -vz server 443
```

Если на сервере нет SYN — проблема до сервера: DNS/routing/firewall.  
Если SYN есть, но ответа нет — firewall/local service.  
Если SYN/SYN-ACK есть, но приложение не работает — выше L4: TLS/HTTP/app.

## Senior flow

```text
1. DNS name -> IP?
2. Route до IP есть?
3. TCP порт открыт?
4. Кто слушает порт?
5. Сервис слушает нужный interface?
6. Firewall разрешает?
7. App protocol отвечает?
8. TLS/HTTP корректны?
```

## Комментарий в заявку

```text
Проверил сетевую доступность сервиса: DNS-разрешение, маршрут и TCP-порт.
Порт <port> на <host> <доступен/недоступен>. 
По результатам проверки проблема находится на уровне <service/firewall/routing/app>.
```
