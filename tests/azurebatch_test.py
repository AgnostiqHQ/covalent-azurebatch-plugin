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


"""Unit tests for the Azure Batch executor plugin."""

import os
from unittest.mock import AsyncMock, MagicMock

import pytest
from azure.batch import models

from covalent_azurebatch_plugin.azurebatch import (
    FUNC_FILENAME,
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
                models.TaskState.preparing,
                models.TaskState.running,
                models.TaskState.completed,
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
    async def test_get_status_exit_code_exception(self, mock_executor, mocker):
        """Test Azure Batch executor get status method exception being raised when exit code is non-zero."""

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
        batch_service_client_mock.task.get.return_value = MockTask(
            models.TaskState.completed, 1, MockExecutionInfo(-1)
        )
        with pytest.raises(BatchTaskFailedException):
            await mock_executor.get_status(self.MOCK_JOB_ID)

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
        mocker.patch(
            "covalent_azurebatch_plugin.azurebatch.AzureBatchExecutor._validate_credentials"
        )
        blob_service_client_mock = mocker.patch(
            "covalent_azurebatch_plugin.azurebatch.AzureBatchExecutor._get_blob_service_client"
        )
        load_pickle_file_mock = mocker.patch(
            "covalent_azurebatch_plugin.azurebatch._load_pickle_file"
        )
        await mock_executor.query_result(self.MOCK_TASK_METADATA)
        blob_service_client_mock().get_blob_client().download_blob.assert_called_once_with(
            self.MOCK_RESULT_FILENAME
        )
        load_pickle_file_mock.assert_called_with(
            os.path.join(self.MOCK_CACHE_DIR, self.MOCK_RESULT_FILENAME)
        )

    @pytest.mark.asyncio
    async def test_cancel(self, mock_executor, mocker):
        """Test Azure Batch executor cancel method."""
        pass

    @pytest.mark.asyncio
    async def test_submit_task(self, mock_executor, mocker):
        """Test Azure Batch executor submit task method."""
        pass
