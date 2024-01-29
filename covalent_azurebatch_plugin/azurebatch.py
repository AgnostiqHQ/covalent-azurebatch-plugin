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

"""Azure Batch executor for the Covalent Dispatcher."""

import asyncio
import os
import tempfile
from datetime import timedelta
from functools import partial
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import cloudpickle as pickle
from azure.batch import BatchServiceClient, models
from azure.common.credentials import ServicePrincipalCredentials
from azure.identity import ClientSecretCredential
from azure.storage.blob import BlobServiceClient
from covalent._shared_files.config import get_config
from covalent._shared_files.logger import app_log
from covalent.executor.executor_plugins.remote_executor import RemoteExecutor
from pydantic import BaseModel

from .exceptions import BatchTaskFailedException, NoBatchTasksException
from .utils import _execute_partial_in_threadpool, _load_pickle_file


class ExecutorPluginDefaults(BaseModel):
    """
    Default configuration values for the executor
    """

    tenant_id: str = ""
    client_id: str = ""
    client_secret: str = ""
    batch_account_url: str = ""
    batch_account_domain: str = "batch.core.windows.net"
    storage_account_name: str = ""
    storage_account_domain: str = "blob.core.windows.net"
    base_image_uri: str = os.environ.get(
        "COVALENT_AZURE_BASE_IMAGE_URI", "covalent.azurecr.io/covalent-executor-base:latest"
    )
    pool_id: str = ""
    retries: int = 3
    time_limit: int = 300
    cache_dir: str = "/tmp/covalent"
    poll_freq: int = 30


class ExecutorInfraDefaults(BaseModel):
    """
    Configuration values for provisioning Azure Batch cloud infrastructure
    """

    prefix: Optional[str] = "covalent-batch"
    subscription_id: str
    owners: List[str] = []
    tenant_id: str
    client_id: str = ""
    client_secret: str = ""
    batch_account_url: str = ""
    batch_account_domain: str = "batch.core.windows.net"
    storage_account_name: str = ""
    storage_account_domain: str = "blob.core.windows.net"
    base_image_uri: str = os.environ.get(
        "COVALENT_AZURE_BASE_IMAGE_URI", "covalent.azurecr.io/covalent-executor-base:latest"
    )
    pool_id: str = ""
    retries: int = 3
    time_limit: int = 300
    cache_dir: str = "/tmp/covalent"
    poll_freq: int = 30
    covalent_package_version: str = ""
    create_batch_account: bool = True
    batch_account_name: str = ""
    batch_resource_group: str = ""


EXECUTOR_PLUGIN_NAME = "AzureBatchExecutor"

_EXECUTOR_PLUGIN_DEFAULTS = ExecutorPluginDefaults().dict()

FUNC_FILENAME = "func-{dispatch_id}-{node_id}.pkl"
RESULT_FILENAME = "result-{dispatch_id}-{node_id}.pkl"
STORAGE_CONTAINER_NAME = "covalent-assets"
JOB_NAME = "covalent-batch-{dispatch_id}-{node_id}"


