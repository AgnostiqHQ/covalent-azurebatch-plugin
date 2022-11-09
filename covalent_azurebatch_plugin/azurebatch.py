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

import os

from covalent._shared_files.config import get_config
from covalent._shared_files.logger import app_log
from covalent.executor.executor_plugins.remote_executor import RemoteExecutor

_EXECUTOR_PLUGIN_DEFAULTS = {
    "tenant_id": "" or os.environ.get("AZURE_TENANT_ID"),
    "client_id": "" or os.environ.get("AZURE_CLIENT_ID"),
    "client_secret": "" or os.environ.get("AZURE_CLIENT_SECRET"),
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

    # TODO - Add return type
    def _validate_credentials(self, raise_exception: bool = True):
        """Validate user-specified Microsoft Azure credentials or environment variables (configured before starting the server). Note: credentials passed should be those of a service principal rather than a developer account.

        Args:
            raise_exception (bool, optional): _description_. Defaults to True.
        """
        pass

    def _debug_log(self, message):
        pass

    async def run(self, function, args, kwargs, task_metadata):
        pass

    async def _upload_task(self, function, args, kwargs, task_metadata):
        pass

    async def submit_task(self, task_metadata, identity):
        pass

    async def get_status(self, job_id):
        pass

    async def _poll_task(self, job_id):
        pass

    async def cancel(self, job_id, reason):
        pass

    async def _query_result(self, task_metadata):
        pass
