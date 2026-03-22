#!/usr/bin/env python3
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

import argparse
import re
import sys
from pathlib import Path
from subprocess import check_output, CalledProcessError

VERSION_RE = re.compile(r'set\(rr_VERSION_(MAJOR|MINOR|PATCH)\s+(\d+)\)')


def get_version(source_dir):
    source_dir = Path(source_dir)
    cmake_file = source_dir / "CMakeLists.txt"
    text = cmake_file.read_text()

    parts = {}
    for match in VERSION_RE.finditer(text):
        parts[match.group(1)] = match.group(2)

    if not all(k in parts for k in ("MAJOR", "MINOR", "PATCH")):
        raise RuntimeError(f"Could not parse rr version from {cmake_file}")

    major = parts["MAJOR"]
    minor = parts["MINOR"]
    patch = parts["PATCH"]

    try:
        desc = check_output(
            ["git", "describe", "--tags", "--long"],
            text=True, cwd=source_dir
        ).strip()
        # Format: tag-N-ghash
        post_commits = int(desc.rsplit("-", 2)[-2])
    except (CalledProcessError, ValueError, IndexError):
        post_commits = 0

    version = f"{major}.{minor}.{patch}"
    if post_commits:
        version += f".post{post_commits}"

    return version


def main():
    parser = argparse.ArgumentParser(description="Extract rr version from CMakeLists.txt")
    parser.add_argument("-s", "--source-dir", type=Path, default=Path("rr"),
                        help="rr source directory (default: rr/)")
    args = parser.parse_args()

    print(get_version(args.source_dir))


if __name__ == "__main__":
    main()
