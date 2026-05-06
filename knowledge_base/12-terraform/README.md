# Terraform

## Команды

```bash
terraform init
terraform fmt
terraform validate
terraform plan
terraform apply
terraform destroy
```

## Базовая структура

```text
main.tf
variables.tf
outputs.tf
providers.tf
versions.tf
terraform.tfvars
```

## Принципы

- state защищать;
- secrets не хранить в tfvars в Git;
- перед apply всегда plan;
- модули делать маленькими;
- имена ресурсов стандартизировать;
- использовать variables/outputs.
