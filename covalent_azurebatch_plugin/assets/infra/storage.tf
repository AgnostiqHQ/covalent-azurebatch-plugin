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

resource "azurerm_container_registry" "batch" {
  name                = "${var.prefix}covalentbatch"
  resource_group_name = var.create_batch_account ? azurerm_resource_group.batch[0].name : data.azurerm_resource_group.batch[0].name
  location            = var.region

  sku = "Basic"

  provisioner "local-exec" {
    interpreter = ["/bin/bash", "-c"]
    command     = <<EOL
      set -eu -o pipefail
      docker build --no-cache --build-arg COVALENT_BASE_IMAGE=python:3.8-slim-bullseye --build-arg COVALENT_PACKAGE_VERSION=${var.covalent_package_version} --tag ${self.login_server}/covalent-executor-base:latest .
      az acr login --name ${self.name}
      docker push -a ${self.login_server}/covalent-executor-base
    EOL
  }
}

resource "azurerm_storage_account" "batch" {
  name                = "${var.prefix}covalentbatch"
  resource_group_name = var.create_batch_account ? azurerm_resource_group.batch[0].name : data.azurerm_resource_group.batch[0].name
  location            = var.region

  account_tier             = "Standard"
  account_replication_type = "LRS"
}

resource "azurerm_storage_container" "assets" {
  name                  = "covalent-assets"
  storage_account_name  = azurerm_storage_account.batch.name
  container_access_type = "private"
}
