#!/usr/bin/env python3
"""Check factory provisioning, preserving metadata, and genuine checksum failure."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

from build_mame import ROOT


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--nvram-seed', type=Path, required=True)
    args = parser.parse_args()
    source = args.nvram_seed / 'ds90tl/configram'
    before = hashlib.sha256(source.read_bytes()).hexdigest()
    firmware = (ROOT / 'firmware/MNENG3.SYS').read_bytes()
    results = {}
    with tempfile.TemporaryDirectory(prefix='ds90-handoff-') as temporary:
        work = Path(temporary)
        for case in ('valid_saved_record', 'corrupt_saved_record', 'existing_factory_fields', 'fresh_erased_store'):
            stage = work / case
            stage.mkdir()
            if case != 'fresh_erased_store':
                shutil.copytree(args.nvram_seed, stage / 'nvram')
                store = stage / 'nvram/ds90tl/configram'
                raw = bytearray(store.read_bytes())
                if case == 'corrupt_saved_record':
                    raw[0x116e ^ 1] ^= 1  # CPU byte order within host 16-bit share
                if case == 'existing_factory_fields':
                    for offset, address, length in ((8,0x786c264,14),(30,0x786c272,20),(50,0x786c286,8)):
                        for index in range(length):
                            raw[(0xc00 + offset + index) ^ 1] = firmware[address - 0x7805000 + index]
                    for index, byte in enumerate(b'\x06CUSTOM'):
                        raw[(0xc1e + index) ^ 1] = byte
                store.write_bytes(raw)
            env = os.environ.copy()
            env.update(SDL_VIDEODRIVER='dummy', SDL_AUDIODRIVER='dummy',
                       DS90_SERIAL_PTY='0', DS90_ROM_ALIGNMENT_ASSIST='1', DS90_RAM_WAIT_CYCLES='1',
                       DS90_EXPECT_SERVER_FALLBACK='1' if case in ('corrupt_saved_record', 'fresh_erased_store') else '0',
                       DS90_CUSTOM_FACTORY='1' if case == 'existing_factory_fields' else '0')
            env.pop('DS90_TAP_NAME', None)
            env.pop('DS90_TAP_PCAP', None)
            log_path = ROOT / f'run/settings-handoff-{case}.log'
            command = [str(ROOT / 'build/mame-ds90tl'), 'ds90tl', '-noreadconfig',
                       '-rompath', str(ROOT / 'run/roms'), '-bench', '2', '-networkprovider', 'none',
                       '-cfg_directory', str(stage / 'cfg'), '-nvram_directory', str(stage / 'nvram'),
                       '-autoboot_delay', '1', '-autoboot_script', str(ROOT / 'tests/settings-handoff.lua')]
            with log_path.open('w') as log:
                process = subprocess.run(command, cwd=ROOT / 'run', env=env, stdout=log,
                                         stderr=subprocess.STDOUT, timeout=30)
            output = log_path.read_text()
            assert process.returncode == 0 and 'DS90 SETTINGS-HANDOFF-PASS' in output, output[-3000:]
            results[case] = next(line for line in output.splitlines() if 'DS90 SETTINGS-HANDOFF-PASS' in line)
    assert hashlib.sha256(source.read_bytes()).hexdigest() == before, 'Seed was modified'
    (ROOT / 'analysis/settings-handoff-verification.json').write_text(json.dumps(results, indent=2) + '\n')
    print(json.dumps(results, indent=2))


if __name__ == '__main__':
    main()
