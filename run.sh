#!/usr/bin/env bash
# Run the verified, bounded MNENG3 initialization and diagnostic login.
set -euo pipefail

repo_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)

usage() {
    printf 'Usage: %s [nvram-directory]\n' "$0"
    printf 'Runs 60 seconds of initialization, then a 50-second diagnostic login.\n'
    printf 'Default store: run/my-decserver. Relative paths are relative to the repository.\n'
    printf 'This is a scripted FIFO probe, not an interactive terminal.\n'
}

if [[ ${1:-} == --help || ${1:-} == -h ]]; then
    usage
    exit 0
fi
if (( $# > 1 )); then
    usage >&2
    exit 2
fi

cd -- "$repo_dir"
if [[ ! -x build/mame-ds90tl ]]; then
    printf 'Simulator executable missing. Build it first:\n  cd %q && python3 tools/build_mame.py -j 2\n' "$repo_dir" >&2
    exit 1
fi

nvram_dir=${1:-run/my-decserver}
common_args=(--rom-alignment-assist --ram-wait-cycles 1 --nvram-directory "$nvram_dir")

printf 'Initializing configuration storage: %s\n' "$nvram_dir"
python3 tools/run_mneng3.py --seconds 60 "${common_args[@]}"
cp -- run/bringup.log run/initialization.log

printf '\nRunning diagnostic login as SIMULATOR...\n'
python3 tools/run_mneng3.py --seconds 50 "${common_args[@]}" \
    --uart-probe-port 1 --uart-probe-at 30 \
    --uart-probe-hex 0d0d0d53494d554c41544f520d
cp -- run/bringup.log run/login.log

printf '\nLogs: %s/run/initialization.log and %s/run/login.log\n' "$repo_dir" "$repo_dir"
