# Network / DNS

## Базовая диагностика

Linux:

```bash
ip a
ip r
ss -tulpn
resolvectl status
dig example.local
traceroute 10.0.0.10
nc -vz host 443
```

Windows:

```cmd
ipconfig /all
route print
nslookup example.local
tracert example.local
Test-NetConnection host -Port 443
```

## Модель

```text
L1 физика -> L2 VLAN/MAC -> L3 IP/routing -> L4 TCP/UDP -> L7 app/TLS/auth
```
