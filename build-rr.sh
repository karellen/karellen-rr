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

SOURCE_DIR="$(readlink -nf rr)"
BUILD_DIR="$(readlink -nf rr.build)"
INSTALL_DIR="$(readlink -nf rr.install)"
CAPNP_SOURCE_DIR="$(readlink -nf capnproto)"
CAPNP_BUILD_DIR="$(readlink -nf capnp.build)"
CAPNP_INSTALL_DIR="$(readlink -nf capnp.install)"

PARALLEL_JOBS="$(nproc)"

# --- Phase 1: Build capnproto from source (static, cached) ---
if [ ! -f "$CAPNP_INSTALL_DIR/lib/libcapnp.a" ]; then
    echo "Building capnproto from source..."
    rm -rf "$CAPNP_BUILD_DIR"/* || true

    cmake -G Ninja \
        -DCMAKE_BUILD_TYPE=Release \
        -DCMAKE_INSTALL_PREFIX="$CAPNP_INSTALL_DIR" \
        -DCMAKE_INSTALL_LIBDIR=lib \
        -DCMAKE_POSITION_INDEPENDENT_CODE=ON \
        -DBUILD_SHARED_LIBS=OFF \
        -DBUILD_TESTING=OFF \
        -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
        -S "$CAPNP_SOURCE_DIR" \
        -B "$CAPNP_BUILD_DIR"

    cmake --build "$CAPNP_BUILD_DIR" -j "$PARALLEL_JOBS"
    cmake --install "$CAPNP_BUILD_DIR"
    echo "capnproto built and installed to $CAPNP_INSTALL_DIR"
else
    echo "Using cached capnproto at $CAPNP_INSTALL_DIR"
fi

# --- Phase 2: Build rr ---
echo "Building rr..."
rm -rf "$BUILD_DIR"/* || true
rm -rf "$INSTALL_DIR"/* || true

export PKG_CONFIG_PATH="$CAPNP_INSTALL_DIR/lib/pkgconfig:${PKG_CONFIG_PATH:-}"
export PATH="$CAPNP_INSTALL_DIR/bin:$PATH"

# Compute extra version string with post-release count and branding
POST_COMMITS="$(cd "$SOURCE_DIR" && git describe --tags --long 2>/dev/null | sed 's/.*-\([0-9]*\)-g.*/\1/' || echo 0)"
GIT_SHORT="$(cd "$SOURCE_DIR" && git rev-parse --short HEAD 2>/dev/null || echo unknown)"
if [ "$POST_COMMITS" -gt 0 ] 2>/dev/null; then
    EXTRA_VERSION="(Karellen, Inc. https://karellen.co .post${POST_COMMITS} ${GIT_SHORT})"
else
    EXTRA_VERSION="(Karellen, Inc. https://karellen.co)"
fi
echo "Extra version string: $EXTRA_VERSION"

# zlib and zstd are part of the manylinux_2_28 baseline — dynamic linking is fine.
# capnproto is found via pkg-config (static-only build from phase 1).
cmake -G Ninja \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_INSTALL_PREFIX="$INSTALL_DIR" \
    -DCMAKE_INSTALL_LIBDIR=lib \
    -Ddisable32bit=ON \
    -Dstrip=ON \
    -DBUILD_TESTS=OFF \
    -DWILL_RUN_TESTS=OFF \
    -DCMAKE_EXE_LINKER_FLAGS="-static-libstdc++ -static-libgcc" \
    -DEXTRA_VERSION_STRING="$EXTRA_VERSION" \
    -S "$SOURCE_DIR" \
    -B "$BUILD_DIR"

cmake --build "$BUILD_DIR" -j "$PARALLEL_JOBS"
cmake --install "$BUILD_DIR"

echo "rr built and installed to $INSTALL_DIR"

# --- Verify linking ---
echo "Verifying rr binary dependencies:"
ldd "$INSTALL_DIR/bin/rr"
