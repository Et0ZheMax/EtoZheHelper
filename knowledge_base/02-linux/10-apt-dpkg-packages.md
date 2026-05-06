---
type: runbook
domain: linux
tags: [linux, apt, dpkg, packages, locks]
risk: medium
requires_root: true
---

# apt/dpkg troubleshooting

## Когда использовать

- apt завис;
- package install failed;
- dpkg interrupted;
- lock file;
- repo недоступен;
- unmet dependencies.

## Базовая диагностика

```bash
sudo apt update
sudo apt -f install
sudo dpkg --configure -a
```

## Locks

Симптом:

```text
Could not get lock /var/lib/dpkg/lock-frontend
```

Проверить:

```bash
ps aux | grep -E 'apt|dpkg|unattended'
sudo lsof /var/lib/dpkg/lock-frontend
sudo lsof /var/lib/dpkg/lock
```

Не удаляй lock сразу. Сначала пойми, живой ли процесс.

## Если dpkg был прерван

```bash
sudo dpkg --configure -a
sudo apt -f install
```

## Проверить held packages

```bash
apt-mark showhold
```

## Список установленных

```bash
dpkg -l | grep <name>
apt policy <package>
```

## Repo/DNS/proxy

```bash
cat /etc/apt/sources.list
ls /etc/apt/sources.list.d/
sudo apt update
resolvectl status
curl -I http://archive.ubuntu.com
```

## Очистка cache

```bash
sudo apt clean
sudo apt autoclean
sudo apt autoremove
```

## Переустановка пакета

```bash
sudo apt install --reinstall <package>
```

## Senior safe flow

```text
1. проверить активные apt/dpkg процессы
2. не удалять lock, если процесс жив
3. dpkg --configure -a
4. apt -f install
5. проверить repo/DNS
6. повторить install
7. записать причину
```
