# Copyright 2023 Agnostiq Inc.
#
# This file is part of Covalent.
#
# Licensed under the GNU Affero General Public License 3.0 (the "License").
# A copy of the License may be obtained with this software package or at
#
#      https://www.gnu.org/licenses/agpl-3.0.en.html
#
# Use of this file is prohibited except in compliance with the License. Any
# modifications or derivative works of this file must retain this copyright
# notice, and modified files must contain a notice indicating that they have
# been altered from the originals.
#
# Covalent is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE. See the License for more details.
#
# Relief from the License may be granted by purchasing a commercial license.

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

resource "azurerm_batch_account" "covalent" {
  name                = "${var.prefix}covalentbatch"
  resource_group_name = azurerm_resource_group.batch.name
  location            = azurerm_resource_group.batch.location

  storage_account_id                  = azurerm_storage_account.batch.id
  storage_account_authentication_mode = "StorageKeys"
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
