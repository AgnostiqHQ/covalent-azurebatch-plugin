# Copyright 2022 Agnostiq Inc.
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

import os

import cloudpickle as pickle
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient

work_dir = os.environ.get("EXECUTOR_WORKDIR", "/tmp")

azure_storage_account = os.getenv("AZURE_BLOB_STORAGE_ACCOUNT")
if not azure_storage_account:
    raise ValueError("Environment variable AZURE_STORAGE_CONTAINER was not found")

azure_storage_container = os.getenv("AZURE_BLOB_STORAGE_CONTAINER")
if not azure_storage_container:
    raise ValueError("Environment variable AZURE_STORAGE_CONTAINER was not found")

azure_storage_account_domain = os.getenv("AZURE_BLOB_STORAGE_ACCOUNT_DOMAIN")
if not azure_storage_account_domain:
    raise ValueError("Environment variable AZURE_BLOB_STORAGE_ACCOUNT_DOMAIN was not found")

covalent_func_filename = os.getenv("COVALENT_TASK_FUNC_FILENAME")
if not covalent_func_filename:
    raise ValueError("Environment variable FUNC_FILENAME was not found")

covalent_result_filename = os.getenv("COVALENT_RESULT_FILENAME")
if not covalent_result_filename:
    raise ValueError("Environment variable COVALENT_RESULT_FILENAME was not found")

local_func_filename = os.path.join(work_dir, covalent_func_filename)
local_result_filename = os.path.join(work_dir, covalent_result_filename)

azure_account_url = f"https://{azure_storage_account}.{azure_storage_account_domain}/"

print(f"Using azure storage account: {azure_storage_account}")
print(f"Using azure storage account url: {azure_account_url}")
print(f"Using azure storage container: {azure_storage_container}")
print(f"Using azure storage account domain: {azure_storage_account_domain}")
print(f"Using function filename: {covalent_func_filename}")
print(f"Using result filename: {covalent_result_filename}")
print(f"AZ_BATCH_NODE_ROOT_DIR: {os.getenv('AZ_BATCH_NODE_ROOT_DIR')}")
print(f"XDG_CONFIG_DIR: {os.getenv('XDG_CONFIG_DIR')}")
print(f"XDG_CACHE_HOME: {os.getenv('XDG_CACHE_HOME')}")
print(f"XDG_DATA_HOME: {os.getenv('XDG_DATA_HOME')}")

# Configure azure client
print("Authenticating with azure storage... ")
credentials = DefaultAzureCredential()
blob_service_client = BlobServiceClient(azure_account_url, credentials)
container_client = blob_service_client.get_container_client(azure_storage_container)

# Download function pickle file
print(f"Downloading {covalent_func_filename} from azure storage to {local_func_filename}... ")
with open(local_func_filename, "wb") as download_file:
    function_file_contents = container_client.download_blob(covalent_func_filename).readall()
    download_file.write(function_file_contents)

with open(local_func_filename, "rb") as f:
    function, args, kwargs = pickle.load(f)

# Execute pickle file
print(f"Executing {covalent_func_filename}... ")
result = function(*args, **kwargs)

# Upload result
with open(local_result_filename, "wb") as f:
    pickle.dump(result, f)

print(f"Uploading {local_result_filename}... ")
with open(local_result_filename, "rb") as f:
    container_client.upload_blob(covalent_result_filename, f)
