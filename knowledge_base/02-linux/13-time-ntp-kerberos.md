---
type: runbook
domain: linux
tags: [linux, time, ntp, kerberos, chrony, timedatectl]
risk: medium
requires_root: sometimes
---

# Time, NTP, Kerberos

## Почему важно

Kerberos и AD чувствительны к расхождению времени. Даже если DNS и пароль правильные, логин может падать из-за времени.

## Проверить время

```bash
date
timedatectl
```

## systemd-timesyncd

```bash
systemctl status systemd-timesyncd
timedatectl timesync-status
```

## chrony

```bash
chronyc tracking
chronyc sources -v
systemctl status chrony
```

## NTP порты

```text
UDP 123
```

## Timezone

```bash
timedatectl list-timezones | grep Moscow
sudo timedatectl set-timezone Europe/Moscow
```

## Включить NTP

```bash
sudo timedatectl set-ntp true
```

## Kerberos checks

```bash
klist
kinit user@example.local
klist
```

## Частые проблемы

```text
- время отличается от DC;
- timezone визуально путает, но UTC корректный;
- NTP недоступен;
- systemd-timesyncd и chrony конфликтуют;
- DNS SRV AD не находятся;
- krb5.conf указывает не туда.
```

## Senior flow для AD auth

```text
1. date/timedatectl
2. DNS SRV records
3. kinit
4. realm list
5. sssctl domain-status
6. auth logs
```
