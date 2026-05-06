# GUI, GDM, X11, Wayland, VNC, xrdp

## Проверка GUI

```bash
systemctl status gdm3
loginctl
echo $XDG_SESSION_TYPE
ps aux | egrep 'Xorg|wayland|gnome|gdm'
```

## GDM включить

```bash
sudo systemctl enable gdm3
sudo systemctl restart gdm3
```

## xrdp

```bash
sudo apt install -y xrdp
sudo systemctl enable --now xrdp
systemctl status xrdp
ss -lntp | grep 3389
```

## Логи xrdp

```bash
journalctl -u xrdp -n 100 --no-pager
journalctl -u xrdp-sesman -n 100 --no-pager
```

## VNC: частые причины

- нет активной графической сессии;
- Wayland мешает X11 VNC;
- firewall;
- сервис VNC не запущен;
- x11-common/Xorg/GDM сломаны;
- пользователь не залогинен.

## Отключить Wayland для GDM

Файл:

```bash
sudo nano /etc/gdm3/custom.conf
```

Строка:

```ini
WaylandEnable=false
```

Применить:

```bash
sudo systemctl restart gdm3
```
