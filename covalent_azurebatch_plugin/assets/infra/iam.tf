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

#########################################
# User-managed identity assumed by Batch
#########################################

resource "azurerm_user_assigned_identity" "batch" {
  name                = "${var.prefix}covalentbatch"
  resource_group_name = var.create_batch_account ? azurerm_resource_group.batch[0].name : data.azurerm_resource_group.batch[0].name
  location            = var.region
}

resource "azurerm_role_assignment" "batch_to_acr" {
  scope                = "/subscriptions/${var.subscription_id}"
  principal_id         = azurerm_user_assigned_identity.batch.principal_id
  role_definition_name = "AcrPull"
}

resource "azurerm_role_assignment" "batch_to_storage" {
  scope                = "/subscriptions/${var.subscription_id}"
  principal_id         = azurerm_user_assigned_identity.batch.principal_id
  role_definition_name = "Storage Blob Data Contributor"
}

####################################################
# Service principal credentials for Covalent server
####################################################

resource "azuread_application" "batch" {
  description  = "Covalent Azure Batch Plugin"
  display_name = "CovalentBatchPlugin"
  owners       = var.owners
}

resource "azuread_service_principal" "batch" {
  client_id = azuread_application.batch.client_id
  owners    = var.owners
}

resource "azurerm_role_assignment" "covalent_plugin_storage" {
  scope                = "/subscriptions/${var.subscription_id}"
  principal_id         = azuread_service_principal.batch.id
  role_definition_name = "Storage Blob Data Contributor"
}

resource "azuread_service_principal_password" "covalent_plugin" {
  end_date_relative    = "672h" # 28 days
  service_principal_id = azuread_service_principal.batch.object_id
}

resource "azurerm_role_definition" "covalent_batch" {
  name        = "${var.prefix}covalentbatch"
  scope       = "/subscriptions/${var.subscription_id}"
  description = "Covalent Azure Batch Permissions"
  permissions {
    actions = [
      "Microsoft.Batch/*",
    ]
    not_actions = []
  }
}

resource "azurerm_role_assignment" "covalent_plugin_batch" {
  scope                = "/subscriptions/${var.subscription_id}"
  principal_id         = azuread_service_principal.batch.id
  role_definition_name = azurerm_role_definition.covalent_batch.name
}
