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

output "acr_login_server" {
  value = azurerm_container_registry.batch.login_server
}

output "user_identity_resource_id" {
  value = azurerm_user_assigned_identity.batch.client_id
}

output "plugin_client_username" {
  value = azuread_application.batch.application_id
}

output "plugin_client_secret" {
  value     = azuread_service_principal_password.covalent_plugin.value
  sensitive = true
}

output "covalent_azurebatch_object" {
  value = <<EOT
    executor = ct.executor.AzureBatchExecutor(
        tenant_id="${var.tenant_id}",
        client_id="${azuread_application.batch.application_id}",
        client_secret=plugin_client_secret,
        batch_account_url="https://${azurerm_batch_account.covalent.account_endpoint}",
        storage_account_name="${azurerm_storage_account.batch.name}",
        pool_id="${azurerm_batch_pool.covalent.name}",
    )
EOT
}
