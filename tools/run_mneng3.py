#!/usr/bin/env python3
"""Run a bounded offline MNENG3/4 MiB experiment; preserve combined output."""
import argparse
import hashlib
import os
from pathlib import Path
import subprocess

from build_mame import ROOT


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seconds', type=int, default=1)
    parser.add_argument('--nvram-directory', type=Path,
                        help='Separate persistent store for an isolated boot experiment')
    args = parser.parse_args()
    if not 1 <= args.seconds <= 60:
        raise SystemExit('--seconds must be between 1 and 60')
    firmware = ROOT/'firmware/MNENG3.SYS'
    digest = hashlib.sha256(firmware.read_bytes()).hexdigest()
    if digest != 'a3764087d79df64eb7124056824652cf23b558fcae2029f887e4a37a3db49ad3':
        raise SystemExit('Unexpected MNENG3 image; this handoff is image-specific')
    run = ROOT/'run'
    roms = run/'roms/ds90tl'
    roms.mkdir(parents=True, exist_ok=True)
    image_link = roms/'mneng3.sys'
    if not image_link.exists():
        image_link.symlink_to(firmware)
    env = os.environ.copy()
    env.update(SDL_VIDEODRIVER='dummy', SDL_AUDIODRIVER='dummy')
    command = [str(ROOT/'build/mame-ds90tl'), 'ds90tl', '-noreadconfig',
               '-rompath', str(run/'roms'), '-bench', str(args.seconds),
               '-skip_gameinfo', '-cfg_directory', str(run/'cfg'),
               '-nvram_directory', str((args.nvram_directory or run/'nvram').resolve())]
    with (run/'bringup.log').open('w') as log:
        try:
            result = subprocess.run(command, cwd=run, env=env, stdout=log,
                                    stderr=subprocess.STDOUT, timeout=120)
        except subprocess.TimeoutExpired:
            raise SystemExit(f'Host timeout; inspect {run/"bringup.log"}')
    print((run/'bringup.log').read_text())
    print(f'Firmware unchanged: {hashlib.sha256(firmware.read_bytes()).hexdigest() == digest}')
    print(f'MAME exit status: {result.returncode}; log: {run/"bringup.log"}')
    raise SystemExit(result.returncode)


if __name__ == '__main__':
    main()
