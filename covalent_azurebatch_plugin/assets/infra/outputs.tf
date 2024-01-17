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

output "acr_login_server" {
  value = azurerm_container_registry.batch.login_server
}

output "user_identity_resource_id" {
  value = azurerm_user_assigned_identity.batch.client_id
}

output "plugin_client_username" {
  value = azuread_application.batch.client_id
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
        batch_account_url="https://${var.create_batch_account ? azurerm_batch_account.covalent[0].account_endpoint : data.azurerm_batch_account.covalent[0].account_endpoint}",
        storage_account_name="${azurerm_storage_account.batch.name}",
        pool_id="${azurerm_batch_pool.covalent.name}",
    )
EOT
}
