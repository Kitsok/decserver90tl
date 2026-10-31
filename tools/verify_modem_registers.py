#!/usr/bin/env python3
"""Verify eight UART modem interfaces using a Lua-driven component fixture.

This halts firmware execution in a private RAM loop and explicitly tests the
register model. Firmware login/flow control is verified by verify_modem.py.
"""
import argparse
import json
import os
from pathlib import Path
import re
import select
import signal
import subprocess
import tempfile
import time

from serial_control import ModemControl, ROOT


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    result = {'kind': 'isolated UART register component test', 'ports': 8}
    with tempfile.TemporaryDirectory(prefix='ds90-registers-') as temporary:
        work = Path(temporary)
        env = os.environ.copy()
        env.update(DS90_SERIAL_PTY='1', DS90_SERIAL_CONTROL=str(work / 'control.sock'),
                   DS90_ROM_ALIGNMENT_ASSIST='1', DS90_RAM_WAIT_CYCLES='1',
                   DS90_MODEM_TEST_DIR=str(work), SDL_VIDEODRIVER='dummy', SDL_AUDIODRIVER='dummy')
        log_path = ROOT / 'run/modem-register-verification.log'
        command = [str(ROOT / 'build/mame-ds90tl'), 'ds90tl', '-noreadconfig',
                   '-rompath', str(ROOT / 'run/roms'), '-video', 'none', '-sound', 'none',
                   '-throttle', '-skip_gameinfo', '-cfg_directory', str(work / 'cfg'),
                   '-nvram_directory', str(work / 'nvram'), '-autoboot_delay', '1',
                   '-autoboot_script', str(ROOT / 'tests/modem-registers.lua')]
        # Keep the lowest recycled PTY separate from the actual test ports:
        # a user's terminal may still be reconnecting to the old port-1 path.
        reserved = os.openpty()
        fds = []
        with log_path.open('w') as log:
            process = subprocess.Popen(command, cwd=ROOT / 'run', env=env, stdout=log, stderr=subprocess.STDOUT)
            try:
                def wait_for(predicate, timeout=10):
                    deadline = time.monotonic() + timeout
                    while not predicate():
                        assert process.poll() is None and time.monotonic() < deadline, log_path.read_text()[-3000:]
                        time.sleep(.02)

                wait_for(lambda: (work / 'ready').exists())
                paths = dict((int(port), path) for port, path in re.findall(r'DS90 SERIAL port=(\d+) path=(\S+)', log_path.read_text()))
                assert len(paths) == 8, paths
                for port in range(1, 9):
                    fds.append(os.open(paths[port], os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK))

                def action(name):
                    (work / name).touch()
                    wait_for(lambda: (work / (name + '-done')).exists())
                    time.sleep(.05)

                def collect(seconds=.1):
                    data = [bytearray() for _ in fds]
                    deadline = time.monotonic() + seconds
                    while time.monotonic() < deadline:
                        ready, _, _ = select.select(fds, [], [], .01)
                        for fd in ready:
                            data[fds.index(fd)].extend(os.read(fd, 65536))
                    return [bytes(item) for item in data]

                with ModemControl(work / 'control.sock') as modem:
                    def states():
                        return [modem.request(f'GET {port}') for port in range(1, 9)]

                    for port in range(1, 9):
                        modem.request(f'SET {port} DSR 0')
                    assert all(item['dtr'] for item in states())
                    action('transmit')
                    assert collect() == [b''] * 8
                    assert all(not (item['sr'] & 4) for item in states())
                    for port in range(1, 9):
                        modem.request(f'SET {port} DSR 1')
                    actual = collect(.5)
                    assert actual == [bytes([64 + port]) for port in range(1, 9)], actual
                    result['dsr_holds_and_resumes_exact_byte_on_all_ports'] = True
                    action('dtr-low')
                    assert all(not item['dtr'] for item in states())
                    action('dtr-high')
                    assert all(item['dtr'] for item in states())
                    result['extended_assert_negate_dtr_commands_on_all_ports'] = True
                    for fd in fds:
                        os.write(fd, b'abc')
                    time.sleep(.1)
                    assert all(not item['dtr'] and item['sr'] & 2 for item in states())
                    action('receive-drain')
                    assert all(item['dtr'] and not (item['sr'] & 2) for item in states())
                    action('reset-receivers')
                    result['full_rx_fifo_drops_dtr_and_drain_restores_on_all_ports'] = True
                    for port in range(1, 9):
                        modem.request(f'SET {port} DSR 0')
                    action('ignore-dsr')
                    assert collect() == [bytes([96 + port]) for port in range(1, 9)]
                    result['disabled_dsr_flow_allows_transmission_on_all_ports'] = True
                    action('hold-reset')
                    assert collect() == [b''] * 8
                    action('reset-transmitters')
                    for port in range(1, 9):
                        modem.request(f'SET {port} DSR 1')
                    assert collect() == [b''] * 8
                    result['reset_discards_held_transmit_byte_on_all_ports'] = True
                process.send_signal(signal.SIGINT)
                assert process.wait(timeout=8) == 0
                assert not (work / 'control.sock').exists()
            finally:
                if process.poll() is None:
                    process.send_signal(signal.SIGINT)
                    try:
                        process.wait(timeout=8)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait()
                for fd in fds + list(reserved):
                    os.close(fd)
    text = json.dumps(result, indent=2) + '\n'
    if args.report:
        args.report.write_text(text)
    print(text, end='')


if __name__ == '__main__':
    main()
