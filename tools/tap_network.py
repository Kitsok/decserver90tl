"""Fail-closed checks for explicitly selected, user-prepared TAP interfaces."""
import os
from pathlib import Path
import re


def validate_tap(name, sysfs=Path('/sys/class/net'), tun=Path('/dev/net/tun')):
    if not re.fullmatch(r'[A-Za-z0-9_.-]{1,15}', name) or name in ('.', '..'):
        raise ValueError('TAP name must be 1..15 letters, digits, dots, underscores or hyphens')
    interface = sysfs / name
    if not interface.exists():
        raise ValueError(f'TAP {name} does not exist; prepare it with network.sh or ip tuntap first')
    flags_file = interface / 'tun_flags'
    if not flags_file.exists() or not (int(flags_file.read_text().strip(), 0) & 2):
        raise ValueError(f'{name} is not a TAP interface; refusing to attach')
    if not int((interface / 'flags').read_text().strip(), 0) & 1:
        raise ValueError(f'TAP {name} is down; bring it up before starting')
    master = interface / 'master'
    if not master.exists() or not (master / 'bridge').is_dir():
        raise ValueError(f'TAP {name} must be attached to a Linux bridge before starting')
    if not tun.exists() or not os.access(tun, os.R_OK | os.W_OK):
        raise ValueError(f'{tun} is missing or inaccessible; TAP access is required')
    return master.resolve().name
