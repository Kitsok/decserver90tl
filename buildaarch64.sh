#!/usr/bin/env bash
# Container-free cross-build for nanovax (Debian 12, AArch64 Cortex-A53).
set -euo pipefail
repo_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
exec python3 "$repo_dir/tools/build_aarch64.py" "$@"
