# Terraform troubleshooting

## Init fails

```bash
terraform init -upgrade
```

Проверить:
- provider source;
- internet/proxy;
- versions.tf;
- lock file.

## State lock

Не снимай lock без понимания причины.

```bash
terraform force-unlock <LOCK_ID>
```

## Drift

```bash
terraform plan
```

Если ресурс изменили руками, Terraform покажет diff.

## Import

```bash
terraform import resource.type.name external-id
```

## Validate

```bash
terraform fmt -recursive
terraform validate
terraform plan -out=tfplan
```
