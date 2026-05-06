---
type: runbook
domain: linux
tags: [linux, sssd, realmd, ad, kerberos]
risk: medium
requires_root: sometimes
---

# SSSD / realmd / AD troubleshooting

## Базовые проверки

```bash
realm list
sssctl domain-list
sssctl domain-status example.local
id user@example.local
getent passwd user@example.local
```

## DNS SRV

```bash
dig _ldap._tcp.dc._msdcs.example.local SRV
dig _kerberos._tcp.example.local SRV
```

## Kerberos

```bash
kinit user@example.local
klist
```

## Логи

```bash
journalctl -u sssd -n 200 --no-pager
sudo tail -n 100 /var/log/sssd/sssd_*.log
```

## SSSD config

```bash
sudo cat /etc/sssd/sssd.conf
sudo sssctl config-check
```

Права должны быть строгие:

```bash
sudo chmod 600 /etc/sssd/sssd.conf
```

## Cache reset

Только если понимаешь последствия:

```bash
sudo systemctl stop sssd
sudo rm -rf /var/lib/sss/db/*
sudo systemctl start sssd
```

## Realm permit

```bash
realm list
sudo realm permit user@example.local
sudo realm permit -g group@example.local
```

## Частые причины

```text
- DNS не видит DC/SRV;
- время не синхронизировано;
- sssd cache stale;
- user не permitted;
- доменная группа не резолвится;
- sudoers group name написан неверно;
- krb5 ticket expired;
- компьютерный аккаунт в AD сломан.
```

## Senior flow

```text
1. DNS SRV
2. time sync
3. realm list
4. kinit
5. id/getent
6. sssctl domain-status
7. sssd logs
8. permit/sudoers
```
