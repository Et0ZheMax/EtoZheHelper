# Runbook: DNS failure

## Симптом

Имя не резолвится, но IP доступен.

## Linux

```bash
ip r
resolvectl status
resolvectl query host.example.local
getent hosts host.example.local
dig host.example.local
```

## Windows

```cmd
ipconfig /all
nslookup host.example.local
nltest /dsgetdc:example.local
```

## Проверить

```text
[ ] DNS server
[ ] search domain
[ ] FQDN vs shortname
[ ] VPN/DHCP не перезаписал DNS
[ ] DNS SRV для AD
[ ] firewall до DNS
```

## Исправление

- поправить DHCP scope;
- поправить NetworkManager/netplan;
- flush cache;
- проверить DC/DNS service.
