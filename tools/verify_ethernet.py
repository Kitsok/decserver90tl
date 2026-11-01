#!/usr/bin/env python3
"""Verify real MNENG3 Ethernet through a prepared isolated bridge and TAP.

Copies the NVRAM seed and configures only that copy. Requires the lab from
network.sh and permission to attach its TAP; never changes host interfaces.
"""
import argparse
import json
import os
from pathlib import Path
import re
import select
import socket
import shutil
import signal
import subprocess
import tempfile
import threading
import time

from build_mame import ROOT
from ethernet_capture import summarize_capture


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--nvram-seed', type=Path, required=True)
    parser.add_argument('--report', type=Path)
    parser.add_argument('--tap', default='ds90tap')
    parser.add_argument('--bridge', default='brds90')
    parser.add_argument('--address', default='192.0.2.90')
    args = parser.parse_args()
    report = {'firmware': 'MNENG3.SYS', 'ram_mib': 4}
    with tempfile.TemporaryDirectory(prefix='ds90-network-') as temporary:
        work = Path(temporary)
        shutil.copytree(args.nvram_seed, work / 'nvram')
        log = ROOT / 'run/ethernet-verification.log'
        command = ['python3', str(ROOT / 'tools/run_mneng3.py'), '--trace', '--interactive',
                   '--rom-alignment-assist', '--ram-wait-cycles', '1', '--tap', args.tap,
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

            wait_for(lambda: guest_seconds[0] >= 30, timeout=100)
            collect(.1)
            send(b'\r\r\r', spacing=1)
            start = len(data)
            send(b'SIMULATOR\r', spacing=.1)
            prompt_since(start)
            report['pty_local_login'] = True
            start = len(data)
            send(b'SET PRIVILEGED\r')
            deadline = time.monotonic() + 10
            while b'Password>' not in data[start:]:
                assert time.monotonic() < deadline, repr(bytes(data[start:]))
                collect(.1)
            start = len(data)
            send(b'SYSTEM\r')
            prompt_since(start)
            report['privileged_login'] = True
            responses = {}
            for command_text in ('SET INTERNET SUBNET MASK 255.255.255.0',
                                 f'SET INTERNET ADDRESS {args.address}'):
                start = len(data)
                send(command_text.encode() + b'\r')
                prompt_since(start)
                responses[command_text] = bytes(data[start:]).decode('ascii', errors='replace')
            report['configuration_responses'] = responses
            collect(1)
            ping = subprocess.run(['ping', '-n', '-I', args.bridge, '-c', '3', '-W', '2', args.address],
                                  text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=15)
            report['ping_returncode'] = ping.returncode
            report['ping_output'] = ping.stdout
            print(ping.stdout, flush=True)
            assert ping.returncode == 0, (responses, ping.stdout)
            try:
                with socket.create_connection((args.address, 23), timeout=3) as connection:
                    connection.settimeout(2)
                    try:
                        banner = connection.recv(4096)
                    except socket.timeout:
                        banner = b''
                    report['tcp_port_23'] = 'connected'
                    report['tcp_port_23_initial_bytes_hex'] = banner.hex()
            except OSError as error:
                report['tcp_port_23'] = str(error)
            collect(.3)
            report.update(summarize_capture(log.with_suffix('.pcap')))
            assert report['station_mac_seen'] and report['station_arp_replies'] >= 1, report
            assert report['station_icmp_echo_replies'] >= 3, report
            assert report['tcp_port_23'] == 'connected', report
            assert report['tcp_port_23_initial_bytes_hex'].startswith('ff'), report
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
