#!/usr/bin/env bash
# Prepare a new, isolated lab network. Never alters an existing interface.
set -euo pipefail
usage() {
    printf 'Usage: sudo %s setup OWNER_UID [BRIDGE [TAP]]\n' "$0"
    printf 'Defaults: brds90, ds90tap. Creates 192.0.2.1/24 on the new bridge.\n'
    printf 'No uplink, forwarding, NAT or existing interface configuration is changed.\n'
}
if [[ ${1:-} == --help || ${1:-} == -h ]]; then usage; exit 0; fi
if [[ ${1:-} != setup || $# -lt 2 || $# -gt 4 ]]; then usage >&2; exit 2; fi
owner_uid=$2
bridge=${3:-brds90}
tap=${4:-ds90tap}
if [[ ! $owner_uid =~ ^[0-9]+$ ]]; then printf 'OWNER_UID must be numeric\n' >&2; exit 2; fi
for name in "$bridge" "$tap"; do
    if [[ ! $name =~ ^[a-zA-Z0-9_.-]{1,15}$ || $name == . || $name == .. ]]; then
        printf 'Invalid interface name: %s\n' "$name" >&2; exit 2
    fi
done
if [[ $bridge == "$tap" ]]; then printf 'Bridge and TAP names must differ\n' >&2; exit 2; fi
if (( EUID != 0 )); then printf 'Run this setup command with sudo; the simulator runs as your normal user.\n' >&2; exit 1; fi
if ip link show dev "$bridge" >/dev/null 2>&1 || ip link show dev "$tap" >/dev/null 2>&1; then
    printf 'Refusing setup: bridge or TAP already exists. Existing interfaces were not changed.\n' >&2
    exit 1
fi
created_bridge=false
created_tap=false
rollback() {
    local status=$?
    if (( status != 0 )); then
        if $created_tap; then ip link delete dev "$tap" || true; fi
        if $created_bridge; then ip link delete dev "$bridge" || true; fi
    fi
}
trap rollback EXIT
ip link add name "$bridge" type bridge
created_bridge=true
ip address add 192.0.2.1/24 dev "$bridge"
ip link set dev "$bridge" up
ip tuntap add dev "$tap" mode tap user "$owner_uid"
created_tap=true
ip link set dev "$tap" master "$bridge"
ip link set dev "$tap" up
printf 'Prepared bridge %s (192.0.2.1/24) and TAP %s owned by UID %s.\n' "$bridge" "$tap" "$owner_uid"
printf 'Run as that user: ./run.sh --interactive --tap %q\n' "$tap"
printf 'Remove this lab after stopping the simulator:\n  sudo ip link delete dev %q\n  sudo ip link delete dev %q\n' "$tap" "$bridge"
