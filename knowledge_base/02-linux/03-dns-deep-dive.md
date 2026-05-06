---
type: runbook
domain: linux
tags: [linux, dns, resolved, networkmanager, netplan, ad]
risk: low
requires_root: false
---

# DNS deep dive на Linux

## Когда использовать

- имя не резолвится;
- shortname не работает, FQDN работает;
- доменный ввод Linux не работает;
- curl по имени падает, по IP работает;
- AD/Kerberos/SSSD ошибки.

## Базовый flow

```bash
hostnamectl
cat /etc/resolv.conf
resolvectl status
resolvectl query host.example.local
getent hosts host.example.local
dig host.example.local
dig @10.0.0.10 host.example.local
```

## `/etc/resolv.conf`

Проверить:

```bash
ls -l /etc/resolv.conf
cat /etc/resolv.conf
```

В Ubuntu часто это symlink на systemd-resolved stub:

```text
/etc/resolv.conf -> ../run/systemd/resolve/stub-resolv.conf
nameserver 127.0.0.53
```

Это нормально, если `resolvectl status` показывает правильные upstream DNS.

## Проверка search domain

```bash
resolvectl status | grep -i 'DNS Domain' -A2
resolvectl query server01
resolvectl query server01.example.local
```

Если FQDN работает, а shortname нет — проблема в search domain.

## NetworkManager

```bash
nmcli dev status
nmcli con show
nmcli dev show
```

Поставить DNS/search domain:

```bash
sudo nmcli con mod "<CONNECTION>" ipv4.dns "10.0.0.10 10.0.0.11"
sudo nmcli con mod "<CONNECTION>" ipv4.dns-search "example.local"
sudo nmcli con up "<CONNECTION>"
resolvectl flush-caches
```

## Netplan

```bash
ls -l /etc/netplan/
sudo netplan get
sudo netplan try
sudo netplan apply
```

Пример:

```yaml
network:
  version: 2
  ethernets:
    enp0s3:
      dhcp4: true
      nameservers:
        addresses: [10.0.0.10, 10.0.0.11]
        search: [example.local]
```

## systemd-resolved

```bash
systemctl status systemd-resolved
resolvectl statistics
sudo resolvectl flush-caches
sudo systemctl restart systemd-resolved
```

## Проверка AD SRV records

```bash
dig _ldap._tcp.dc._msdcs.example.local SRV
dig _kerberos._tcp.example.local SRV
```

Если SRV не находятся, realm/sssd/kerberos могут ломаться.

## DNS через конкретный сервер

```bash
dig @10.0.0.10 host.example.local
dig @10.0.0.10 _ldap._tcp.dc._msdcs.example.local SRV
```

## getent vs dig

`dig` спрашивает DNS напрямую.  
`getent hosts` использует NSS: `/etc/hosts`, DNS, mdns, sssd и порядок из `/etc/nsswitch.conf`.

```bash
grep '^hosts:' /etc/nsswitch.conf
getent hosts host.example.local
```

## Частые причины

```text
- DNS сервер не тот;
- search domain отсутствует;
- VPN перезаписал DNS;
- split DNS;
- /etc/resolv.conf сломан;
- systemd-resolved не запущен;
- NetworkManager и netplan конфликтуют;
- локальная запись /etc/hosts перекрывает DNS;
- AD SRV records недоступны;
- firewall блокирует 53/tcp или 53/udp.
```

## Проверить порт DNS

```bash
nc -vz 10.0.0.10 53
dig @10.0.0.10 example.local
```

UDP через nc не всегда показателен. Лучше dig.

## Комментарий в заявку

```text
Проверил DNS-настройки Linux-клиента: /etc/resolv.conf, systemd-resolved, upstream DNS, search domain и разрешение FQDN/shortname.
Выявлена проблема на уровне <DNS server/search domain/resolved/VPN>. После корректировки разрешение имён проверено через getent/resolvectl/dig.
```
