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
