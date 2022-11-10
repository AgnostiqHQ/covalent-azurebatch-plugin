# Copyright 2021 Agnostiq Inc.
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

import os
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient
import cloudpickle as pickle

azure_storage_account = os.getenv("AZURE_STORAGE_ACCOUNT")
if not azure_storage_account:
    raise ValueError("Environment variable AZURE_STORAGE_CONTAINER was not found")

azure_storage_container = os.getenv("AZURE_STORAGE_CONTAINER")
if not azure_storage_container:
    raise ValueError("Environment variable AZURE_STORAGE_CONTAINER was not found")

func_filename = os.getenv("COVALENT_TASK_FUNC_FILENAME")
if not func_filename:
    raise ValueError("Environment variable FUNC_FILENAME was not found")

result_filename = os.getenv("RESULT_FILENAME")
if not result_filename:
    raise ValueError("Environment variable RESULT_FILENAME was not found")

local_func_filename = os.path.join("/covalent", func_filename)
local_result_filename = os.path.join("/covalent", result_filename)

azure_account_url = f"https://{azure_storage_account}.blob.core.windows.net/"

print(f"Using azure storage account: {azure_storage_account}")
print(f"Using azure storage account url: {azure_account_url}")
print(f"Using azure storage container: {azure_storage_container}")
print(f"Using function filename: {func_filename}")
print(f"Using result filename: {result_filename}")

# Configure azure client
print("Authenticating with azure storage... ")
credentials = DefaultAzureCredential()
blob_service_client = BlobServiceClient(azure_account_url, credentials)
container_client = blob_service_client.get_container_client(azure_storage_container)

# Download function pickle file
print(f"Downloading {local_func_filename} from azure storage... ")
with open(local_func_filename, "wb") as download_file:
    download_file.write(container_client.download_blob(func_filename).readall())

with open(local_func_filename, "rb") as f:
    function, args, kwargs = pickle.load(f)

# Execute pickle file
print(f"Executing {func_filename}... ")
result = function(*args, **kwargs)

# Upload result
print(f"Uploading {local_result_filename}... ")
with open(local_result_filename, "wb") as f:
    pickle.dump(result, f)
    container_client.upload_blob(result_filename,f)
