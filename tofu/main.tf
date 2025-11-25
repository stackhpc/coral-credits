terraform {
  required_providers {
    restapi = {
      source  = "Mastercard/restapi"
      version = "1.20.0"
    }
  }
}

provider "restapi" {
  alias                 = "coral"
  uri                   = var.coral_uri
  debug                 = false
  write_returns_object  = true
  create_returns_object = true
  id_attribute = "id"
  headers = {
    "Content-Type" = "application/json"
    Authorization  = "Bearer ${var.auth_token}"
  }
}

module "coral_tofu" {
    source = "git::https://github.com/stackhpc/coral-credits-tofu.git?ref=0.1.0"
    
    resource_provider_name = var.resource_provider_name
    resource_provider_email = var.resource_provider_email
    resource_provider_info_url = var.resource_provider_info_url
    allocations = var.allocations
    accounts = var.accounts
    resource_classes = var.resource_classes

    providers = {
        restapi.coral = restapi.coral
    }
}