#!/usr/bin/env bash
# Run the verified, bounded MNENG3 initialization and diagnostic login.
set -euo pipefail

repo_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)

usage() {
    printf 'Usage: %s [--verbose] [--interactive] [--tap NAME] [nvram-directory]\n' "$0"
    printf 'Runs 60 seconds of initialization, then a 50-second diagnostic login.\n'
    printf 'Default store: run/my-decserver. Relative paths are relative to the repository.\n'
    printf 'Use --tap NAME to attach an existing bridged TAP; default is offline.\n'
    printf 'Use --interactive for eight serial PTYs, running until Ctrl-C.\n'
    printf 'Console: live progress and serial text. Logfiles: full raw trace.\n'
    printf 'Use --verbose to also show the full trace on console.\n'
}

interactive=false
network_args=()
console_args=()
positional=()
while (( $# )); do
    case $1 in
        -h|--help) usage; exit 0 ;;
        --interactive) interactive=true ;;
        --tap)
            if (( $# < 2 )); then printf '%s\n' '--tap requires an interface name' >&2; exit 2; fi
            network_args=(--tap "$2"); shift ;;
        -v|--verbose) console_args=(--verbose) ;;
        --) shift; positional+=("$@"); break ;;
        -*) printf 'Unknown option: %s\n' "$1" >&2; usage >&2; exit 2 ;;
        *) positional+=("$1") ;;
    esac
    shift
done
if (( ${#positional[@]} > 1 )); then
    usage >&2
    exit 2
fi

cd -- "$repo_dir"
if [[ ! -x build/mame-ds90tl ]]; then
    printf 'Simulator executable missing. Build it first:\n  cd %q && python3 tools/build_mame.py -j 2\n' "$repo_dir" >&2
    exit 1
fi

nvram_dir=${positional[0]:-run/my-decserver}
common_args=(--rom-alignment-assist --ram-wait-cycles 1 --nvram-directory "$nvram_dir" "${console_args[@]}" "${network_args[@]}")

run_stage() {
    local label=$1 log_path=$2
    shift 2
    printf '\n%s\n' "$label"
    if python3 tools/run_mneng3.py "${common_args[@]}" --log-file "$log_path" "$@"; then
        printf '%s: completed normally. Full trace: %s/%s\n' "$label" "$repo_dir" "$log_path"
    else
        local status=$?
        printf '%s: stopped with status %d. Full trace: %s/%s\n' "$label" "$status" "$repo_dir" "$log_path" >&2
        return "$status"
    fi
}

if $interactive; then
    exec python3 tools/run_mneng3.py "${common_args[@]}" --interactive --log-file run/interactive.log
fi

printf 'Configuration storage: %s\n' "$nvram_dir"
printf 'Two timed runs: 60 + 50 simulated seconds; wall time depends on host speed.\n'
printf 'Both runs stop automatically. This is not an interactive terminal.\n'
run_stage '[1/2] Configuration initialization (60 simulated seconds)' run/initialization.log --seconds 60
run_stage '[2/2] Scripted login as SIMULATOR (50 simulated seconds; input starts at 30s)' run/login.log --seconds 50 \
    --uart-probe-port 1 --uart-probe-at 30 \
    --uart-probe-hex 0d0d0d53494d554c41544f520d

printf '\nFinished both timed runs; simulator has stopped normally.\n'
printf '\nLogs: %s/run/initialization.log and %s/run/login.log\n' "$repo_dir" "$repo_dir"
