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

from unittest.mock import MagicMock

import pytest

from covalent_azurebatch_plugin.azurebatch import AzureBatchExecutor


class TestAzureBatchExecutor:

    MOCK_TENANT_ID = "mock-tenant-id"
    MOCK_CLIENT_ID = "mock-client-id"
    MOCK_CLIENT_SECRET = "mock-client-secret"
    MOCK_BATCH_ACCOUNT_URL = "mock-batch-account-url"
    MOCK_STORAGE_ACCOUNT_NAME = "mock-storage-account-name"
    MOCK_STORAGE_ACCOUNT_DOMAIN = "mock-storage-account-domain"
    MOCK_POOL_ID = "mock-pool-id"
    MOCK_JOB_ID = "mock-job-id"
    MOCK_RETRIES = 2
    MOCK_TIME_LIMIT = 3
    MOCK_CACHE_DIR = "/tmp/covalent"
    MOCK_POLL_FREQ = 4
    MOCK_DISPATCH_ID = "mock-dispatch-id"
    MOCK_NODE_ID = 1

    @pytest.fixture
    def mock_executor_config(self):
        """Mock executor config values."""
        return {
            "tenant_id": self.MOCK_TENANT_ID,
            "client_id": self.MOCK_CLIENT_ID,
            "client_secret": self.MOCK_CLIENT_SECRET,
            "batch_account_url": self.MOCK_BATCH_ACCOUNT_URL,
            "storage_account_name": self.MOCK_STORAGE_ACCOUNT_NAME,
            "storage_account_domain": self.MOCK_STORAGE_ACCOUNT_DOMAIN,
            "pool_id": self.MOCK_POOL_ID,
            "job_id": self.MOCK_JOB_ID,
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

    def test_get_blob_client(self, mock_executor, mocker):
        """Test Azure Batch executor blob client getter."""
        credentials_mock = MagicMock()
        blob_service_client_mock = mocker.patch(
            "covalent_azurebatch_plugin.azurebatch.BlobServiceClient.__init__", return_value=None
        )
        mock_executor._get_blob_client(credentials_mock)
        account_uri_mock = (
            f"https://{mock_executor.storage_account_name}.{mock_executor.storage_account_domain}/"
        )
        blob_service_client_mock.assert_called_once_with(
            account_url=account_uri_mock, credentials=credentials_mock
        )

    def test_get_batch_client(self, mock_executor, mocker):
        """Test Azure Batch executor batch client getter."""
        credentials_mock = MagicMock()
        batch_service_client_mock = mocker.patch(
            "covalent_azurebatch_plugin.azurebatch.BatchServiceClient.__init__", return_value=None
        )
        mock_executor._get_batch_service_client(credentials_mock)
        batch_service_client_mock.assert_called_once_with(
            credentials=credentials_mock, batch_url=mock_executor.batch_account_url
        )

    @pytest.mark.asyncio
    async def test_run(self, mock_executor, mocker):
        """Test Azure Batch executor run method."""

        def mock_func(x, y):
            return x + y

        credential_mock = MagicMock()
        validate_credentials_mock = mocker.patch(
            "covalent_azurebatch_plugin.azurebatch.AzureBatchExecutor._validate_credentials",
            return_value=credential_mock,
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
        submit_task_mock.assert_called_once_with(self.MOCK_TASK_METADATA, credential_mock)
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
    def test_validate_credentials(
        self, mock_executor, mocker, tenant_id, client_id, client_secret
    ):
        """Test Azure Batch executor credential validation."""
        mock_executor.tenant_id = tenant_id
        mock_executor.client_id = client_id
        mock_executor.client_secret = client_secret

        secret_credential_mock = MagicMock()
        default_credential_mock = MagicMock()

        mocker.patch(
            "covalent_azurebatch_plugin.azurebatch.ClientSecretCredential",
            return_value=secret_credential_mock,
        )
        mocker.patch(
            "covalent_azurebatch_plugin.azurebatch.DefaultAzureCredential",
            return_value=default_credential_mock,
        )

        credentials = mock_executor._validate_credentials()
        if tenant_id and client_id and client_secret:
            assert credentials == secret_credential_mock
        else:
            assert credentials == default_credential_mock

    def test_validate_credentials_exception_raised(self, mock_executor, mocker):
        """Test Azure Batch executor credential validation exception being raised."""
        mocker.patch(
            "covalent_azurebatch_plugin.azurebatch.ClientSecretCredential", side_effect=Exception
        )
        with pytest.raises(Exception):
            mock_executor._validate_credentials()

    def test_validate_credentials_exception_not_raised(self, mock_executor, mocker):
        """Test Azure Batch executor credential validation exception not being raised."""
        mocker.patch(
            "covalent_azurebatch_plugin.azurebatch.ClientSecretCredential", side_effect=Exception
        )
        credentials = mock_executor._validate_credentials(raise_exception=False)
        assert not credentials

    def test_poll_task(self, mock_executor, mocker):
        pass

    def test_debug_log(self, mock_executor, mocker):
        pass
