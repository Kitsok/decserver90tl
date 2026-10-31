#!/usr/bin/env python3
"""Verify live NVRAM checkpoints survive SIGKILL with real firmware commands.

Uses a copied initialized store and factory privileged password SYSTEM. Kills
only its own MAME child; no normal-exit save can satisfy the durability check.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import signal
import tempfile

from verify_settings import ROOT, Session, digest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--nvram-seed', type=Path, required=True)
    args = parser.parse_args()
    source = args.nvram_seed / 'ds90tl/configram'
    source_hash = digest(source)
    report = {}
    with tempfile.TemporaryDirectory(prefix='ds90-durability-') as temporary:
        work = Path(temporary)
        shutil.copytree(args.nvram_seed, work / 'nvram')
        store = work / 'nvram/ds90tl/configram'
        mode = store.stat().st_mode & 0o777

        def contains(value):
            raw = store.read_bytes()
            cpu_bytes = bytearray(raw)
            cpu_bytes[::2], cpu_bytes[1::2] = raw[1::2], raw[::2]
            return value.encode() in cpu_bytes

        def crash(session):
            children = Path(f'/proc/{session.proc.pid}/task/{session.proc.pid}/children').read_text().split()
            assert len(children) == 1, children
            os.kill(int(children[0]), signal.SIGKILL)
            session.proc.wait(timeout=8)
            assert session.proc.returncode != 0
            session.stop()
            # SIGKILL cannot run the unrelated PTY sideband's cleanup.
            (work / 'control.sock').unlink(missing_ok=True)

        session = Session(work, 'runtime-define')
        try:
            session.login()
            session.privilege()
            session.collect(1)
            baseline = digest(store)
            session.command('SET SERVER NAME DS90VOL')
            session.collect(1)
            assert digest(store) == baseline, 'SET unexpectedly changed NVRAM'
            report['set_does_not_checkpoint_operational_only_changes'] = True
            session.command('DEFINE SERVER NAME DS90DEFINED')
            session.wait(lambda: contains('DS90DEFINED'), 20)
            report['define_saved_before_exit'] = digest(store) != baseline
            assert report['define_saved_before_exit']
            assert store.stat().st_mode & 0o777 == mode
            assert not list(store.parent.glob('configram.tmp.*'))
            report['existing_file_permissions_preserved'] = True
            crash(session)
        finally:
            if session.proc.poll() is None:
                session.stop()

        session = Session(work, 'runtime-change')
        try:
            session.login()
            session.privilege()
            shown = session.command('SHOW SERVER')
            assert 'DS90DEFINED' in shown and 'DS90VOL' not in shown, shown
            assert 'DS90DEFINED' in session.command('LIST SERVER')
            report['define_restored_after_sigkill_set_value_discarded'] = True
            session.command('CHANGE SERVER NAME DS90CRASH')
            session.wait(lambda: contains('DS90CRASH'), 20)
            report['change_saved_before_exit'] = True
            report['checkpoint_sha256'] = digest(store)
            crash(session)
        finally:
            if session.proc.poll() is None:
                session.stop()

        session = Session(work, 'runtime-restart')
        try:
            session.login()
            session.privilege()
            assert 'DS90CRASH' in session.command('SHOW SERVER')
            assert 'DS90CRASH' in session.command('LIST SERVER')
            assert not any('-602-' in line or '-603-' in line for line in session.output)
            report['change_restored_after_sigkill_in_both_databases'] = True
            report['startup_warnings_absent'] = True
        finally:
            session.stop()
    assert digest(source) == source_hash, 'Seed was modified'
    report['seed_unchanged'] = True
    report['original_backing_file_size'] = source.stat().st_size
    text = json.dumps(report, indent=2) + '\n'
    (ROOT / 'analysis/nvram-runtime-verification.json').write_text(text)
    print(text, end='')


if __name__ == '__main__':
    main()
