# Copyright 2023 Agnostiq Inc.
#
# This file is part of Covalent.
#
# Licensed under the Apache License 2.0 (the "License"). A copy of the
# License may be obtained with this software package or at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Use of this file is prohibited except in compliance with the License.
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

provider "azurerm" {
  tenant_id       = var.tenant_id
  subscription_id = var.subscription_id

  features {
    resource_group {
      prevent_deletion_if_contains_resources = false
    }
  }
}

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
  name                = "default"
  resource_group_name = azurerm_resource_group.batch.name

  account_name = azurerm_batch_account.covalent.name
  display_name = "Covalent Azure Plugin Default Pool"

  vm_size           = var.vm_name
  node_agent_sku_id = "batch.node.ubuntu 20.04"

  auto_scale {
    evaluation_interval = "PT15M"

    formula = <<EOF
      startingNumberOfVMs = 1;
      minNumberofVMs = 1;
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
    type                  = "DockerCompatible"
    container_image_names = ["${azurerm_container_registry.batch.login_server}/covalent-executor-base"]

    container_registries {
      registry_server           = azurerm_container_registry.batch.login_server
      user_assigned_identity_id = azurerm_user_assigned_identity.batch.id
    }
  }

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.batch.id]
  }
}
