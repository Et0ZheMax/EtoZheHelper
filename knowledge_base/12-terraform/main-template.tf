terraform {
  required_version = ">= 1.6.0"

  required_providers {
    example = {
      source  = "example/example"
      version = "~> 1.0"
    }
  }
}

provider "example" {
  # Configure provider here
}

resource "example_resource" "main" {
  name = var.name
}

output "resource_id" {
  value = example_resource.main.id
}
