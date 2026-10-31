#!/usr/bin/env python3
"""Test Telnet console login on a prepared TAP lab using copied settings."""
import argparse
import json
import shutil
import tempfile
from pathlib import Path

import pexpect

from verify_settings import ROOT, Session, digest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--nvram-seed', type=Path, required=True)
    parser.add_argument('--tap', default='ds90tap')
    parser.add_argument('--address', default='192.0.2.90')
    args = parser.parse_args()
    seed = args.nvram_seed / 'ds90tl/configram'
    before = digest(seed)
    report = {'address': args.address, 'sessions': []}
    with tempfile.TemporaryDirectory(prefix='ds90-telnet-') as temporary:
        work = Path(temporary)
        shutil.copytree(args.nvram_seed, work / 'nvram')
        session = Session(work, 'telnet', ('--tap', args.tap))
        try:
            session.login()
            session.privilege()
            report['server_before'] = session.command('SHOW SERVER')
            report['remote_console_before'] = session.command('SHOW SERVER REMOTE CONSOLE')
            report['configuration'] = [session.command(command) for command in (
                'SET INTERNET SUBNET MASK 255.255.255.0',
                f'SET INTERNET ADDRESS {args.address}',
                'SET NOPRIVILEGED')]
            with (ROOT / 'run/telnet-transcript.log').open('w') as transcript:
                for attempt in range(2):
                    client = pexpect.spawn('/usr/bin/telnet', [args.address, '23'],
                                           encoding='ascii', codec_errors='replace', timeout=20)
                    client.logfile = transcript
                    client.linesep = '\r'
                    responses = {}
                    try:
                        client.expect('Escape character is')
                        client.sendline('')
                        for _ in range(8):
                            state = client.expect([r'(?im)^Local> ', r'Password>', r'Enter username>', r'Username>'])
                            if state == 0:
                                break
                            client.sendline('ACCESS' if state == 1 else 'TELNET_TEST')
                        else:
                            raise AssertionError('Telnet login did not complete')
                        for command in ('SHOW SERVER', 'SHOW INTERNET'):
                            client.sendline(command)
                            client.expect(r'(?m)^Local> ')
                            responses[command] = client.before
                        assert args.address in responses['SHOW INTERNET'], responses
                        if attempt == 0:
                            client.sendline('SET PRIVILEGED')
                            client.expect('Password>')
                            client.sendline('SYSTEM')
                            client.expect(r'(?m)^Local> ')
                            client.sendline('SET SERVER IDENTIFICATION "TELNET_SESSION_OK"')
                            client.expect(r'(?m)^Local> ')
                            client.sendline('SHOW SERVER')
                            client.expect(r'(?m)^Local> ')
                            assert 'TELNET_SESSION_OK' in client.before, client.before
                            client.sendline('SET NOPRIVILEGED')
                            client.expect(r'(?m)^Local> ')
                        else:
                            assert 'TELNET_SESSION_OK' in responses['SHOW SERVER'], responses
                        client.sendline('LOGOUT')
                        client.expect(pexpect.EOF)
                        report['sessions'].append(responses)
                    finally:
                        client.close(force=True)
        except Exception as error:
            report['passed'] = False
            report['error'] = str(error)
            (ROOT / 'analysis/telnet-verification.json').write_text(json.dumps(report, indent=2) + '\n')
            raise
        finally:
            session.stop()
    assert digest(seed) == before, 'Original settings changed'
    report['seed_unchanged'] = True
    report['passed'] = True
    (ROOT / 'analysis/telnet-verification.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
