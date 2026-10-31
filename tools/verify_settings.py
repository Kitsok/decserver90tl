#!/usr/bin/env python3
"""Diagnose SET/DEFINE/CHANGE and restart persistence in two offline boots.

Uses a copied NVRAM seed and factory privileged password SYSTEM. Only the
copy is changed; the report records observed behavior, including failures.
"""
import hashlib, json, os, re, select, shutil, signal, subprocess, tempfile, threading, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

class Session:

    def __init__(self, work, stage):
        self.output = []
        self.data = bytearray()
        self.pty = None
        self.guest = 0
        self.path = None
        self.reserved = os.openpty()
        self.proc = subprocess.Popen(['python3', str(ROOT / 'tools/run_mneng3.py'), '--interactive', '--rom-alignment-assist', '--ram-wait-cycles', '1', '--nvram-directory', str(work / 'nvram'), '--serial-control', str(work / 'control.sock'), '--log-file', str(ROOT / f'run/settings-{stage}.log')], cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

        def reader():
            for line in self.proc.stdout:
                self.output.append(line)
                m = re.search('SERIAL port=1 path=(\\S+)', line)
                if m:
                    self.path = m[1]
                m = re.search('Emulated ([\\d.]+)/', line)
                if m:
                    self.guest = float(m[1])
        self.thread = threading.Thread(target=reader, daemon=True)
        self.thread.start()

    def wait(self, predicate, timeout):
        end = time.monotonic() + timeout
        while not predicate():
            assert self.proc.poll() is None and time.monotonic() < end, ''.join(self.output[-15:])
            self.collect(0.05) if self.pty is not None else time.sleep(0.05)

    def collect(self, seconds):
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            ready, _, _ = select.select([self.pty], [], [], min(0.05, max(0, end - time.monotonic())))
            if ready:
                try:
                    self.data.extend(os.read(self.pty, 65536))
                except BlockingIOError:
                    pass

    def send(self, text, spacing=0.02):
        for byte in text:
            os.write(self.pty, bytes([byte]))
            self.collect(spacing)

    def prompt(self, start, timeout=15):
        end = time.monotonic() + timeout
        while not re.search(b'(?:^|[\\r\\n])Local> ', self.data[start:]):
            assert time.monotonic() < end, repr(bytes(self.data[start:]))
            self.collect(0.1)
        self.collect(0.2)
        return bytes(self.data[start:]).decode('ascii', errors='replace')

    def login(self):
        self.wait(lambda: self.path is not None, 15)
        self.pty = os.open(self.path, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
        self.wait(lambda: self.guest >= 30, 100)
        self.send(b'\r\r\r', 1)
        start = len(self.data)
        self.send(b'SIMULATOR\r', 0.1)
        self.prompt(start)

    def command(self, text):
        start = len(self.data)
        self.send(text.encode() + b'\r')
        return self.prompt(start)

    def privilege(self):
        start = len(self.data)
        self.send(b'SET PRIVILEGED\r')
        self.wait(lambda: b'Password>' in self.data[start:], 10)
        start = len(self.data)
        self.send(b'SYSTEM\r')
        self.prompt(start)

    def stop(self):
        if self.proc.poll() is None:
            self.proc.send_signal(signal.SIGINT)
            try:
                self.proc.wait(timeout=8)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.wait()
        self.thread.join(timeout=2)
        self.proc.stdout.close()
        for fd in ([self.pty] if self.pty is not None else []) + list(self.reserved):
            os.close(fd)

def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--nvram-seed', type=Path, required=True)
    parser.add_argument('--report', type=Path, default=ROOT / 'analysis/settings-verification.json')
    args = parser.parse_args()
    report = {}
    with tempfile.TemporaryDirectory(prefix='ds90-settings-') as temporary:
        work = Path(temporary)
        shutil.copytree(args.nvram_seed, work / 'nvram')
        store = work / 'nvram/ds90tl/configram'
        report['initial_file_sha256'] = digest(store)
        report['file_bytes'] = store.stat().st_size
        session = Session(work, 'write')
        try:
            session.login()
            session.privilege()
            report['commands'] = []
            for command in ['SET SERVER NAME DS90VOL', 'SHOW SERVER', 'DEFINE SERVER NAME DS90DEFINED', 'SHOW SERVER', 'LIST SERVER', 'CHANGE SERVER NAME DS90SAVED', 'SHOW SERVER', 'LIST SERVER']:
                response = session.command(command)
                report['commands'].append({'command': command, 'response': response})
            before_wait = session.guest
            session.wait(lambda: session.guest >= before_wait + 15, 30)
            report['minimum_simulated_write_drain_seconds'] = 10
            report['file_sha256_before_exit'] = digest(store)
        finally:
            session.stop()
        report['file_sha256_after_exit'] = digest(store)
        report['host_file_unchanged_while_running'] = report['file_sha256_before_exit'] == report['initial_file_sha256']
        report['host_file_changed_after_exit'] = report['file_sha256_after_exit'] != report['initial_file_sha256']
        session = Session(work, 'restart')
        try:
            session.login()
            session.privilege()
            report['restart_show_server'] = session.command('SHOW SERVER')
            report['restart_list_server'] = session.command('LIST SERVER')
            report['change_restored_to_operational_database'] = 'DS90SAVED' in report['restart_show_server']
            report['change_survived_in_permanent_database'] = 'DS90SAVED' in report['restart_list_server']
            report['startup_warnings'] = [line for line in session.output if 'Local -602-' in line or 'Local -603-' in line]
        finally:
            session.stop()
    responses = [item['response'] for item in report['commands']]
    report['in_session_checks'] = {
        'set_updates_operational': 'DS90VOL' in responses[1],
        'define_leaves_operational_unchanged': 'DS90VOL' in responses[3],
        'define_updates_permanent': 'DS90DEFINED' in responses[4],
        'change_updates_operational': 'DS90SAVED' in responses[6],
        'change_updates_permanent': 'DS90SAVED' in responses[7],
    }
    args.report.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({key: value for key, value in report.items() if key != 'commands'}, indent=2))
if __name__ == '__main__':
    main()
