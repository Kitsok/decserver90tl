#!/usr/bin/env python3
"""Exercise eight Telnet serial listeners on a prepared isolated TAP lab."""
import argparse
from contextlib import ExitStack
import json
import os
from pathlib import Path
import re
import select
import shutil
import tempfile
import time

import pexpect

from verify_settings import ROOT, Session, digest
from serial_control import ModemControl


def receive(fd, seconds):
    data = bytearray()
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        if select.select([fd], [], [], min(.05, max(0, end-time.monotonic())))[0]:
            try:
                data.extend(os.read(fd, 65536))
            except BlockingIOError:
                pass
    return bytes(data)


def until(fd, marker, timeout=10):
    data = bytearray()
    end = time.monotonic() + timeout
    while marker not in data:
        assert time.monotonic() < end, (marker, bytes(data))
        data.extend(receive(fd, .05))
    return bytes(data)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--nvram-seed', type=Path, required=True)
    parser.add_argument('--tap', default='ds90tap')
    parser.add_argument('--address', default='192.0.2.90')
    parser.add_argument('--ports', default='1,2,3,4,5,6,7,8')
    args = parser.parse_args()
    seed = args.nvram_seed / 'ds90tl/configram'
    original = digest(seed)
    report = {'address': args.address, 'ports': [], 'configuration': []}
    listeners = {port: 2000+port for port in range(1, 9)}
    clients = []
    fds = []
    with ExitStack() as resources, tempfile.TemporaryDirectory(prefix='ds90-telnet-ports-') as temporary:
        # Keep recycled low PTYs occupied across both boots. A user's tio can
        # otherwise reconnect to /dev/pts/2 and consume the test's serial bytes.
        for _ in range(8):
            for fd in os.openpty():
                resources.callback(os.close, fd)
        work = Path(temporary)
        shutil.copytree(args.nvram_seed, work / 'nvram')
        session = Session(work, 'telnet-ports', ('--tap', args.tap))
        transcript = (ROOT / 'run/telnet-ports-transcript.log').open('wb')
        try:
            session.login()
            session.privilege()
            for command in ('CHANGE INTERNET SUBNET MASK 255.255.255.0',
                            f'CHANGE INTERNET ADDRESS {args.address}', 'SET NOPRIVILEGED'):
                session.command(command)
            console = pexpect.spawn('/usr/bin/telnet', [args.address, '23'], timeout=20)
            clients.append(console)
            console.logfile = transcript
            console.linesep = b'\r'
            console.expect(b'Escape character is')
            console.sendline(b'')
            console.expect(b'#\x00')
            console.sendline(b'ACCESS')
            console.expect(b'Enter username>')
            console.sendline(b'PORT_TEST')
            console.expect(rb'(?m)^Local> ')
            console.sendline(b'SET PRIVILEGED')
            console.expect(b'Password>')
            console.sendline(b'SYSTEM')
            console.expect(rb'(?m)^Local> ')

            def command(text):
                console.sendline(text.encode())
                console.expect(rb'(?m)^Local> ')
                response = console.before.decode('ascii', errors='replace')
                report['configuration'].append({'command': text, 'response': response})
                assert not re.search(r'Local -\d+-', response), response
                return response

            for port in range(1, 9):
                for setting in ('AUTOBAUD DISABLED', 'CHARACTER SIZE 8', 'PARITY NONE',
                                'SPEED 9600', 'FLOW CONTROL DISABLED'):
                    command(f'CHANGE PORT {port} {setting}')
                command(f'DEFINE PORT {port} ACCESS REMOTE')
                command(f'LOGOUT PORT {port}')
                command(f'CHANGE TELNET LISTENER {2000+port} PORTS {port}')
                command(f'CHANGE TELNET LISTENER {2000+port} CONNECTIONS ENABLED')
            guest = session.guest
            session.wait(lambda: session.guest >= guest + 10, 30)
            console.sendline(b'LOGOUT')
            console.expect(pexpect.EOF)
            console.close()
            session.stop()
            session = Session(work, 'telnet-ports-restored', ('--tap', args.tap))
            session.wait(lambda: session.guest >= 30, 100)
            console = pexpect.spawn('/usr/bin/telnet', [args.address, '23'], timeout=20)
            clients.append(console)
            console.logfile = transcript
            console.linesep = b'\r'
            console.expect(b'Escape character is')
            console.sendline(b'')
            console.expect(b'#\x00')
            console.sendline(b'ACCESS')
            console.expect(b'Enter username>')
            console.sendline(b'PORT_TEST')
            console.expect(rb'(?m)^Local> ')
            console.sendline(b'SET PRIVILEGED')
            console.expect(b'Password>')
            console.sendline(b'SYSTEM')
            console.expect(rb'(?m)^Local> ')
            report['restarted_with_saved_configuration'] = True
            report['listener7_before'] = command('SHOW TELNET LISTENER 2007')
            report['listener8_before'] = command('SHOW TELNET LISTENER 2008')
            paths = {int(p): path for line in session.output
                     for p, path in re.findall(r'SERIAL port=(\d+) path=(\S+)', line)}
            assert len(paths) == 8, paths
            for port in range(1, 9):
                fds.append(os.open(paths[port], os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK))
            for fd in fds:
                receive(fd, .1)

            def connect(port):
                client = pexpect.spawn('/usr/bin/telnet', ['-8', args.address, str(listeners[port])], timeout=15)
                clients.append(client)
                client.logfile = transcript
                try:
                    client.expect(b'Escape character is')
                except pexpect.EOF:
                    report[f'port{port}_show'] = command(f'SHOW PORT {port}')
                    report[f'port{port}_list'] = command(f'LIST PORT {port}')
                    report[f'listener{port}_at_refusal'] = command(f'SHOW TELNET LISTENER {2000+port}')
                    raise
                return client

            with ModemControl(work / 'control.sock') as modem:
                for port in map(int, args.ports.split(',')):
                    fd = fds[port-1]
                    client = connect(port)
                    print(f'Testing serial port {port}', flush=True)
                    down = f'NET_TO_SERIAL_{port}_END'.encode()
                    client.send(down)
                    until(fd, down)
                    up = f'SERIAL_TO_NET_{port}_END'.encode()
                    for byte in up:
                        os.write(fd, bytes([byte]))
                        time.sleep(.02)
                    client.expect_exact(up)
                    # No other serial output may contain this port's marker.
                    for other in fds:
                        if other != fd:
                            assert down not in receive(other, .02)
                    command(f'SET PORT {port} FLOW CONTROL DSR')
                    modem.request(f'SET {port} DSR 0')
                    receive(fd, .2)
                    held = f'DSR_HELD_{port}_END'.encode()
                    client.send(held)
                    assert held not in receive(fd, .5), 'Output continued with DSR low'
                    modem.request(f'SET {port} DSR 1')
                    until(fd, held)
                    command(f'SET PORT {port} FLOW CONTROL XON')
                    os.write(fd, b'\x13')
                    time.sleep(.3)
                    held = f'XOFF_HELD_{port}_END'.encode()
                    client.send(held)
                    assert held not in receive(fd, .5), 'Output continued with XOFF'
                    os.write(fd, b'\x11')
                    until(fd, held)
                    command(f'SET PORT {port} FLOW CONTROL DISABLED')
                    client.close(force=True)
                    time.sleep(.5)
                    replacement = connect(port)
                    marker = f'RECONNECT_{port}_END'.encode()
                    replacement.send(marker)
                    until(fd, marker)
                    replacement.close(force=True)
                    report['ports'].append({'port': port, 'tcp_port': listeners[port],
                                            'bidirectional': True, 'dsr': True,
                                            'xon_xoff': True, 'reconnect': True})
            report['passed'] = True
        except Exception as error:
            report['passed'] = False
            report['error'] = str(error)
            raise
        finally:
            for client in clients:
                if client.isalive():
                    client.close(force=True)
            session.stop()
            transcript.close()
            for fd in fds:
                os.close(fd)
            report['seed_unchanged'] = digest(seed) == original
            (ROOT / 'analysis/telnet-ports-verification.json').write_text(json.dumps(report, indent=2)+'\n')
    assert report['seed_unchanged']
    print(json.dumps(report['ports'], indent=2))


if __name__ == '__main__':
    main()
