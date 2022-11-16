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

ARG COVALENT_BASE_IMAGE
FROM ${COVALENT_BASE_IMAGE}

COPY requirements.txt /covalent/requirements.txt
WORKDIR /covalent

RUN apt-get update && apt-get install -y \
  && rm -rf /var/lib/apt/lists/* \
  && pip install --no-cache-dir --use-feature=in-tree-build --upgrade \
  azure-batch==12.0.0 \
  azure-identity==1.11.0 \
  azure-storage-blob==12.14.1 \
  "covalent>=0.202.0,<1"

COPY covalent_azurebatch_plugin/exec.py /covalent

ENTRYPOINT [ "python" ]
CMD [ "/covalent/exec.py" ]
