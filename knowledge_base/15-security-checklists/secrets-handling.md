# Secrets handling

## Что считать секретом

- passwords;
- tokens;
- API keys;
- cookies;
- private keys;
- database URLs with credentials;
- OAuth client secrets;
- SSH keys;
- backup encryption keys.

## Где хранить

- Vault/secret manager;
- CI/CD protected variables;
- OS keyring;
- encrypted Ansible Vault;
- Kubernetes secrets with proper access control.

## Где не хранить

- Git;
- Markdown docs;
- screenshots;
- ticket comments;
- chat;
- Docker image layers;
- Terraform state without protection.

## Поиск секретов

```bash
grep -RniE "password|token|secret|apikey|api_key|private key" .
```

Инструменты:
- gitleaks
- trufflehog
- git-secrets
