#!/usr/bin/env python3
"""Inspect eight 90TL modem interfaces or set a modem's DSR input.

The PTYs carry data; this local datagram socket carries DTR/DSR state.
The real 90TL has no CTS/RTS, DCD or RI connector signals.
"""
import argparse
import json
from pathlib import Path
import socket
import tempfile

ROOT = Path(__file__).resolve().parents[1]


class ModemControl:
    def __init__(self, path):
        self.path = str(Path(path).resolve())
        self.directory = tempfile.TemporaryDirectory(prefix='ds90-control-')
        self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        self.socket.settimeout(3)
        try:
            self.socket.bind(str(Path(self.directory.name) / 'client.sock'))
            self.socket.connect(self.path)
        except BaseException:
            self.close()
            raise

    def close(self):
        self.socket.close()
        self.directory.cleanup()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def request(self, command):
        self.socket.send(command.encode('ascii'))
        result = json.loads(self.socket.recv(4096))
        if 'error' in result:
            raise ValueError(result['error'])
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--socket', type=Path, default=ROOT / 'run/serial-control.sock')
    commands = parser.add_subparsers(dest='command', required=True)
    get = commands.add_parser('get', help='Read signal and UART state')
    get.add_argument('port', choices=['all'] + [str(port) for port in range(1, 9)])
    setter = commands.add_parser('set', help='Set a modem input (DSR only)')
    setter.add_argument('port', type=int, choices=range(1, 9))
    setter.add_argument('signal', choices=['dsr'])
    setter.add_argument('value', type=int, choices=[0, 1])
    args = parser.parse_args()
    try:
        with ModemControl(args.socket) as client:
            if args.command == 'get':
                ports = range(1, 9) if args.port == 'all' else [int(args.port)]
                result = [client.request(f'GET {port}') for port in ports]
                if args.port != 'all':
                    result = result[0]
            else:
                result = client.request(f'SET {args.port} DSR {args.value}')
        print(json.dumps(result, indent=2))
    except (OSError, ValueError) as error:
        parser.exit(1, f'Modem control failed: {error}\n')


if __name__ == '__main__':
    main()
