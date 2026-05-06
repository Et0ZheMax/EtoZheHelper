---
type: cheatsheet
domain: linux
tags: [linux, commands, cheatsheet]
risk: low
requires_root: false
---

# Linux command cheatsheet

## System

```bash
hostnamectl
uptime
date
timedatectl
uname -a
lsb_release -a
```

## Network

```bash
ip -br a
ip r
ip route get 8.8.8.8
ss -tulpn
nc -vz host 443
curl -vk https://host
```

## DNS

```bash
cat /etc/resolv.conf
resolvectl status
resolvectl query host
getent hosts host
dig host
dig @dns host
```

## Services

```bash
systemctl status service --no-pager
systemctl cat service
journalctl -u service -n 100 --no-pager
systemctl --failed
```

## Logs

```bash
journalctl -p err..alert -n 100 --no-pager
journalctl --since "1 hour ago"
dmesg -T | tail -100
```

## Disk

```bash
df -h
df -i
lsblk -f
du -xh /var | sort -h | tail
lsof +L1
```

## Performance

```bash
top
free -h
vmstat 1 5
ps aux --sort=-%cpu | head
ps aux --sort=-%mem | head
iostat -xz 1
```

## Users/permissions

```bash
whoami
id
groups
sudo -l
ls -la
stat file
namei -l /path/to/file
```

## Packages

```bash
apt policy package
dpkg -l | grep package
sudo apt update
sudo dpkg --configure -a
sudo apt -f install
```

## SSH

```bash
ssh -vvv user@host
ssh-keygen -R host
journalctl -u ssh -n 100 --no-pager
```
