variable "prefix" {
  description = "Unique prefix for a deployment"
}

variable "region" {
  default     = "East US"
  description = "Region in which resources are deployed"
}

variable "environment" {
  default     = "dev"
  description = "Deployment environment name"
}

variable "tenant_id" {
  description = "Azure tenant ID"
}

variable "subscription_id" {
  description = "Azure subscription ID"
}

variable "owners" {
  description = "List of owner IDs for the service principal credentials"
  type = list(str)
}
