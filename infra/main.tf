provider "azurerm" {
  tenant_id       = var.tenant_id
  subscription_id = var.subscription_id

  features {
    resource_group {
      prevent_deletion_if_contains_resources = false
    }
  }
}

data "azurerm_subscription" "current" {}

resource "azurerm_resource_group" "batch" {
  name     = "${var.prefix}-covalent-batch"
  location = var.region
}

resource "azurerm_container_registry" "batch" {
  name                = "${var.prefix}covalentbatch"
  resource_group_name = azurerm_resource_group.batch.name
  location            = azurerm_resource_group.batch.location

  sku = "Basic"

  provisioner "local-exec" {
    interpreter = ["/bin/bash", "-c"]
    command     = <<EOL
      docker build --build-arg COVALENT_BASE_IMAGE=python:3.8-slim-bullseye --tag ${self.login_server}/covalent-executor-base:latest .
      az acr login --name ${self.name}
      docker push -a ${self.login_server}/covalent-executor-base
    EOL
  }
}

resource "azurerm_storage_account" "batch" {
  name                = "${var.prefix}covalentbatch"
  resource_group_name = azurerm_resource_group.batch.name
  location            = azurerm_resource_group.batch.location

  account_tier             = "Standard"
  account_replication_type = "LRS"
}

resource "azurerm_storage_container" "assets" {
  name = "covalent-assets"
  storage_account_name = azurerm_storage_account.batch.name
  container_access_type = "private"
}

resource "azurerm_batch_account" "covalent" {
  name                = "${var.prefix}covalentbatch"
  resource_group_name = azurerm_resource_group.batch.name
  location            = azurerm_resource_group.batch.location

  storage_account_id                  = azurerm_storage_account.batch.id
  storage_account_authentication_mode = "StorageKeys"
}

resource "azurerm_user_assigned_identity" "batch" {
  name                = "${var.prefix}covalentbatch"
  resource_group_name = azurerm_resource_group.batch.name
  location            = azurerm_resource_group.batch.location
}

resource "azurerm_role_assignment" "batch_to_acr" {
  scope = data.azurerm_subscription.current.id
  principal_id = azurerm_user_assigned_identity.batch.principal_id
  role_definition_name = "AcrPull"
}

resource "azurerm_role_assignment" "batch_to_storage" {
  scope = data.azurerm_subscription.current.id
  principal_id = azurerm_user_assigned_identity.batch.principal_id
  role_definition_name = "Storage Blob Data Contributor"
}

resource "azurerm_batch_pool" "covalent" {
  name = "default"
  resource_group_name = azurerm_resource_group.batch.name

  account_name = azurerm_batch_account.covalent.name
  display_name = "Covalent Azure Plugin Default Pool"

  vm_size = "Standard_A1_v2"
  node_agent_sku_id = "batch.node.ubuntu 20.04"

  auto_scale {
    evaluation_interval = "PT15M"

    formula = <<EOF
      startingNumberOfVMs = 0;
      minNumberofVMs = 0;
      maxNumberofVMs = 25;
      pendingTaskSamplePercent = $PendingTasks.GetSamplePercent(180 * TimeInterval_Second);
      pendingTaskSamples = pendingTaskSamplePercent < 70 ? startingNumberOfVMs : avg($PendingTasks.GetSample(180 *   TimeInterval_Second));
      $TargetDedicatedNodes=max(minNumberofVMs,min(maxNumberofVMs, pendingTaskSamples));
EOF
  }

  storage_image_reference {
    publisher = "microsoft-azure-batch"
    offer     = "ubuntu-server-container"
    sku       = "20-04-lts"
    version   = "latest"
  }

  container_configuration {
    type = "DockerCompatible"
    container_image_names = ["${azurerm_container_registry.batch.login_server}/covalent-executor-base"]

    container_registries {
      registry_server = azurerm_container_registry.batch.login_server
      user_assigned_identity_id = azurerm_user_assigned_identity.batch.id
    }
  }

  identity {
    type = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.batch.id]
  }
}

resource "azuread_application" "batch" {
  description = "Covalent Azure Batch Plugin"
  display_name = "CovalentBatchPlugin"
  owners = var.owners
}

resource "azuread_service_principal" "batch" {
  application_id = azuread_application.batch.application_id
  owners = var.owners
}

resource "azurerm_role_assignment" "covalent_plugin_storage" {
  scope = data.azurerm_subscription.current.id
  principal_id = azuread_service_principal.batch.object_id
  role_definition_name = "Storage Blob Data Contributor"
}

resource "azuread_service_principal_password" "covalent_plugin" {
  end_date_relative = "672h" # 28 days
  service_principal_id = azuread_service_principal.batch.object_id
}

resource "azurerm_role_definition" "covalent_batch" {
  name = "${var.prefix}covalentbatch"
  scope = data.azurerm_subscription.current.id
  description = "Covalent Azure Batch Permissions"
  permissions {
    actions = [
      "Microsoft.Batch/*",
    ]
    not_actions = []
  }
}

resource "azurerm_role_assignment" "covalent_plugin_batch" {
  scope = data.azurerm_subscription.current.id
  principal_id = azuread_service_principal.batch.object_id
  role_definition_name = azurerm_role_definition.covalent_batch.name
}
