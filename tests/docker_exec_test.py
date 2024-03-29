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

"""Unit tests for AWS batch executor braket execution file."""

import os
import sys
from unittest import mock

import cloudpickle
import pytest
from anyio import Path

MOCK_STORAGE_ACCOUNT = "mock_storage_account"
MOCK_STORAGE_CONTAINER = "pickle_container"
MOCK_STORAGE_ACCOUNT_DOMAIN = "mock_domain"
MOCK_COVALENT_TASK_FUNC_FILENAME = "function_file.pkl"
MOCK_COVALENT_RESULT_FILENAME = "result_file.pkl"


@pytest.mark.parametrize(
    "env_dict",
    [
        {},
        {"AZURE_BLOB_STORAGE_ACCOUNT": MOCK_STORAGE_ACCOUNT},
        {
            "AZURE_BLOB_STORAGE_ACCOUNT": MOCK_STORAGE_ACCOUNT,
            "AZURE_BLOB_STORAGE_CONTAINER": MOCK_STORAGE_CONTAINER,
        },
        {
            "AZURE_BLOB_STORAGE_ACCOUNT": MOCK_STORAGE_ACCOUNT,
            "AZURE_BLOB_STORAGE_CONTAINER": MOCK_STORAGE_CONTAINER,
            "AZURE_BLOB_STORAGE_ACCOUNT_DOMAIN": MOCK_STORAGE_ACCOUNT_DOMAIN,
        },
        {
            "AZURE_BLOB_STORAGE_ACCOUNT": MOCK_STORAGE_ACCOUNT,
            "AZURE_BLOB_STORAGE_CONTAINER": MOCK_STORAGE_CONTAINER,
            "AZURE_BLOB_STORAGE_ACCOUNT_DOMAIN": MOCK_STORAGE_ACCOUNT_DOMAIN,
            "COVALENT_TASK_FUNC_FILENAME": MOCK_COVALENT_TASK_FUNC_FILENAME,
        },
        {"COVALENT_RESULT_FILENAME": MOCK_COVALENT_RESULT_FILENAME},
        {"EXECUTOR_WORKDIR": "/tmp"},
    ],
)
def test_execution_exceptions(mocker, env_dict, tmp_path: Path):
    azure_identity_mock = mock.MagicMock()
    azure_storage_mock = mock.MagicMock()
    sys.modules["azure.identity"] = azure_identity_mock
    sys.modules["azure.storage.blob"] = azure_storage_mock

    mocker.patch.dict(os.environ, **env_dict)

    with pytest.raises(ValueError):
        import covalent_azurebatch_plugin

        sys.path.append(os.path.dirname(covalent_azurebatch_plugin.__file__) + "/assets/infra")
        import exec


def test_execution(mocker, tmp_path: Path):
    azure_identity_mock = mock.MagicMock()
    azure_storage_mock = mock.MagicMock()
    sys.modules["azure.identity"] = azure_identity_mock
    sys.modules["azure.storage.blob"] = azure_storage_mock

    container_client_mock = azure_storage_mock.BlobServiceClient().get_container_client()

    def mock_function(x):
        return x

    tmp_function_pickle_file = tmp_path / MOCK_COVALENT_TASK_FUNC_FILENAME
    tmp_result_pickle_file = tmp_path / MOCK_COVALENT_RESULT_FILENAME

    mocker.patch.dict(
        os.environ,
        {
            "AZURE_BLOB_STORAGE_ACCOUNT": MOCK_STORAGE_ACCOUNT,
            "AZURE_BLOB_STORAGE_CONTAINER": MOCK_STORAGE_CONTAINER,
            "AZURE_BLOB_STORAGE_ACCOUNT_DOMAIN": MOCK_STORAGE_ACCOUNT_DOMAIN,
            "COVALENT_TASK_FUNC_FILENAME": MOCK_COVALENT_TASK_FUNC_FILENAME,
            "COVALENT_RESULT_FILENAME": MOCK_COVALENT_RESULT_FILENAME,
            "EXECUTOR_WORKDIR": str(tmp_path),
        },
    )

    with open(str(tmp_function_pickle_file), "wb") as f:
        x = 1
        positional_args = [x]
        cloudpickle.dump((mock_function, positional_args, {}), f)

    with open(str(tmp_function_pickle_file), "rb") as f:
        container_client_mock.download_blob().readall.return_value = f.read()

    import covalent_azurebatch_plugin

    sys.path.append(os.path.dirname(covalent_azurebatch_plugin.__file__) + "/assets/infra")
    import exec

    container_client_mock.download_blob().readall.assert_called_once()
    container_client_mock.download_blob.assert_any_call(MOCK_COVALENT_TASK_FUNC_FILENAME)

    with open(str(tmp_result_pickle_file), "rb") as f:
        result = cloudpickle.load(f)
        assert result == 1

    container_client_mock.upload_blob.assert_called_with(MOCK_COVALENT_RESULT_FILENAME, mock.ANY)
