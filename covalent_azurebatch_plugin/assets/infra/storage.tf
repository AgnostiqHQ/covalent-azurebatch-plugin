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
  name                  = "covalent-assets"
  storage_account_name  = azurerm_storage_account.batch.name
  container_access_type = "private"
}
