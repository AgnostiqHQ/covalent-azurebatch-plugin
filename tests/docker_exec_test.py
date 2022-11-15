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

"""Unit tests for AWS batch executor braket execution file."""

import os
import sys
from unittest import mock

import cloudpickle
from anyio import Path


MOCK_STORAGE_ACCOUNT = "mock_storage_account"
MOCK_STORAGE_CONTAINER = "pickle_container"
MOCK_COVALENT_TASK_FUNC_FILENAME = "function_file.pkl"
MOCK_RESULT_FILENAME = "result_file.pkl"

def test_execution(mocker, tmp_path: Path):
    azure_identity_mock = mock.MagicMock()
    azure_storage_mock = mock.MagicMock()
    sys.modules["azure.identity"] = azure_identity_mock
    sys.modules["azure.storage.blob"] = azure_storage_mock

    container_client_mock = azure_storage_mock.BlobServiceClient().get_container_client()

    # mocker.patch("azure.identity")

    def mock_function(x):
        return x

    tmp_function_pickle_file = tmp_path / MOCK_COVALENT_TASK_FUNC_FILENAME
    tmp_result_pickle_file = tmp_path / MOCK_RESULT_FILENAME

    mocker.patch.dict(
        os.environ,
        {
            "AZURE_BLOB_STORAGE_ACCOUNT": MOCK_STORAGE_ACCOUNT,
            "AZURE_BLOB_STORAGE_CONTAINER": MOCK_STORAGE_CONTAINER,
            "COVALENT_TASK_FUNC_FILENAME": MOCK_COVALENT_TASK_FUNC_FILENAME,
            "RESULT_FILENAME": MOCK_RESULT_FILENAME,
            "EXECUTOR_WORKDIR": str(tmp_path),
        },
    )

    with open(str(tmp_function_pickle_file), "wb") as f:
        x = 1
        positional_args = [x]
        cloudpickle.dump((mock_function, positional_args, {}), f)

    

    with open(str(tmp_function_pickle_file),"rb") as f:
        container_client_mock.download_blob().readall.return_value = f.read()

    import covalent_azurebatch_plugin.exec

    container_client_mock.download_blob().readall.assert_called_once()
    container_client_mock.download_blob.assert_any_call(MOCK_COVALENT_TASK_FUNC_FILENAME)

    with open(str(tmp_result_pickle_file),"rb") as f:
        result = cloudpickle.load(f)
        assert result == 1

    container_client_mock.upload_blob.assert_called_with(MOCK_RESULT_FILENAME,mock.ANY)
