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

"""Azure Batch executor for the Covalent Dispatcher."""

import asyncio
from typing import Any, Callable, Dict, List, Union

from azure.batch import BatchServiceClient, models
from azure.identity import ClientSecretCredential, DefaultAzureCredential
from azure.storage.blob import BlobServiceClient
from covalent._shared_files.config import get_config
from covalent._shared_files.logger import app_log
from covalent.executor.executor_plugins.remote_executor import RemoteExecutor

_EXECUTOR_PLUGIN_DEFAULTS = {
    "tenant_id": "",
    "client_id": "",
    "client_secret": "",
    "batch_account_url": "",
    "storage_account_name": "",
    "storage_account_domain": "blob.core.windows.net",
    "pool_id": "",
    "job_id": "",
    "retries": 3,
    "time_limit": 300,
    "cache_dir": "/tmp/covalent",
    "poll_freq": 10,
}

EXECUTOR_PLUGIN_NAME = "AzureBatchExecutor"

FUNC_FILENAME = "func-{dispatch_id}-{node_id}.pkl"
RESULT_FILENAME = "result-{dispatch_id}-{node_id}.pkl"
JOB_NAME = "covalent-batch-{dispatch_id}-{node_id}"
COVALENT_EXEC_BASE_URI = ""


class AzureBatchExecutor(RemoteExecutor):
    """Microsoft Azure Batch Executor."""

    def __init__(
        self,
        tenant_id: str = None,
        client_id: str = None,
        client_secret: str = None,
        batch_account_url: str = None,
        storage_account_name: str = None,
        storage_account_domain: str = None,
        pool_id: str = None,
        job_id: str = None,
        retries: int = None,
        time_limit: float = None,
        cache_dir: str = None,
        poll_freq: int = None,
    ) -> None:
        """Azure Batch executor initialization."""
        self.tenant_id = tenant_id or get_config("executors.azurebatch.tenant_id")
        self.client_id = client_id or get_config("executors.azurebatch.client_id")
        self.client_secret = client_secret or get_config("executors.azurebatch.client_secret")
        self.batch_account_url = batch_account_url or get_config(
            "executors.azurebatch.batch_account_url"
        )
        self.storage_account_name = storage_account_name or get_config(
            "executors.azurebatch.storage_account_name"
        )
        self.storage_account_domain = storage_account_domain or get_config(
            "executors.azurebatch.storage_account_domain"
        )
        self.pool_id = pool_id or get_config("executors.azurebatch.pool_id")
        self.job_id = job_id or get_config("executors.azurebatch.job_id")
        self.retries = retries or get_config("executors.azurebatch.retries")
        self.time_limit = time_limit or get_config("executors.azurebatch.time_limit")
        self.cache_dir = cache_dir or get_config("executors.azurebatch.cache_dir")
        self.poll_freq = poll_freq or get_config("executors.azurebatch.poll_freq")

        config = {
            "tenant_id": self.tenant_id,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "batch_account_url": self.batch_account_url,
            "storage_account_name": self.storage_account_name,
            "storage_account_domain": self.storage_account_domain,
            "pool_id": self.pool_id,
            "job_id": self.job_id,
            "retries": self.retries,
            "time_limit": self.time_limit,
            "cache_dir": self.cache_dir,
            "poll_freq": self.poll_freq,
        }
        self._debug_log("Starting Azure Batch Executor with config:")
        self._debug_log(config)

    def _get_blob_client(
        self, credentials: Union[bool, DefaultAzureCredential, ClientSecretCredential]
    ) -> BlobServiceClient:
        """Get Azure Blob client."""
        self._debug_log("Initializing blob storage client...")
        return BlobServiceClient(
            account_url=f"https://{self.storage_account_name}.{self.storage_account_domain}/",
            credentials=credentials,
        )

    def _get_batch_service_client(
        self, credentials: Union[bool, DefaultAzureCredential, ClientSecretCredential]
    ) -> BatchServiceClient:
        """Get Azure Batch client."""
        self._debug_log("Initializing batch client...")
        return BatchServiceClient(credentials=credentials, batch_url=self.batch_account_url)

    def _validate_credentials(
        self, raise_exception: bool = True
    ) -> Union[bool, DefaultAzureCredential, ClientSecretCredential]:
        """Validate user-specified Microsoft Azure credentials or environment variables (configured before starting the server). Note: credentials passed should be those of a service principal rather than a developer account.

        Args:
            raise_exception (bool, optional): Status of whether to raise exception. Defaults to True.
        """
        try:
            if self.tenant_id and self.client_id and self.client_secret:
                self._debug_log("Returning credentials from user-specified values.")
                return ClientSecretCredential(self.tenant_id, self.client_id, self.client_secret)
            else:
                self._debug_log("Returning default credentials.")
                return DefaultAzureCredential()
        except Exception as e:
            if raise_exception:
                raise e
            self._debug_log(
                f"Failed to validate credentials. Check credentials or that the environment variables were set before starting the Covalent server. Exception raised: {e}"
            )
            return False

    def _debug_log(self, message: str) -> None:
        """Debug log message template."""
        app_log.debug(f"Azure Batch Executor: {message}")

    async def run(self, function: Callable, args: List, kwargs: Dict, task_metadata: Dict) -> None:
        """Main run method for the Azure Batch executor."""
        dispatch_id = task_metadata["dispatch_id"]
        node_id = task_metadata["node_id"]

        self._debug_log(f"Executing Dispatch ID {dispatch_id} Node {node_id}...")

        self._debug_log("Validating credentials...")
        credential = self._validate_credentials()

        self._debug_log("Uploading task to Azure blob storage...")
        await self._upload_task(function, args, kwargs, task_metadata)

        self._debug_log("Submitting task to Batch service...")
        job_id = await self.submit_task(task_metadata, credential)

        self._debug_log(f"Job id: {job_id}")
        await self._poll_task(job_id)

        self._debug_log("Querying result...")
        return await self.query_result(task_metadata)

    async def _upload_task(self, function, args, kwargs, task_metadata):
        pass

    async def submit_task(self, task_metadata, credential):
        pass

    async def get_status(self, job_id):
        pass

    async def _poll_task(self, job_id) -> None:
        """Poll task status until completion."""
        self._debug_log(f"Polling task status with job id {job_id}...")
        credential = self._validate_credentials()
        batch_service_client = self._get_batch_service_client(credentials=credential)

        tasks = batch_service_client.task.list(job_id)
        self._debug_log(f"Tasks retrieved: {tasks}")

        while tasks[0].state != models.TaskState.completed:
            await asyncio.sleep(self.poll_freq)
            tasks = batch_service_client.task.list(job_id)

        # TODO: Add snippet to get exit code from task and raise exception/log.

    async def cancel(self, job_id, reason):
        pass

    async def query_result(self, task_metadata) -> Any:
        pass
