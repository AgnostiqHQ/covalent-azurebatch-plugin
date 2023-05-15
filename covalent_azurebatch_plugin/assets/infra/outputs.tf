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
        batch_account_url="${azurerm_batch_account.covalent.account_endpoint}",
        storage_account_name="${azurerm_storage_account.batch.name}",
        pool_id="${azurerm_batch_pool.covalent.name}",
    )
EOT
}
