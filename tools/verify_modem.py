#!/usr/bin/env python3
"""Exercise real firmware flow control and all eight modem sidebands.

Requires a previously initialized NVRAM seed; copies it into an isolated store.
Runs the built simulator, logs in via port 1, checks XON/XOFF and DSR gating,
then requests normal shutdown. No running simulator or seed is modified.
"""
import argparse
import json
import os
from pathlib import Path
import re
import select
import shutil
import signal
import subprocess
import tempfile
import threading
import time

from serial_control import ModemControl, ROOT


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--nvram-seed', type=Path, required=True)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    report = {'firmware': 'MNENG3.SYS', 'ram_mib': 4}
    with tempfile.TemporaryDirectory(prefix='ds90-modem-') as temporary:
        work = Path(temporary)
        shutil.copytree(args.nvram_seed, work / 'nvram')
        log = ROOT / 'run/modem-verification.log'
        command = ['python3', str(ROOT / 'tools/run_mneng3.py'), '--interactive',
                   '--rom-alignment-assist', '--ram-wait-cycles', '1',
                   '--nvram-directory', str(work / 'nvram'),
                   '--serial-control', str(work / 'control.sock'), '--log-file', str(log)]
        # Reserve the lowest recycled PTY against reconnecting terminal clients.
        reserved = os.openpty()
        process = subprocess.Popen(command, cwd=ROOT, stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT, text=True)
        paths = {}
        output = []
        guest_seconds = [0.0]
        fds = []

        def console_reader():
            for line in process.stdout:
                output.append(line)
                match = re.search(r'SERIAL port=(\d+) path=(\S+)', line)
                if match:
                    paths[int(match[1])] = match[2]
                match = re.search(r'Emulated ([\d.]+)/', line)
                if match:
                    guest_seconds[0] = float(match[1])

        reader = threading.Thread(target=console_reader, daemon=True)
        reader.start()

        def wait_for(predicate, timeout=15):
            deadline = time.monotonic() + timeout
            while not predicate():
                if process.poll() is not None or time.monotonic() >= deadline:
                    raise AssertionError('Simulator wait failed:\n' + ''.join(output[-20:]))
                time.sleep(.05)

        try:
            wait_for(lambda: len(paths) == 8)
            for port in range(1, 9):
                fds.append(os.open(paths[port], os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK))
            fd = fds[0]
            data = bytearray()

            def collect(seconds):
                deadline = time.monotonic() + seconds
                start = len(data)
                while time.monotonic() < deadline:
                    ready, _, _ = select.select([fd], [], [], min(.05, max(0, deadline - time.monotonic())))
                    if ready:
                        try:
                            data.extend(os.read(fd, 65536))
                        except BlockingIOError:
                            pass
                return bytes(data[start:])

            def send(value, spacing=.02):
                for byte in value:
                    os.write(fd, bytes([byte]))
                    collect(spacing)

            def prompt_since(start, timeout=15):
                deadline = time.monotonic() + timeout
                while b'Local>' not in data[start:]:
                    assert time.monotonic() < deadline, repr(bytes(data[start:]))
                    collect(.1)
                collect(.2)

            with ModemControl(work / 'control.sock') as modem:
                initial = [modem.request(f'GET {port}') for port in range(1, 9)]
                assert all(item['dsr'] == 1 for item in initial)
                for port in range(1, 9):
                    state = modem.request(f'SET {port} DSR 0')
                    mask = 1 if port % 2 else 4
                    assert state['dsr'] == 0 and state['input_pins'] & mask, state
                    for other in range(1, 9):
                        if other != port:
                            assert modem.request(f'GET {other}')['dsr'] == 1
                    state = modem.request(f'SET {port} DSR 1')
                    assert not state['input_pins'] & mask, state
                for request in ('SET 1 CTS 0', 'SET 0 DSR 1', 'SET 9 DSR 1', 'SET 1 DSR 2', 'GET 1 extra'):
                    try:
                        modem.request(request)
                    except ValueError:
                        pass
                    else:
                        raise AssertionError(request)
                report['eight_dsr_inputs_and_port_isolation'] = True
                report['invalid_requests_rejected'] = True
                wait_for(lambda: guest_seconds[0] >= 30, timeout=100)
                collect(.1)
                send(b'\r\r\r', spacing=1)
                start = len(data)
                send(b'SIMULATOR\r', spacing=.1)
                prompt_since(start)
                report['pty_local_login'] = True
                report['logged_in_state'] = modem.request('GET 1')
                assert report['logged_in_state']['dtr'] == 1

                # Software flow control belongs to firmware, not the transport.
                send(b'\x13')
                collect(.4)
                start = len(data)
                send(b'SHOW PORT\r')
                collect(.5)
                assert len(data) == start, ('Output while XOFF', bytes(data[start:]))
                send(b'\x11')
                prompt_since(start)
                report['firmware_xoff_stops_xon_resumes'] = True

                start = len(data)
                send(b'SET PORT FLOW CONTROL DSR\r')
                prompt_since(start)
                state = modem.request('GET 1')
                assert state['dsr_flow'] and state['rx_dtr_flow'], (state, bytes(data[start:]))
                report['dsr_flow_state'] = state
                modem.request('SET 1 DSR 0')
                collect(.3)
                start = len(data)
                send(b'SHOW PORT\r')
                collect(.5)
                assert len(data) == start, ('Output while DSR low', bytes(data[start:]))
                held = modem.request('GET 1')
                assert not (held['sr'] & 4), held  # THR occupied: no false TxRDY
                report['dsr_held_state'] = held
                modem.request('SET 1 DSR 1')
                prompt_since(start)
                report['dsr_stops_transmitter_and_resumes'] = True
                report['port1_output_bytes'] = len(data)
            process.send_signal(signal.SIGINT)
            process.wait(timeout=8)
            reader.join(timeout=2)
            assert not (work / 'control.sock').exists(), 'Control socket leaked'
            assert (work / 'nvram/ds90tl/configram').exists(), 'Configuration not saved'
            report['normal_shutdown_and_socket_cleanup'] = True
        finally:
            if process.poll() is None:
                process.send_signal(signal.SIGINT)
                try:
                    process.wait(timeout=8)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
            reader.join(timeout=2)
            process.stdout.close()
            for fd in fds + list(reserved):
                os.close(fd)
    text = json.dumps(report, indent=2) + '\n'
    if args.report:
        args.report.write_text(text)
    print(text, end='')


if __name__ == '__main__':
    main()
