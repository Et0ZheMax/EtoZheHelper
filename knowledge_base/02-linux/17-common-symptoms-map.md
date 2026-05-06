---
type: decision_tree
domain: linux
tags: [linux, symptoms, troubleshooting, map]
risk: low
requires_root: false
---

# Common symptoms map

## Сайт не открывается

```text
DNS?
  getent hosts host
TCP?
  nc -vz host 443
TLS?
  curl -vk https://host
HTTP?
  curl -I https://host
Proxy?
  nginx logs
Backend?
  curl localhost:backend_port
Service?
  systemctl status app
Logs?
  journalctl -u app
```

## Сервис не стартует

```text
systemctl status
journalctl -u service
systemctl cat service
config validation
ss -lntp for port conflict
df -h / df -i
permissions
env file
```

## Сервер тормозит

```text
uptime/load
top
free -h
vmstat
iostat
ps cpu/mem
dmesg OOM
disk full
```

## DNS не работает

```text
cat /etc/resolv.conf
resolvectl status
getent hosts
dig @dns
search domain
NetworkManager/netplan
VPN overrides
```

## SSH не работает

```text
DNS/IP
nc port 22
ssh -vvv
sshd status
auth.log
keys permissions
AllowUsers/Groups
fail2ban
```

## Нет места

```text
df -h
df -i
du -xh
journalctl --disk-usage
docker system df
lsof +L1
```

## apt сломан

```text
ps apt/dpkg
lsof locks
dpkg --configure -a
apt -f install
apt update
repo/DNS/proxy
```

## sudo ругается hostname

```text
hostname
/etc/hostname
/etc/hosts
127.0.1.1 hostname
```

## AD login не работает

```text
date/timedatectl
DNS SRV
realm list
kinit
id user
sssctl domain-status
sssd logs
realm permit
```
