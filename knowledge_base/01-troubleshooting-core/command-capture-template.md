# Шаблон фиксации диагностики

```bash
date
hostname
whoami
id
uptime
ip a
ip r
resolvectl status || systemd-resolve --status
df -h
df -i
free -h
systemctl --failed
journalctl -p warning..alert -n 100 --no-pager
```

## Как сохранять вывод

```bash
mkdir -p ~/diag
{
  echo "### DATE"; date
  echo "### HOSTNAME"; hostnamectl
  echo "### UPTIME"; uptime
  echo "### IP"; ip a
  echo "### ROUTES"; ip r
  echo "### DNS"; resolvectl status
  echo "### DISK"; df -h; df -i
  echo "### MEMORY"; free -h
  echo "### FAILED UNITS"; systemctl --failed
  echo "### JOURNAL"; journalctl -p warning..alert -n 200 --no-pager
} | tee ~/diag/diag-$(hostname)-$(date +%F-%H%M%S).log
```
