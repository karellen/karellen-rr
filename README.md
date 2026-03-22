# Karellen rr

[rr](https://rr-project.org/) reverse debugger packaged as a pip-installable
Python wheel for Linux x86_64.

## Overview

This project builds the `rr` reverse debugger inside a `manylinux_2_28` Docker
container and packages it as a `py3-none-manylinux_2_28_x86_64` wheel using
[wheel-axle](https://github.com/karellen/wheel-axle). The resulting wheel can
be installed with pip and provides the `rr` binary on PATH.

## Installation

```bash
pip install karellen-rr
```

After installation, `rr` is available directly:

```bash
rr record ./my-program
rr replay
```

## Building

### Prerequisites

- Docker
- Python 3.10+
- `wheel-axle` and `setuptools` (`pip install -r requirements.txt`)

### Build Steps

```bash
# Build rr inside manylinux_2_28 container
python docker-build.py

# Package on host
python packager.py -t rr.install

# Smoke test
bash test-build.sh
```

## Licenses

- **Packaging infrastructure** (this project): Apache License 2.0
- **rr**: MIT License (see `rr/LICENSE`)
- **Cap'n Proto**: MIT License (see `capnproto/LICENSE`)

All component licenses are bundled in the wheel under
`share/karellen-rr/licenses/`.
