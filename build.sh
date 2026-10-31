#!/usr/bin/env bash
# Fetch the pinned MAME dependency and build the DECserver machine.
set -euo pipefail

repo_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
jobs=2
offline=false
check_only=false

usage() {
    printf 'Usage: %s [-j JOBS] [--offline] [--check]\n' "$0"
    printf 'Builds the host-native emulator and its bundled MAME dependencies.\n'
    printf 'Fetches the pinned MAME revision on first use; later builds reuse it.\n'
    printf '  -j, --jobs N  Parallel build jobs (default: 2)\n'
    printf '  --offline     Never fetch dependencies\n'
    printf '  --check       Check prerequisites without fetching or building\n'
    printf 'System packages are reported when missing; installation is explicit.\n'
}

while (( $# )); do
    case $1 in
        -h|--help) usage; exit 0 ;;
        -j|--jobs)
            if (( $# < 2 )); then printf '%s\n' '--jobs requires a positive integer' >&2; exit 2; fi
            jobs=$2; shift ;;
        --offline) offline=true ;;
        --check) check_only=true ;;
        *) printf 'Unknown option: %s\n' "$1" >&2; usage >&2; exit 2 ;;
    esac
    shift
done
if [[ ! $jobs =~ ^[1-9][0-9]*$ ]]; then
    printf '%s\n' '--jobs requires a positive integer' >&2
    exit 2
fi

cd -- "$repo_dir"
missing=false
for command in git make gcc g++ python3 pkg-config flock; do
    if ! command -v "$command" >/dev/null 2>&1; then
        printf 'Missing build tool: %s\n' "$command" >&2
        missing=true
    fi
done
if command -v pkg-config >/dev/null 2>&1; then
    for package in sdl2 SDL2_ttf fontconfig egl; do
        if ! pkg-config --exists "$package"; then
            printf 'Missing development package: %s\n' "$package" >&2
            missing=true
        fi
    done
fi
if $missing; then
    printf '%s\n' 'On Debian/Ubuntu, install prerequisites explicitly:' >&2
    printf '%s\n' '  sudo apt-get install build-essential git python3 pkg-config util-linux libsdl2-dev libsdl2-ttf-dev libfontconfig-dev libegl-dev' >&2
    exit 1
fi

revision=$(<mame-revision.txt)
if [[ ! $revision =~ ^[[:xdigit:]]{40}$ ]]; then
    printf '%s\n' 'Invalid pinned revision in mame-revision.txt' >&2
    exit 1
fi
python3 -c 'import hashlib, pathlib, sys; p=pathlib.Path("firmware/MNENG3.SYS"); sys.exit(0 if hashlib.sha256(p.read_bytes()).hexdigest()=="a3764087d79df64eb7124056824652cf23b558fcae2029f887e4a37a3db49ad3" else "Unexpected MNENG3 firmware hash")'

if $check_only; then
    printf 'Host build prerequisites and firmware: OK\nPinned MAME revision: %s\n' "$revision"
    exit 0
fi

mkdir -p .deps
exec 9>.deps/build-entry.lock
if ! flock -n 9; then
    printf '%s\n' 'Another build.sh is running.' >&2
    exit 1
fi
if [[ ! -e .deps/mame ]]; then
    mkdir .deps/mame
fi
if [[ ! -e .deps/mame/.git ]]; then
    if [[ -n $(find .deps/mame -mindepth 1 -maxdepth 1 -print -quit) ]]; then
        printf '%s\n' '.deps/mame is not an empty directory or a Git checkout; refusing to overwrite it.' >&2
        exit 1
    fi
    if $offline; then
        printf '%s\n' 'Pinned MAME checkout is missing; rerun without --offline to fetch it.' >&2
        exit 1
    fi
    git -C .deps/mame init --quiet
    git -C .deps/mame remote add origin https://github.com/mamedev/mame.git
fi
if ! git -C .deps/mame rev-parse --verify HEAD >/dev/null 2>&1; then
    if ! git -C .deps/mame cat-file -e "$revision^{commit}" 2>/dev/null; then
        if $offline; then
            printf '%s\n' 'Pinned MAME commit is unavailable locally; rerun without --offline.' >&2
            exit 1
        fi
        git -C .deps/mame fetch --depth 1 https://github.com/mamedev/mame.git "$revision"
    fi
    git -C .deps/mame checkout --detach "$revision"
fi
actual=$(git -C .deps/mame rev-parse HEAD)
if [[ $actual != "$revision" ]]; then
    printf 'MAME revision mismatch: expected %s, found %s. Existing checkout left unchanged.\n' "$revision" "$actual" >&2
    exit 1
fi

printf 'Building DECserver 90TL for %s with %s jobs.\n' "$(uname -m)" "$jobs"
python3 tools/build_mame.py --jobs "$jobs"
printf '\nBuild complete: %s/build/mame-ds90tl\nRun: %s/run.sh --interactive\n' "$repo_dir" "$repo_dir"
