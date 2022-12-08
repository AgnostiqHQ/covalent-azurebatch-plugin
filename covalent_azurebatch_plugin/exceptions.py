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

"""Azure Batch executor exceptions module."""


class NoBatchTasksException(Exception):
    """Exception when no tasks were found in the Azure Batch job list."""

    pass


class BatchTaskFailedException(Exception):
    """Exception when a task failed with non-zero exit code."""

    def __init__(self, exit_code):
        msg = f"Task failed with exit code {exit_code}. Check batch task log for more details."
        super().__init__(msg)
