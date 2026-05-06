# DNS checklist

## Симптомы DNS

- IP пингуется, имя нет.
- FQDN работает, shortname нет.
- В домене не находится DC.
- Сервис открывается по IP, но не по имени.
- Kerberos/AD join ломается.

## Linux

```bash
resolvectl status
resolvectl query host.example.local
getent hosts host.example.local
dig host.example.local
dig _ldap._tcp.dc._msdcs.example.local SRV
```

## Windows

```cmd
ipconfig /all
nslookup host.example.local
nslookup -type=SRV _ldap._tcp.dc._msdcs.example.local
nltest /dsgetdc:example.local
```

## Что проверять

```text
[ ] DNS servers правильные
[ ] Search domain есть
[ ] FQDN работает
[ ] Shortname работает
[ ] SRV записи AD доступны
[ ] Нет split DNS конфликта
[ ] VPN не перезаписал DNS
[ ] Время на клиенте корректное
```
