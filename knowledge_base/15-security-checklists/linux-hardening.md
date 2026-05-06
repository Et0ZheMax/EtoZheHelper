# Linux hardening quick checklist

```text
[ ] Обновления включены/процесс есть
[ ] SSH root login отключён
[ ] Пароли SSH отключены, если ключи готовы
[ ] sudo только нужным группам
[ ] firewall настроен
[ ] лишние сервисы выключены
[ ] fail2ban/аналог при внешнем SSH
[ ] логи собираются
[ ] backups есть
[ ] секреты не лежат в /home/user/scripts
```

## Проверки

```bash
ss -tulpn
systemctl --failed
sudo ufw status verbose
sudo last -a | head
sudo journalctl -u ssh -n 100 --no-pager
```
