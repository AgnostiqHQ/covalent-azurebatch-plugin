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
import os
import tempfile
from functools import partial
from pathlib import Path
from typing import Any, Callable, Dict, List, Tuple, Union

import cloudpickle as pickle
from azure.batch import BatchServiceClient, models
from azure.identity import ClientSecretCredential, DefaultAzureCredential
from azure.storage.blob import BlobServiceClient
from covalent._shared_files.config import get_config
from covalent._shared_files.logger import app_log
from covalent.executor.executor_plugins.remote_executor import RemoteExecutor

from .exceptions import BatchTaskFailedException, NoBatchTasksException
from .utils import _execute_partial_in_threadpool, _load_pickle_file

_EXECUTOR_PLUGIN_DEFAULTS = {
    "tenant_id": "",
    "client_id": "",
    "client_secret": "",
    "batch_account_url": "",
    "storage_account_name": "covalentbatch",  # TODO - Change default to empty string after
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
STORAGE_CONTAINER_NAME = (
    "covalent-pickles"  # TODO - Change to dispatch / node id dependent name after
)
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

    def _runtime_init(self) -> None:
        """Initialization step before running any tasks."""
        Path(self.cache_dir).mkdir(parents=True, exist_ok=True)

    def _get_blob_service_client(
        self, credential: Union[bool, DefaultAzureCredential, ClientSecretCredential]
    ) -> BlobServiceClient:
        """Get Azure Blob client."""
        self._debug_log("Initializing blob storage client...")
        return BlobServiceClient(
            account_url=f"https://{self.storage_account_name}.{self.storage_account_domain}/",
            credential=credential,
        )

    def _get_batch_service_client(
        self, credential: Union[bool, DefaultAzureCredential, ClientSecretCredential]
    ) -> BatchServiceClient:
        """Get Azure Batch client."""
        self._debug_log("Initializing batch client...")
        return BatchServiceClient(credential=credential, batch_url=self.batch_account_url)

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
        self._runtime_init()

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

    def _upload_task_to_blob(
        self,
        dispatch_id: str,
        node_id: str,
        function: Callable,
        args: List,
        kwargs: Dict,
        container_name: str,
    ) -> None:
        """Upload task to Azure blob storage."""
        self._debug_log("Uploading task to Azure blob storage...")
        blob_service_client = self._get_blob_service_client(self._validate_credentials())

        with tempfile.NamedTemporaryFile(dir=self.cache_dir) as function_file:
            pickle.dump((function, args, kwargs), function_file)
            function_file.flush()
            blob_obj_filename = FUNC_FILENAME.format(dispatch_id=dispatch_id, node_id=node_id)
            blob_client = blob_service_client.get_blob_client(
                container=container_name, blob=blob_obj_filename
            )

            with open(file=function_file.name, mode="rb") as data:
                blob_client.upload_blob(data)

    async def _upload_task(
        self, function: Callable, args: List, kwargs: Dict, task_metadata: Dict
    ) -> None:
        """Async wrapper for task upload."""
        self._debug_log("Async wrapper for task upload to Azure blob...")

        dispatch_id = task_metadata["dispatch_id"]
        node_id = task_metadata["node_id"]
        container_name = STORAGE_CONTAINER_NAME.format(dispatch_id=dispatch_id, node_id=node_id)
        self._debug_log(f"Task metadata {task_metadata}.")

        partial_func = partial(
            self._upload_task_to_blob, dispatch_id, node_id, function, args, kwargs, container_name
        )
        await _execute_partial_in_threadpool(partial_func)

    async def submit_task(self, task_metadata, credential):
        pass

    async def get_status(self, job_id: str) -> Tuple[models.TaskState, int]:
        """Get the status of a batch task."""
        self._debug_log(f"Getting status for job id: {job_id}")
        credential = self._validate_credentials()
        batch_client = self._get_batch_service_client(credential)

        partial_func = partial(batch_client.task.list, job_id)
        tasks = await _execute_partial_in_threadpool(partial_func)

        self._debug_log(f"Batch tasks list: {tasks}")
        if len(tasks) == 0:
            raise NoBatchTasksException

        partial_func = partial(batch_client.task.get, job_id, tasks[0].id)
        cloud_task = await _execute_partial_in_threadpool(partial_func)

        self._debug_log(f"Cloud task execution info: {cloud_task.execution_info}")
        exit_code = cloud_task.execution_info.exit_code
        if exit_code != 0:
            raise BatchTaskFailedException(exit_code)

        return tasks[0].state, exit_code

    async def _poll_task(self, job_id: str) -> None:
        """Poll task status until completion."""
        self._debug_log(f"Polling task status with job id {job_id}...")
        status = await self.get_status(job_id)

        while status != models.TaskState.completed:
            await asyncio.sleep(self.poll_freq)
            status = await self.get_status(job_id)

    async def cancel(self, job_id, reason):
        pass

    async def query_result(self, task_metadata) -> Any:
        """Query result once task has completed."""
        self._debug_log("Querying result...")
        dispatch_id = task_metadata["dispatch_id"]
        node_id = task_metadata["node_id"]
        result_filename = RESULT_FILENAME.format(dispatch_id=dispatch_id, node_id=node_id)

        local_result_filename = os.path.join(self.cache_dir, result_filename)

        self._debug_log(
            f"Downloading result from Azure blob storage to {local_result_filename}..."
        )

        credential = self._validate_credentials()
        blob_service_client = self._get_blob_service_client(credential)

        container_name = STORAGE_CONTAINER_NAME.format(dispatch_id=dispatch_id, node_id=node_id)
        blob_client = blob_service_client.get_blob_client(container=container_name)

        self._debug_log(
            f"Downloading result object from blob to local file {local_result_filename}..."
        )
        partial_func = partial(blob_client.download_blob, result_filename)
        await _execute_partial_in_threadpool(partial_func)

        self._debug_log(f"Loading result object from local file {local_result_filename}...")
        partial_func = partial(_load_pickle_file, local_result_filename)
        return await _execute_partial_in_threadpool(partial_func)
