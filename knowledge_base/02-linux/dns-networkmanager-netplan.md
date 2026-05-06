# DNS на Ubuntu: systemd-resolved, NetworkManager, netplan

## Проверка

```bash
resolvectl status
cat /etc/resolv.conf
nmcli dev show
nmcli con show
ip r
ping -c 3 8.8.8.8
ping -c 3 example.local
getent hosts example.local
```

## Важные вопросы

- Есть ли DNS-сервер?
- Есть ли search domain?
- Используется ли NetworkManager или systemd-networkd?
- `/etc/resolv.conf` смотрит на systemd stub?
- Проблема только с shortname или с FQDN тоже?

## Проверка shortname

```bash
getent hosts server01
getent hosts server01.example.local
resolvectl query server01
resolvectl query server01.example.local
```

Если FQDN работает, а shortname нет — смотри search domain.

## NetworkManager: добавить DNS и search

```bash
nmcli con show
sudo nmcli con mod "<CONNECTION_NAME>" ipv4.dns "10.0.0.10 10.0.0.11"
sudo nmcli con mod "<CONNECTION_NAME>" ipv4.dns-search "example.local"
sudo nmcli con up "<CONNECTION_NAME>"
resolvectl flush-caches
```

## Netplan example

```yaml
network:
  version: 2
  ethernets:
    enp0s3:
      dhcp4: true
      nameservers:
        addresses:
          - 10.0.0.10
          - 10.0.0.11
        search:
          - example.local
```

Применить:

```bash
sudo netplan try
sudo netplan apply
```
