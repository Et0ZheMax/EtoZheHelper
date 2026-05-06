---
type: runbook
domain: linux
tags: [linux, network, routing, firewall, ufw, nftables, iptables]
risk: medium
requires_root: sometimes
---

# Network, routing, firewall

## Быстрая диагностика

```bash
ip -br a
ip r
ip rule
ip route get 8.8.8.8
ip route get <target_ip>
ss -tulpn
```

## Проверить интерфейсы

```bash
ip link
ip addr show
ethtool <iface>
```

Если `ethtool` нет:

```bash
sudo apt install ethtool
```

## Маршрут до IP

```bash
ip route get 10.0.0.20
traceroute 10.0.0.20
tracepath 10.0.0.20
```

## Проверить default route

```bash
ip r | grep default
```

## Проверить порт

```bash
nc -vz host 443
```

## UFW

```bash
sudo ufw status verbose
sudo ufw status numbered
```

Разрешить порт:

```bash
sudo ufw allow 443/tcp
```

## iptables

```bash
sudo iptables -S
sudo iptables -L -n -v
```

## nftables

```bash
sudo nft list ruleset
```

## firewalld

```bash
sudo firewall-cmd --state
sudo firewall-cmd --list-all
```

## tcpdump

```bash
sudo tcpdump -ni any host 10.0.0.20
sudo tcpdump -ni any port 443
sudo tcpdump -ni any 'tcp[tcpflags] & tcp-syn != 0'
```

## Диагностика TCP handshake

На сервере:

```bash
sudo tcpdump -ni any host <client_ip> and port <port>
```

На клиенте:

```bash
nc -vz <server_ip> <port>
```

Интерпретация:

```text
SYN нет на сервере        -> проблема до сервера
SYN есть, SYN-ACK нет     -> firewall/service/server issue
SYN/SYN-ACK/ACK есть      -> TCP OK, смотри приложение/TLS
RST                       -> порт закрыт или приложение отказало
```

## MTU issues

Симптомы:
- маленькие запросы работают, большие виснут;
- VPN/туннель;
- TLS handshake странно зависает.

Проверка:

```bash
ping -M do -s 1472 host
ping -M do -s 1400 host
tracepath host
```

## Senior flow

```text
1. IP/interface up?
2. Route selected?
3. DNS correct?
4. TCP port reachable?
5. Firewall local?
6. Firewall between nodes?
7. tcpdump confirms packets?
8. App protocol responds?
```
