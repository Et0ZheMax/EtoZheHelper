# Ansible Vault

## Создать vault

```bash
ansible-vault create group_vars/all/vault.yml
```

## Редактировать

```bash
ansible-vault edit group_vars/all/vault.yml
```

## Запуск

```bash
ansible-playbook playbook.yml --ask-vault-pass
```

## Использовать nano

```bash
export EDITOR=nano
ansible-vault edit group_vars/all/vault.yml
```

## Зачем Vault

- хранить много секретных переменных в зашифрованном виде;
- не держать пароли в plain text;
- коммитить зашифрованный файл в репозиторий.

Важно: сам пароль от vault всё равно нужно защищать отдельно.
