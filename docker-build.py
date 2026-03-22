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

import atexit
import os
import signal
import sys
from grp import getgrgid
from os import makedirs, getuid, getgid
from os.path import join as jp, abspath as ap, expanduser
from pwd import getpwuid
from subprocess import Popen, run

CMAKE_VERSION = "4.2.1"
NINJA_VERSION = "1.13.1"

DOCKER_IMAGES = {
    "x86_64": "ghcr.io/karellen/manylinux_2_28_x86_64:latest",
    "aarch64": "ghcr.io/karellen/manylinux_2_28_aarch64:latest",
}

# x86_64 has no arch suffix in ninja zip name; aarch64 does
ARCH_ENV = {
    "x86_64": [],
    "aarch64": ["export NINJA_ARCH='-aarch64'"],
}

INIT_SCRIPT = [
    'ARCH="$(uname -m)"',
    f"curl -Ls -o /tmp/cmake.sh https://github.com/Kitware/CMake/releases/download/v{CMAKE_VERSION}/cmake-{CMAKE_VERSION}-linux-$ARCH.sh",
    "chmod +x /tmp/cmake.sh && /tmp/cmake.sh --exclude-subdir --skip-license --prefix=/usr/local",
    f'curl -Ls -o /tmp/ninja.zip https://github.com/ninja-build/ninja/releases/download/v{NINJA_VERSION}/ninja-linux${{NINJA_ARCH:-}}.zip',
    "unzip /tmp/ninja.zip -d /usr/local/bin",
    "ln -s /usr/local/bin/ninja /usr/local/bin/ninja-build",
    "yum install -y zlib-devel zlib-static libzstd-devel",
]


MAPPED_FILES = [
    ("build-rr.sh", None, "ro"),
]

BUILD_DIRS = ["rr.build", "rr.install", "capnp.build", "capnp.install"]
MAPPED_SOURCES_RO = ["rr", "capnproto", ".git/modules"]


_current_proc = None
_current_container = None
_cleaning_up = False


def cleanup():
    global _cleaning_up
    if _cleaning_up:
        return
    _cleaning_up = True

    # Terminate the docker process first — this is the direct child
    if _current_proc and _current_proc.poll() is None:
        _current_proc.terminate()
        try:
            _current_proc.wait(timeout=5)
        except Exception:
            _current_proc.kill()
            _current_proc.wait()

    # Then ensure the container is stopped (--rm will clean it up)
    if _current_container:
        try:
            run(["docker", "stop", "-t", "3", _current_container],
                capture_output=True, timeout=10)
        except Exception:
            try:
                run(["docker", "kill", _current_container],
                    capture_output=True, timeout=5)
            except Exception:
                pass

    _cleaning_up = False


def sighandler(signum, frame):
    cleanup()
    # Re-raise with default handler for correct exit code
    signal.signal(signum, signal.SIG_DFL)
    os.kill(os.getpid(), signum)


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("-a", "--arch", choices=["x86_64", "aarch64", "all"],
                        default="all",
                        help="architecture(s) to build (default: all)")
    args = parser.parse_args()

    uid = getuid()
    uname = getpwuid(uid)[0]
    gid = getgid()
    gname = getgrgid(gid)[0]
    udir = expanduser("~")

    atexit.register(cleanup)
    signal.signal(signal.SIGINT, sighandler)
    signal.signal(signal.SIGTERM, sighandler)

    archs = list(DOCKER_IMAGES.keys()) if args.arch == "all" else [args.arch]

    global _current_proc, _current_container
    for arch in archs:
        _current_container = f"karellen-rr-build-{arch}"

        script_lines = ["set -eEux"] + ARCH_ENV[arch] + INIT_SCRIPT + [
            f"groupadd -g {gid} {gname}",
            f"useradd {uname} -u {uid} -g {gid} -d {udir} -M -s /bin/bash",
            f"mkdir -p {udir}",
            f"chown {uname}:{gname} /build",
            f"chown {uname}:{gname} {udir}",
            "cd /build",
            f"su -m {uname} ./build-rr.sh",
        ]
        inner_script = " && ".join(script_lines)

        cmd_line = ["docker", "run", "--pull", "always", "--rm",
                    "--name", _current_container,
                    "--init"]

        for mf in MAPPED_FILES:
            cmd_line.extend(["-v", "%s:%s:%s" % (ap(mf[0]), mf[1] or jp("/build", mf[0]), mf[2])])

        # Per-arch build directories
        for bd in BUILD_DIRS:
            local_dir = f"{bd}.{arch}"
            makedirs(local_dir, exist_ok=True)
            cmd_line.extend(["-v", "%s:%s" % (ap(local_dir), jp("/build", bd))])

        for src in MAPPED_SOURCES_RO:
            cmd_line.extend(["-v", "%s:%s:ro" % (ap(src), jp("/build", src))])

        cmd_line.extend([DOCKER_IMAGES[arch], "/bin/bash", "-c", inner_script])

        print(f"=== Building for {arch} ===", file=sys.stderr)
        _current_proc = Popen(cmd_line)
        return_code = _current_proc.wait()
        _current_proc = None
        _current_container = None

        if return_code:
            raise RuntimeError("Build for %s failed with exit code %d" % (arch, return_code))


if __name__ == "__main__":
    main()
