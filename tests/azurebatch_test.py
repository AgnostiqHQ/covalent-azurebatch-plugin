# Copyright 2022 Agnostiq Inc.
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


"""Unit tests for the Azure Batch executor plugin."""

import os
from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from azure.batch import models

from covalent_azurebatch_plugin.azurebatch import (
    FUNC_FILENAME,
    JOB_NAME,
    RESULT_FILENAME,
    STORAGE_CONTAINER_NAME,
    AzureBatchExecutor,
)
from covalent_azurebatch_plugin.exceptions import BatchTaskFailedException, NoBatchTasksException


class TestAzureBatchExecutor:

    MOCK_TENANT_ID = "mock-tenant-id"
    MOCK_CLIENT_ID = "mock-client-id"
    MOCK_CLIENT_SECRET = "mock-client-secret"
    MOCK_BATCH_ACCOUNT_URL = "mock-batch-account-url"
    MOCK_BATCH_ACCOUNT_DOMAIN = "mock-batch-account-domain"
    MOCK_STORAGE_ACCOUNT_NAME = "mock-storage-account-name"
    MOCK_STORAGE_ACCOUNT_DOMAIN = "mock-storage-account-domain"
    MOCK_BASE_IMAGE_URI = "mock-base-image-uri"
    MOCK_POOL_ID = "mock-pool-id"
    MOCK_RETRIES = 2
    MOCK_TIME_LIMIT = 3
    MOCK_CACHE_DIR = "/tmp/covalent"
    MOCK_POLL_FREQ = 0.5
    MOCK_DISPATCH_ID = "mock-dispatch-id"
    MOCK_NODE_ID = 1
    MOCK_CONTAINER_NAME = STORAGE_CONTAINER_NAME
    MOCK_JOB_ID = "mock-job-id"

    @pytest.fixture
    def mock_executor_config(self):
        """Mock executor config values."""
        return {
            "tenant_id": self.MOCK_TENANT_ID,
            "client_id": self.MOCK_CLIENT_ID,
            "client_secret": self.MOCK_CLIENT_SECRET,
            "batch_account_url": self.MOCK_BATCH_ACCOUNT_URL,
            "batch_account_domain": self.MOCK_BATCH_ACCOUNT_DOMAIN,
            "storage_account_name": self.MOCK_STORAGE_ACCOUNT_NAME,
            "storage_account_domain": self.MOCK_STORAGE_ACCOUNT_DOMAIN,
            "base_image_uri": self.MOCK_BASE_IMAGE_URI,
            "pool_id": self.MOCK_POOL_ID,
            "retries": self.MOCK_RETRIES,
            "time_limit": self.MOCK_TIME_LIMIT,
            "cache_dir": self.MOCK_CACHE_DIR,
            "poll_freq": self.MOCK_POLL_FREQ,
        }

    @property
    def MOCK_TASK_METADATA(self):
        """Mock task metadata."""
        return {
            "dispatch_id": self.MOCK_DISPATCH_ID,
            "node_id": self.MOCK_NODE_ID,
        }

    @property
    def MOCK_ARGS(self):
        return [1]

    @property
    def MOCK_KWARGS(self):
        return {"y": 1}

    @property
    def MOCK_FUNC_FILENAME(self):
        return FUNC_FILENAME.format(dispatch_id=self.MOCK_DISPATCH_ID, node_id=self.MOCK_NODE_ID)

    @property
    def MOCK_RESULT_FILENAME(self):
        return RESULT_FILENAME.format(dispatch_id=self.MOCK_DISPATCH_ID, node_id=self.MOCK_NODE_ID)

    @pytest.fixture
    def mock_executor(self, mock_executor_config):
        """Mock Azure Batch executor fixture."""
        return AzureBatchExecutor(**mock_executor_config)

    def test_init_null_values(self, mock_executor_config, mocker):
        """Test Azure Batch executor initialization with null values."""
        mocker.patch(
            "covalent_azurebatch_plugin.azurebatch.get_config", return_value="MOCK_CONFIG"
        )
        batch_executor = AzureBatchExecutor()
        for executor_attr in mock_executor_config:
            assert getattr(batch_executor, executor_attr) == "MOCK_CONFIG"

    def test_init_non_null_values(self, mock_executor_config, mocker):
        """Test Azure Batch executor initialization with non-null values."""
        mocker.patch("covalent_azurebatch_plugin.azurebatch.get_config", return_value=None)
        batch_executor = AzureBatchExecutor(**mock_executor_config)
        for executor_attr in mock_executor_config:
            assert getattr(batch_executor, executor_attr) == mock_executor_config[executor_attr]

    def test_dispatcher_side_init(self, mocker, mock_executor):
        """Test the init method run on the dispatcher side."""
        path_mock = mocker.patch("covalent_azurebatch_plugin.azurebatch.Path")
        mock_executor._dispatcher_side_init()
        path_mock().mkdir.assert_called_once_with(parents=True, exist_ok=True)

    def test_get_blob_service_client_credential(self, mock_executor, mocker):
        """Test getting a blob service client with a credential."""
        client_secret_credential_mock = mocker.patch(
            "covalent_azurebatch_plugin.azurebatch.ClientSecretCredential"
        )
        credentials = mock_executor._get_blob_service_client_credential()
        client_secret_credential_mock.assert_called_once_with(
            client_id=mock_executor.client_id,
            client_secret=mock_executor.client_secret,
            tenant_id=mock_executor.tenant_id,
        )
        assert credentials == client_secret_credential_mock()

    def test_get_batch_service_client_credential(self, mock_executor, mocker):
        """Test getting a batch service client with a credential."""
        service_principal_credentials_mock = mocker.patch(
            "covalent_azurebatch_plugin.azurebatch.ServicePrincipalCredentials"
        )
        credentials = mock_executor._get_batch_service_client_credential()
        service_principal_credentials_mock.assert_called_once_with(
            client_id=mock_executor.client_id,
            secret=mock_executor.client_secret,
            tenant=mock_executor.tenant_id,
            resource=f"https://{mock_executor.batch_account_domain}/",
        )
        assert credentials == service_principal_credentials_mock()

    def test_get_blob_service_client(self, mock_executor, mocker):
        """Test Azure Batch executor blob client getter."""
        blob_service_client_mock = mocker.patch(
            "covalent_azurebatch_plugin.azurebatch.BlobServiceClient"
        )
        credential_mock = mocker.patch(
            "covalent_azurebatch_plugin.azurebatch.AzureBatchExecutor._get_blob_service_client_credential"
        )
        mock_executor._get_blob_service_client()
        account_url_mock = (
            f"https://{mock_executor.storage_account_name}.{mock_executor.storage_account_domain}/"
        )
        blob_service_client_mock.assert_called_once_with(
            account_url=account_url_mock, credential=credential_mock()
        )

    def test_get_batch_service_client(self, mock_executor, mocker):
        """Test Azure Batch executor batch client getter."""
        batch_service_client_mock = mocker.patch(
            "covalent_azurebatch_plugin.azurebatch.BatchServiceClient"
        )
        credential_mock = mocker.patch(
            "covalent_azurebatch_plugin.azurebatch.AzureBatchExecutor._get_batch_service_client_credential"
        )
        mock_executor._get_batch_service_client()
        batch_service_client_mock.assert_called_once_with(
            credentials=credential_mock(), batch_url=mock_executor.batch_account_url
        )

    @pytest.mark.asyncio
    async def test_run(self, mock_executor, mocker):
        """Test Azure Batch executor run method."""

        def mock_func(x, y):
            return x + y

        validate_credentials_mock = mocker.patch(
            "covalent_azurebatch_plugin.azurebatch.AzureBatchExecutor._validate_credentials",
        )
        upload_task_mock = mocker.patch(
            "covalent_azurebatch_plugin.azurebatch.AzureBatchExecutor._upload_task"
        )
        submit_task_mock = mocker.patch(
            "covalent_azurebatch_plugin.azurebatch.AzureBatchExecutor.submit_task",
            return_value=self.MOCK_JOB_ID,
        )
        poll_task_mock = mocker.patch(
            "covalent_azurebatch_plugin.azurebatch.AzureBatchExecutor._poll_task"
        )
        terminate_mock = mocker.patch(
            "covalent_azurebatch_plugin.azurebatch.AzureBatchExecutor._terminate_job"
        )
        query_result_mock = mocker.patch(
            "covalent_azurebatch_plugin.azurebatch.AzureBatchExecutor.query_result",
            return_value="MOCK_RESULT",
        )

        assert (
            await mock_executor.run(
                mock_func, self.MOCK_ARGS, self.MOCK_KWARGS, self.MOCK_TASK_METADATA
            )
            == "MOCK_RESULT"
        )

        validate_credentials_mock.assert_called_once_with()
        upload_task_mock.assert_called_once_with(
            mock_func, self.MOCK_ARGS, self.MOCK_KWARGS, self.MOCK_TASK_METADATA
        )
        submit_task_mock.assert_called_once_with(self.MOCK_TASK_METADATA)
        poll_task_mock.assert_called_once_with(self.MOCK_JOB_ID)
        terminate_mock.assert_called_once_with(self.MOCK_JOB_ID)
        query_result_mock.assert_called_once_with(self.MOCK_TASK_METADATA)

    @pytest.mark.parametrize(
        "tenant_id,client_id,client_secret",
        [
            (None, None, None),
            ("mock-tenant-id", "mock-client-id", None),
            ("mock-tenant-id", "mock-client-id", "mock-cllient-secret"),
        ],
    )
    def test_validate_credentials(self, mock_executor, tenant_id, client_id, client_secret):
        """Test Azure Batch executor credential validation."""
        mock_executor.tenant_id = tenant_id
        mock_executor.client_id = client_id
        mock_executor.client_secret = client_secret

        credentials = mock_executor._validate_credentials(raise_exception=False)
        if tenant_id and client_id and client_secret:
            assert credentials is True
        else:
            assert credentials is False

    @pytest.mark.parametrize(
        "tenant_id,client_id,client_secret",
        [
            (None, None, None),
            ("mock-tenant-id", "mock-client-id", None),
            ("mock-tenant-id", None, "mock-cllient-secret"),
            (None, "mock-client-id", "mock-cllient-secret"),
        ],
    )
    def test_validate_credentials_exception_raised(
        self, tenant_id, client_id, client_secret, mock_executor
    ):
        """Test Azure Batch executor credential validation exception being raised."""
        mock_executor.tenant_id = tenant_id
        mock_executor.client_id = client_id
        mock_executor.client_secret = client_secret

        with pytest.raises(ValueError):
            mock_executor._validate_credentials()

    @pytest.mark.asyncio
    async def test_poll_task(self, mock_executor, mocker):
        """Test Azure Batch executor task polling."""
        asyncio_sleep_mock = mocker.patch("covalent_azurebatch_plugin.azurebatch.asyncio.sleep")
        mocker.patch(
            "covalent_azurebatch_plugin.azurebatch.AzureBatchExecutor._validate_credentials"
        )
        async_get_status_mock = AsyncMock(
            side_effect=[
                (models.TaskState.preparing, None),
                (models.TaskState.running, None),
                (models.TaskState.completed, 0),
            ],
        )
        mocker.patch(
            "covalent_azurebatch_plugin.azurebatch.AzureBatchExecutor.get_status",
            side_effect=async_get_status_mock,
        )

        await mock_executor._poll_task(self.MOCK_JOB_ID)
        asyncio_sleep_mock.assert_has_calls(
            [mocker.call(self.MOCK_POLL_FREQ), mocker.call(self.MOCK_POLL_FREQ)]
        )

    @pytest.mark.asyncio
    async def test_poll_task_exception_raised(self, mock_executor, mocker):
        """Test Azure Batch executor task polling."""
        mocker.patch("covalent_azurebatch_plugin.azurebatch.asyncio.sleep")
        mocker.patch(
            "covalent_azurebatch_plugin.azurebatch.AzureBatchExecutor._validate_credentials"
        )
        async_get_status_mock = AsyncMock(
            side_effect=[
                (models.TaskState.preparing, None),
                (models.TaskState.running, None),
                (models.TaskState.completed, -1),
            ],
        )
        mocker.patch(
            "covalent_azurebatch_plugin.azurebatch.AzureBatchExecutor.get_status",
            side_effect=async_get_status_mock,
        )

        with pytest.raises(BatchTaskFailedException):
            await mock_executor._poll_task(self.MOCK_JOB_ID)

    @pytest.mark.asyncio
    async def test_get_status(self, mock_executor, mocker):
        """Test Azure Batch executor get status method."""

        class MockExecutionInfo:
            def __init__(self, exit_code=0):
                self.exit_code = exit_code

        class MockTask:
            def __init__(self, state, task_id, execution_info=MockExecutionInfo()) -> None:
                self.state = state
                self.id = task_id
                self.execution_info = execution_info

        mocker.patch(
            "covalent_azurebatch_plugin.azurebatch.AzureBatchExecutor._validate_credentials"
        )
        batch_service_client_mock = MagicMock()
        mocker.patch(
            "covalent_azurebatch_plugin.azurebatch.AzureBatchExecutor._get_batch_service_client",
            return_value=batch_service_client_mock,
        )
        batch_service_client_mock.task.list.return_value = [
            MockTask(models.TaskState.completed, 1)
        ]
        batch_service_client_mock.task.get.return_value = MockTask(models.TaskState.completed, 1)
        state, exit_code = await mock_executor.get_status(self.MOCK_JOB_ID)
        assert state == models.TaskState.completed
        assert exit_code == 0

    @pytest.mark.asyncio
    async def test_get_status_no_task_exception(self, mock_executor, mocker):
        """Test Azure Batch executor get status method exception."""
        mocker.patch(
            "covalent_azurebatch_plugin.azurebatch.AzureBatchExecutor._validate_credentials"
        )
        batch_service_client_mock = MagicMock()
        mocker.patch(
            "covalent_azurebatch_plugin.azurebatch.AzureBatchExecutor._get_batch_service_client",
            return_value=batch_service_client_mock,
        )
        batch_service_client_mock.task.list.return_value = []
        with pytest.raises(NoBatchTasksException):
            await mock_executor.get_status(self.MOCK_JOB_ID)

    def test_debug_log(self, mock_executor, mocker):
        """Test Azure Batch executor debug logging."""
        app_log_mock = mocker.patch("covalent_azurebatch_plugin.azurebatch.app_log")
        mock_executor._debug_log("mock-message")
        app_log_mock.debug.assert_called_once_with("Azure Batch Executor: mock-message")

    def test_upload_task_to_blob(self, mock_executor, mocker):
        """Test Azure Batch executor upload task to blob."""

        def mock_func(x, y):
            return x + y

        mocker.patch(
            "covalent_azurebatch_plugin.azurebatch.AzureBatchExecutor._validate_credentials"
        )
        blob_service_client_mock = mocker.patch(
            "covalent_azurebatch_plugin.azurebatch.AzureBatchExecutor._get_blob_service_client"
        )

        mock_executor._upload_task_to_blob(
            self.MOCK_DISPATCH_ID,
            self.MOCK_NODE_ID,
            mock_func,
            self.MOCK_ARGS,
            self.MOCK_KWARGS,
            self.MOCK_CONTAINER_NAME,
        )
        blob_service_client_mock().get_blob_client.assert_called_once_with(
            container=self.MOCK_CONTAINER_NAME, blob=self.MOCK_FUNC_FILENAME
        )

    @pytest.mark.asyncio
    async def test_upload_task(self, mock_executor, mocker):
        """Test Azure Batch executor upload task method."""

        def mock_func(x, y):
            return x + y

        upload_task_to_blob_mock = mocker.patch(
            "covalent_azurebatch_plugin.azurebatch.AzureBatchExecutor._upload_task_to_blob"
        )
        await mock_executor._upload_task(
            mock_func, self.MOCK_ARGS, self.MOCK_KWARGS, self.MOCK_TASK_METADATA
        )
        upload_task_to_blob_mock.assert_called_once_with(
            self.MOCK_DISPATCH_ID,
            self.MOCK_NODE_ID,
            mock_func,
            self.MOCK_ARGS,
            self.MOCK_KWARGS,
            self.MOCK_CONTAINER_NAME,
        )

    @pytest.mark.asyncio
    async def test_query_result(self, mock_executor, mocker):
        """Test Azure Batch executor query result method."""
        download_result_from_blob_mock = mocker.patch(
            "covalent_azurebatch_plugin.azurebatch.AzureBatchExecutor._download_result_from_blob"
        )
        load_pickle_file_mock = mocker.patch(
            "covalent_azurebatch_plugin.azurebatch._load_pickle_file"
        )
        await mock_executor.query_result(self.MOCK_TASK_METADATA)
        local_result_filename = os.path.join(self.MOCK_CACHE_DIR, self.MOCK_RESULT_FILENAME)
        download_result_from_blob_mock.assert_called_once_with(
            self.MOCK_DISPATCH_ID, self.MOCK_NODE_ID, local_result_filename
        )
        load_pickle_file_mock.assert_called_with(local_result_filename)

    @pytest.mark.asyncio
    async def test_download_result_from_blob(self, mock_executor, mocker):
        """Test Azure Batch executor download result from blob method."""
        blob_service_client_mock = mocker.patch(
            "covalent_azurebatch_plugin.azurebatch.AzureBatchExecutor._get_blob_service_client"
        )
        local_result_filename = os.path.join(self.MOCK_CACHE_DIR, self.MOCK_RESULT_FILENAME)
        open_file_mock = mocker.patch("builtins.open", mocker.mock_open())
        mock_executor._download_result_from_blob(
            self.MOCK_DISPATCH_ID, self.MOCK_NODE_ID, local_result_filename
        )
        blob_service_client_mock().get_blob_client.assert_called_once_with(
            container=self.MOCK_CONTAINER_NAME, blob=self.MOCK_RESULT_FILENAME
        )
        open_file_mock().write.assert_called_once_with(
            blob_service_client_mock().get_blob_client().download_blob().readall()
        )

    @pytest.mark.asyncio
    async def test_cancel(self, mock_executor, mocker):
        """Test Azure Batch executor cancel method."""
        batch_service_client_mock = mocker.patch(
            "covalent_azurebatch_plugin.azurebatch.AzureBatchExecutor._get_batch_service_client"
        )
        job_id = JOB_NAME.format(dispatch_id=self.MOCK_DISPATCH_ID, node_id=self.MOCK_NODE_ID)
        await mock_executor.cancel(job_id, reason="mock-reason")
        batch_service_client_mock().task.terminate.assert_called_once_with(
            job_id=job_id, task_id=job_id
        )

    @pytest.mark.asyncio
    async def test_submit_task(self, mock_executor, mocker):
        """Test Azure Batch executor submit task method."""
        models_mock = mocker.patch("covalent_azurebatch_plugin.azurebatch.models")
        batch_service_client_mock = mocker.patch(
            "covalent_azurebatch_plugin.azurebatch.AzureBatchExecutor._get_batch_service_client"
        )
        await mock_executor.submit_task(self.MOCK_TASK_METADATA)
        models_mock.TaskContainerSettings.assert_called_once_with(
            image_name=self.MOCK_BASE_IMAGE_URI,
            container_run_options='--rm --workdir /covalent -u 0',
        )
        models_mock.TaskConstraints.assert_called_once_with(
            max_wall_clock_time=timedelta(seconds=self.MOCK_TIME_LIMIT),
            max_task_retry_count=self.MOCK_RETRIES,
        )
        assert models_mock.EnvironmentSetting.mock_calls == [
            mocker.call(name="COVALENT_TASK_FUNC_FILENAME", value="func-mock-dispatch-id-1.pkl"),
            mocker.call(name="COVALENT_RESULT_FILENAME", value="result-mock-dispatch-id-1.pkl"),
            mocker.call(name="AZURE_BLOB_STORAGE_ACCOUNT", value="mock-storage-account-name"),
            mocker.call(name="AZURE_BLOB_STORAGE_CONTAINER", value="covalent-assets"),
            mocker.call(
                name="AZURE_BLOB_STORAGE_ACCOUNT_DOMAIN", value="mock-storage-account-domain"
            ),
        ]
        models_mock.TaskAddParameter.assert_called_once_with(
            id=JOB_NAME.format(dispatch_id=self.MOCK_DISPATCH_ID, node_id=self.MOCK_NODE_ID),
            command_line="",
            container_settings=models_mock.TaskContainerSettings(),
            constraints=models_mock.TaskConstraints(),
            environment_settings=[
                models_mock.EnvironmentSetting(),
                models_mock.EnvironmentSetting(),
                models_mock.EnvironmentSetting(),
                models_mock.EnvironmentSetting(),
                models_mock.EnvironmentSetting(),
            ],
        )
        models_mock.PoolInformation.assert_called_once_with(pool_id=self.MOCK_POOL_ID)
        models_mock.JobAddParameter.assert_called_once_with(
            id=JOB_NAME.format(dispatch_id=self.MOCK_DISPATCH_ID, node_id=self.MOCK_NODE_ID),
            pool_info=models_mock.PoolInformation(),
        )
        batch_service_client_mock().job.add.assert_called_once_with(models_mock.JobAddParameter())
        batch_service_client_mock().task.add.assert_called_once_with(
            job_id=JOB_NAME.format(dispatch_id=self.MOCK_DISPATCH_ID, node_id=self.MOCK_NODE_ID),
            task=models_mock.TaskAddParameter(),
        )