class AzureBatchExecutor(RemoteExecutor):
    """Microsoft Azure Batch Executor."""

    def __init__(
        self,
        tenant_id: str = None,
        client_id: str = None,
        client_secret: str = None,
        batch_account_url: str = None,
        batch_account_domain: str = None,
        storage_account_name: str = None,
        storage_account_domain: str = None,
        base_image_uri: str = None,
        pool_id: str = None,
        retries: int = None,
        time_limit: float = None,  # Time in seconds
        cache_dir: str = None,
        poll_freq: int = None,
        **kwargs,
    ) -> None:
        """Azure Batch executor initialization."""
        super().__init__(**kwargs)

        self.tenant_id = tenant_id or get_config("executors.azurebatch.tenant_id")
        self.client_id = client_id or get_config("executors.azurebatch.client_id")
        self.client_secret = client_secret or get_config("executors.azurebatch.client_secret")
        self.batch_account_url = batch_account_url or get_config(
            "executors.azurebatch.batch_account_url"
        )
        self.batch_account_domain = batch_account_domain or get_config(
            "executors.azurebatch.batch_account_domain"
        )
        self.storage_account_name = storage_account_name or get_config(
            "executors.azurebatch.storage_account_name"
        )
        self.storage_account_domain = storage_account_domain or get_config(
            "executors.azurebatch.storage_account_domain"
        )
        self.base_image_uri = base_image_uri or get_config("executors.azurebatch.base_image_uri")
        self.pool_id = pool_id or get_config("executors.azurebatch.pool_id")
        self.retries = retries or get_config("executors.azurebatch.retries")
        self.time_limit = time_limit or get_config("executors.azurebatch.time_limit")
        self.cache_dir = cache_dir or get_config("executors.azurebatch.cache_dir")
        self.poll_freq = poll_freq or get_config("executors.azurebatch.poll_freq")

        config = {
            "tenant_id": self.tenant_id,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "batch_account_url": self.batch_account_url,
            "batch_account_domain": self.batch_account_domain,
            "storage_account_name": self.storage_account_name,
            "storage_account_domain": self.storage_account_domain,
            "base_image_uri": self.base_image_uri,
            "pool_id": self.pool_id,
            "retries": self.retries,
            "time_limit": self.time_limit,
            "cache_dir": self.cache_dir,
            "poll_freq": self.poll_freq,
        }
        self._debug_log("Starting Azure Batch Executor with config:")
        self._debug_log(config)

    def _dispatcher_side_init(self) -> None:
        """Initialization step before running any tasks."""
        Path(self.cache_dir).mkdir(parents=True, exist_ok=True)

    def _get_batch_service_client_credential(self) -> ServicePrincipalCredentials:
        """Get credential for blob service client."""
        return ServicePrincipalCredentials(
            client_id=self.client_id,
            secret=self.client_secret,
            tenant=self.tenant_id,
            resource=f"https://{self.batch_account_domain}/",
        )

    def _get_blob_service_client_credential(self) -> ClientSecretCredential:
        """Get credential for blob service client."""
        return ClientSecretCredential(
            client_id=self.client_id,
            client_secret=self.client_secret,
            tenant_id=self.tenant_id,
        )

    def _get_blob_service_client(self) -> BlobServiceClient:
        """Get Azure Blob client."""
        self._debug_log("Initializing blob storage client...")
        return BlobServiceClient(
            account_url=f"https://{self.storage_account_name}.{self.storage_account_domain}/",
            credential=self._get_blob_service_client_credential(),
        )

    def _get_batch_service_client(self) -> BatchServiceClient:
        """Get Azure Batch client."""
        self._debug_log("Initializing batch client...")
        return BatchServiceClient(
            credentials=self._get_batch_service_client_credential(),
            batch_url=self.batch_account_url,
        )

    def _validate_credentials(self, raise_exception: bool = True) -> bool:
        """Validate user-specified Microsoft Azure credentials or environment variables (configured before starting the server). Note: credentials passed should be those of a service principal rather than a developer account.

        Args:
            raise_exception (bool, optional): Status of whether to raise exception. Defaults to True.
        """
        if self.tenant_id and self.client_id and self.client_secret:
            self._debug_log("Credentials are valid.")
            return True

        elif raise_exception:
            raise ValueError(
                "Failed to validate credentials. Check credentials or that the environment variables were set before starting the Covalent server."
            )
        return False

    def _debug_log(self, message: str) -> None:
        """Debug log message template."""
        app_log.debug(f"Azure Batch Executor: {message}")

    async def run(self, function: Callable, args: List, kwargs: Dict, task_metadata: Dict) -> None:
        """Main run method for the Azure Batch executor."""
        self._debug_log("Validating credentials...")
        self._validate_credentials()

        self._debug_log("Dispatcher side initialization...")
        self._dispatcher_side_init()

        self._debug_log("Uploading task to Azure blob storage...")
        await self._upload_task(function, args, kwargs, task_metadata)

        self._debug_log("Submitting task to Batch service...")
        job_id = await self.submit_task(task_metadata)

        self._debug_log(f"Polling task with job id: {job_id}")
        await self._poll_task(job_id)

        self._debug_log("Terminating job...")
        await self._terminate_job(job_id)

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
        blob_service_client = self._get_blob_service_client()

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

    async def submit_task(self, task_metadata: Dict):
        """Submit task to Azure Batch service."""
        self._debug_log("Submitting task...")
        dispatch_id = task_metadata["dispatch_id"]
        node_id = task_metadata["node_id"]
        job_id = task_id = JOB_NAME.format(dispatch_id=dispatch_id, node_id=node_id)

        self._debug_log(f"Dispatch id: {dispatch_id}")
        self._debug_log(f"Node id: {node_id}")
        self._debug_log(f"Job id, task_id: {job_id, task_id}")

        task_container_settings = models.TaskContainerSettings(
            image_name=self.base_image_uri,
            container_run_options="--rm --workdir /covalent -u 0",
        )

        constraints = models.TaskConstraints(
            max_wall_clock_time=timedelta(seconds=self.time_limit),
            max_task_retry_count=self.retries,
        )

        covalent_task_func_filename_env = models.EnvironmentSetting(
            name="COVALENT_TASK_FUNC_FILENAME",
            value=FUNC_FILENAME.format(dispatch_id=dispatch_id, node_id=node_id),
        )
        covalent_result_filename_env = models.EnvironmentSetting(
            name="COVALENT_RESULT_FILENAME",
            value=RESULT_FILENAME.format(dispatch_id=dispatch_id, node_id=node_id),
        )
        azure_storage_account_env = models.EnvironmentSetting(
            name="AZURE_BLOB_STORAGE_ACCOUNT", value=self.storage_account_name
        )
        azure_storage_container_env = models.EnvironmentSetting(
            name="AZURE_BLOB_STORAGE_CONTAINER",
            value=STORAGE_CONTAINER_NAME.format(dispatch_id=dispatch_id, node_id=node_id),
        )
        azure_storage_account_domain_env = models.EnvironmentSetting(
            name="AZURE_BLOB_STORAGE_ACCOUNT_DOMAIN", value=self.storage_account_domain
        )

        task = models.TaskAddParameter(
            id=task_id,
            command_line="",
            container_settings=task_container_settings,
            constraints=constraints,
            environment_settings=[
                covalent_task_func_filename_env,
                covalent_result_filename_env,
                azure_storage_account_env,
                azure_storage_container_env,
                azure_storage_account_domain_env,
            ],
        )

        batch_client = self._get_batch_service_client()
        job = models.JobAddParameter(
            id=job_id, pool_info=models.PoolInformation(pool_id=self.pool_id)
        )
        batch_client.job.add(job)
        batch_client.task.add(job_id=job_id, task=task)
        return job_id

    async def get_status(self, job_id: str) -> Tuple[models.TaskState, int]:
        """Get the status of a batch task."""
        self._debug_log(f"Getting status for job id: {job_id}")
        batch_client = self._get_batch_service_client()

        partial_func = partial(batch_client.task.list, job_id)
        tasks = list(await _execute_partial_in_threadpool(partial_func))

        self._debug_log(f"Batch tasks list: {tasks}")
        if not tasks:
            raise NoBatchTasksException

        partial_func = partial(batch_client.task.get, job_id, tasks[0].id)
        cloud_task = await _execute_partial_in_threadpool(partial_func)

        self._debug_log(f"Cloud task execution info: {cloud_task.execution_info}")
        exit_code = cloud_task.execution_info.exit_code

        return tasks[0].state, exit_code

    async def _poll_task(self, job_id: str) -> None:
        """Poll task status until completion."""
        self._debug_log(f"Polling task status with job id {job_id}...")
        status = await self.get_status(job_id)

        while status != models.TaskState.completed:
            await asyncio.sleep(self.poll_freq)
            status, exit_code = await self.get_status(job_id)

        if exit_code != 0:
            raise BatchTaskFailedException(exit_code)

    async def _terminate_job(self, job_id: str) -> None:
        """Mark job as completed."""

        batch_client = self._get_batch_service_client()
        partial_func = partial(
            batch_client.job.terminate,
            job_id=job_id,
            terminate_reason="Completed",
        )

        await _execute_partial_in_threadpool(partial_func)

    async def cancel(self, job_id: str, reason: str = None) -> None:
        """Cancel an Azure Batch task."""
        self._debug_log(
            f"Cancelling Azure Batch task with job and task id {job_id} for reason {reason}..."
        )
        batch_service_client = self._get_batch_service_client()
        partial_func = partial(
            batch_service_client.task.terminate, job_id=job_id, task_id=job_id
        )  # Currently, there is only one task per job.
        await _execute_partial_in_threadpool(partial_func)
        self._debug_log("Task was cancelled.")

    def _download_result_from_blob(
        self, dispatch_id: str, node_id: str, local_result_filename: str
    ) -> None:
        """Download result from Azure blob."""
        self._debug_log(
            f"Downloading result from Azure blob to local filename {local_result_filename}..."
        )
        blob_service_client = self._get_blob_service_client()
        blob_client = blob_service_client.get_blob_client(
            container=STORAGE_CONTAINER_NAME.format(dispatch_id=dispatch_id, node_id=node_id),
            blob=RESULT_FILENAME.format(dispatch_id=dispatch_id, node_id=node_id),
        )

        with open(local_result_filename, "wb") as my_blob:
            download_stream = blob_client.download_blob()
            my_blob.write(download_stream.readall())

    async def query_result(self, task_metadata: Dict) -> Any:
        """Query result once task has completed."""
        self._debug_log("Querying result...")
        dispatch_id = task_metadata["dispatch_id"]
        node_id = task_metadata["node_id"]
        local_result_filename = os.path.join(
            self.cache_dir, RESULT_FILENAME.format(dispatch_id=dispatch_id, node_id=node_id)
        )

        partial_func = partial(
            self._download_result_from_blob, dispatch_id, node_id, local_result_filename
        )
        await _execute_partial_in_threadpool(partial_func)

        self._debug_log(f"Loading result object from local file {local_result_filename}...")
        partial_func = partial(_load_pickle_file, local_result_filename)
        return await _execute_partial_in_threadpool(partial_func)
