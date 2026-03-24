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
import os
import sys
from functools import partial
from pathlib import Path
from shutil import move, copy2, copytree
from subprocess import check_call
from tempfile import TemporaryDirectory

import version_extractor

log = partial(print, file=sys.stderr)

SETUP_PY_TEMPLATE = """\
from os import walk
from os.path import abspath, join as jp

from setuptools import setup
from wheel_axle.bdist_axle import BdistAxle


def get_data_files(src_dir):
    current_path = abspath(src_dir)
    for root, dirs, files in walk(current_path, followlinks=True):
        if not files:
            continue
        path_prefix = root[len(current_path) + 1:]
        if (path_prefix.endswith(".egg-info")
                or path_prefix.startswith("build")
                or path_prefix.startswith("dist")):
            continue
        if not path_prefix:
            files = [f for f in files
                     if not f.endswith(("setup.py", "setup.cfg", "pyproject.toml"))]
            if not files:
                continue
        yield path_prefix, [jp(root, f) for f in files]


data_files = list(get_data_files("."))

setup(
    name=%(name)r,
    version=%(version)r,
    description=%(description)r,
    long_description=%(long_description)r,
    long_description_content_type='text/markdown',
    classifiers=[
        'Programming Language :: Python',
        'Operating System :: POSIX :: Linux',
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Debuggers',
    ],
    keywords=%(keywords)r,
    author='Karellen, Inc.',
    author_email='supervisor@karellen.co',
    maintainer='Arcadiy Ivanov',
    maintainer_email='arcadiy@karellen.co',
    license="Apache-2.0",
    url='https://github.com/karellen/karellen-rr',
    project_urls={
        'Bug Tracker': 'https://github.com/karellen/karellen-rr/issues',
        'Source Code': 'https://github.com/karellen/karellen-rr',
        'Upstream': 'https://rr-project.org/',
    },
    scripts=[],
    packages=[],
    data_files=data_files,
    install_requires=[],
    zip_safe=False,
    cmdclass={"bdist_wheel": BdistAxle},
)
"""

SETUP_CFG_TEMPLATE = """\
[bdist_wheel]
root_is_pure = false
python_tag = py3
abi_tag = none
%(plat_name_line)s"""

PYPROJECT_TOML = """\
[build-system]
requires = ["setuptools", "wheel", "wheel-axle>=0.0.12"]
build-backend = "setuptools.build_meta"
"""

ARCH_PLAT_MAP = {
    "x86_64": "manylinux_2_28_x86_64",
    "aarch64": "manylinux_2_28_aarch64",
}


def copy_licenses(staging_dir, source_dir):
    """Copy component licenses into the staging tree so they end up in the wheel."""
    license_dir = staging_dir / "share" / "karellen-rr" / "licenses"
    license_dir.mkdir(parents=True, exist_ok=True)

    for src, dst_name in [
        (source_dir / "rr" / "LICENSE", "rr-LICENSE"),
        (source_dir / "capnproto" / "LICENSE", "capnproto-LICENSE"),
        (source_dir / "LICENSE", "karellen-rr-LICENSE"),
    ]:
        if src.exists():
            copy2(src, license_dir / dst_name)


def package_arch(arch, source_dir, wheel_dir, version, long_description):
    plat_name = ARCH_PLAT_MAP[arch]
    install_dir = Path(f"rr.install.{arch}")

    if not install_dir.exists() or not any(install_dir.iterdir()):
        log(f"Skipping {arch}: {install_dir} does not exist or is empty")
        return

    log(f"Packaging for {arch} (plat: {plat_name})...")

    with TemporaryDirectory() as tmp:
        staging_dir = Path(tmp)

        # Copy installed files into staging
        copytree(install_dir, staging_dir, symlinks=True, dirs_exist_ok=True)

        # Add component licenses
        copy_licenses(staging_dir, source_dir)

        # Generate build files
        plat_name_line = f"plat_name = {plat_name}"
        (staging_dir / "pyproject.toml").write_text(PYPROJECT_TOML, encoding="utf-8")
        (staging_dir / "setup.py").write_text(SETUP_PY_TEMPLATE % dict(
            name="karellen-rr",
            version=version,
            description="rr reverse debugger",
            long_description=long_description,
            keywords=["rr", "debugger", "reverse-debugging", "record-replay"],
        ), encoding="utf-8")
        (staging_dir / "setup.cfg").write_text(SETUP_CFG_TEMPLATE % dict(
            plat_name_line=plat_name_line,
        ), encoding="utf-8")

        # Build wheel
        check_call([sys.executable, "-m", "build", "--wheel", "--no-isolation"],
                    cwd=staging_dir)

        # Move wheel to output
        for whl in (staging_dir / "dist").glob("*.whl"):
            dest = wheel_dir / whl.name
            move(str(whl), str(dest))
            log(f"Wheel: {dest}")


def main():
    parser = argparse.ArgumentParser(description="Package rr install tree as a Python wheel")
    parser.add_argument("-a", "--arch", choices=["x86_64", "aarch64", "all"],
                        default="all",
                        help="architecture(s) to package (default: all)")
    parser.add_argument("-s", "--source-dir", type=Path, default=Path("."),
                        help="project root directory (default: .)")
    parser.add_argument("-w", "--wheel-dir", type=Path, default=Path("wheels"),
                        help="output wheel directory (default: wheels/)")
    args = parser.parse_args()

    version = version_extractor.get_version(args.source_dir / "rr")
    log(f"rr version: {version}")

    args.wheel_dir.mkdir(parents=True, exist_ok=True)

    readme_path = args.source_dir / "README.md"
    if readme_path.exists():
        long_description = readme_path.read_text()
    else:
        long_description = "rr reverse debugger packaged as a Python wheel"

    if args.arch == "all":
        archs = list(ARCH_PLAT_MAP.keys())
    else:
        archs = [args.arch]

    for arch in archs:
        package_arch(arch, args.source_dir, args.wheel_dir, version, long_description)


if __name__ == "__main__":
    main()
