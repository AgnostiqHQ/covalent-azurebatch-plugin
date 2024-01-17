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

variable "prefix" {
  default     = "covalent"
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
  type        = list(string)
  default     = []
}

variable "vm_name" {
  description = "Name of the VM used in the Batch pool"
  default     = "Standard_A1_v2"
}

variable "covalent_package_version" {
  type        = string
  description = "Covalent version to be installed in the container, if not specified the latest stable version will be installed"
  default     = ""
}

variable "create_batch_account" {
  type        = bool
  description = "Whether to create a new Batch account or use an existing one"
  default     = true
}

variable "batch_account_name" {
  type        = string
  description = "Name of the Batch account to be used"
  default     = ""
}

variable "batch_resource_group" {
  type        = string
  description = "Name of the resource group containing the Batch account to be used"
  default     = ""
}
