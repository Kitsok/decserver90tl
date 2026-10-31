#!/usr/bin/env python3
"""Exercise checkpoint queue guards, exclusive writer locks and I/O failure.

Uses temporary copied stores and a Lua component fixture; no host network.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time

from build_mame import ROOT


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--nvram-seed', type=Path, required=True)
    args = parser.parse_args()
    report = {}
    source = args.nvram_seed / 'ds90tl/configram'
    source_hash = digest(source)
    with tempfile.TemporaryDirectory(prefix='ds90-checkpoint-') as temporary:
        work = Path(temporary)
        for case in ('queue_and_lock', 'io_failure', 'malformed_file'):
            stage = work / case
            shutil.copytree(args.nvram_seed, stage / 'nvram')
            store = stage / 'nvram/ds90tl/configram'
            if case == 'malformed_file':
                store.write_bytes(b'invalid length')
            baseline = digest(store)
            env = os.environ.copy()
            env.update(SDL_VIDEODRIVER='dummy', SDL_AUDIODRIVER='dummy', DS90_SERIAL_PTY='0',
                       DS90_ROM_ALIGNMENT_ASSIST='1', DS90_RAM_WAIT_CYCLES='1', DS90_NVRAM_TEST_DIR=str(stage))
            env.pop('DS90_TAP_NAME', None)
            env.pop('DS90_TAP_PCAP', None)
            log_path = ROOT / f'run/nvram-checkpoint-{case}.log'
            command = [str(ROOT / 'build/mame-ds90tl'), 'ds90tl', '-noreadconfig',
                       '-rompath', str(ROOT / 'run/roms'), '-video', 'none', '-sound', 'none',
                       '-throttle', '-networkprovider', 'none', '-cfg_directory', str(stage / 'cfg'),
                       '-nvram_directory', str(stage / 'nvram'), '-autoboot_delay', '1',
                       '-autoboot_script', str(ROOT / 'tests/nvram-checkpoint.lua')]
            original_mode = store.parent.stat().st_mode & 0o777
            with log_path.open('w') as log:
                process = subprocess.Popen(command, cwd=ROOT / 'run', env=env, stdout=log, stderr=subprocess.STDOUT)
                try:
                    def wait_for(predicate, timeout=8):
                        deadline = time.monotonic() + timeout
                        while not predicate():
                            assert process.poll() is None and time.monotonic() < deadline, log_path.read_text()[-2500:]
                            time.sleep(.02)

                    def action(name):
                        (stage / name).touch()
                        wait_for(lambda: (stage / (name + '-done')).exists())

                    if case == 'malformed_file':
                        assert process.wait(timeout=10) != 0
                        assert digest(store) == baseline
                        assert 'readable 65536-byte regular file' in log_path.read_text()
                        report['malformed_file_rejected_without_overwrite'] = True
                        continue
                    wait_for(lambda: (stage / 'ready').exists())
                    time.sleep(.6)  # let the fixture's initial idle state settle
                    baseline = digest(store)
                    if case == 'queue_and_lock':
                        duplicate = subprocess.run(command, cwd=ROOT / 'run', env=env, stdout=subprocess.PIPE,
                                                   stderr=subprocess.STDOUT, text=True, timeout=10)
                        assert duplicate.returncode != 0 and 'Cannot lock NVRAM' in duplicate.stdout
                        assert digest(store) == baseline
                        report['second_writer_rejected_before_store_change'] = True
                    action('flag-pending')
                    time.sleep(.6)
                    assert digest(store) == baseline, 'Checkpoint while firmware flag is pending'
                    action('head-pending')
                    time.sleep(.6)
                    assert digest(store) == baseline, 'Checkpoint while firmware queue head is nonzero'
                    if case == 'io_failure':
                        assert os.geteuid() != 0, 'Run the permission failure test as a normal user'
                        store.parent.chmod(0o555)
                    action('queue-idle')
                    if case == 'io_failure':
                        assert process.wait(timeout=10) != 0
                        assert digest(store) == baseline
                        assert 'NVRAM checkpoint failed' in log_path.read_text()
                        report['unwritable_directory_preserves_previous_checkpoint'] = True
                        continue
                    wait_for(lambda: digest(store) != baseline)
                    assert store.read_bytes()[0xff00 ^ 1] == 0x34
                    assert not list(store.parent.glob('configram.tmp.*'))
                    report['flag_and_head_guards_block_partial_checkpoints'] = True
                    report['idle_queue_releases_atomic_checkpoint'] = True
                    completed = digest(store)
                    action('exit-pending')
                    assert process.wait(timeout=10) == 0
                    assert digest(store) == completed
                    assert 'retained last completed checkpoint' in log_path.read_text()
                    report['normal_exit_preserves_completed_image_when_queue_pending'] = True
                finally:
                    store.parent.chmod(original_mode)
                    if process.poll() is None:
                        process.kill()
                        process.wait()
    assert digest(source) == source_hash
    report['seed_unchanged'] = True
    text = json.dumps(report, indent=2) + '\n'
    (ROOT / 'analysis/nvram-checkpoint-verification.json').write_text(text)
    print(text, end='')


if __name__ == '__main__':
    main()
