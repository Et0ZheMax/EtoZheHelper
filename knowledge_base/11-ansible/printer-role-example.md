# Printer role idea

## Цель

Устанавливать принтеры через CUPS безопасно и повторяемо.

## Переменные

```yaml
printers:
  - name: prn-101
    uri: socket://10.0.0.50:9100
    ppd: canon.ppd
    default: true
```

## Tasks

```yaml
- name: Install cups
  apt:
    name:
      - cups
      - cups-client
    state: present
    update_cache: true

- name: Copy PPD
  copy:
    src: "{{ item.ppd }}"
    dest: "/tmp/{{ item.ppd }}"
  loop: "{{ printers }}"

- name: Add printer
  command: >
    lpadmin -p {{ item.name }} -E
    -v {{ item.uri }}
    -P /tmp/{{ item.ppd }}
  loop: "{{ printers }}"
  changed_when: true
```

## Acceptance criteria

- playbook проходит `--check`;
- повторный запуск идемпотентный или контролируемо changed;
- можно ограничить `--limit`;
- есть проверка очереди `lpstat -t`.
