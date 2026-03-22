#!/bin/bash
#
# (C) Copyright 2026 Karellen, Inc. (https://www.karellen.co/)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

set -eEux
set -o pipefail

PYTHON=$(which python3)
PYTHON_VER="$($PYTHON -c 'import sys; print("".join(map(str, sys.version_info[:2])))')"
PYTHON_VENV="$(readlink -nf ./venv-test-cp$PYTHON_VER)"
rm -rf "$PYTHON_VENV"
$PYTHON -m venv "$PYTHON_VENV"
PATH=$PYTHON_VENV/bin:$PATH
export PATH

pip install --no-input wheels/*.whl
python -c pass
rr --version
echo "rr wheel test passed!"
