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

#########################################
# User-managed identity assumed by Batch
#########################################

resource "azurerm_user_assigned_identity" "batch" {
  name                = "${var.prefix}covalentbatch"
  resource_group_name = azurerm_resource_group.batch.name
  location            = azurerm_resource_group.batch.location
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
  application_id = azuread_application.batch.application_id
  owners         = var.owners
}

resource "azurerm_role_assignment" "covalent_plugin_storage" {
  scope                = "/subscriptions/${var.subscription_id}"
  principal_id         = azuread_service_principal.batch.object_id
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
  principal_id         = azuread_service_principal.batch.object_id
  role_definition_name = azurerm_role_definition.covalent_batch.name
}
