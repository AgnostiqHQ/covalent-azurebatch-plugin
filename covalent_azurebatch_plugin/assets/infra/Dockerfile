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

ARG COVALENT_BASE_IMAGE
FROM ${COVALENT_BASE_IMAGE}

ARG COVALENT_PACKAGE_VERSION

USER root

RUN apt-get update && apt-get install gcc -y \
  && rm -rf /var/lib/apt/lists/* \
  && pip install --no-cache-dir --upgrade \
  azure-batch==12.0.0 \
  azure-identity==1.11.0 \
  azure-storage-blob==12.14.1


RUN if [ -z "$COVALENT_PACKAGE_VERSION" ]; then \
		pip install covalent; else \
		pip install "covalent==$COVALENT_PACKAGE_VERSION"; \
	fi


WORKDIR /covalent

ENV XDG_CONFIG_DIR=/mnt/batch/tasks
ENV XDG_CACHE_HOME=/mnt/batch/tasks
ENV XDG_DATA_HOME=/mnt/batch/tasks

COPY exec.py /covalent

ENTRYPOINT [ "python" ]
CMD [ "/covalent/exec.py" ]
