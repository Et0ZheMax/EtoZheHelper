# Ansible

## Базовые команды

```bash
ansible all -i inventory.ini -m ping
ansible-playbook -i inventory.ini playbook.yml
ansible-playbook -i inventory.ini playbook.yml --check --diff
ansible-playbook -i inventory.ini playbook.yml -K
```

## Ключи

- `-i` inventory
- `-m` module
- `-a` arguments
- `-b` become/sudo
- `-K` ask become password
- `--check` dry-run
- `--diff` показать изменения
- `--limit` ограничить хосты
- `-vvv` debug

## Структура роли

```text
roles/myrole/
├─ defaults/main.yml
├─ vars/main.yml
├─ tasks/main.yml
├─ handlers/main.yml
├─ templates/
├─ files/
└─ README.md
```
