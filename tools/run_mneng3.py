#!/usr/bin/env python3
"""Run MNENG3/4 MiB with timed diagnostics or eight interactive serial PTYs."""
import argparse
import hashlib
import os
from pathlib import Path
import subprocess
import tempfile

from tap_network import validate_tap

from build_mame import ROOT
from run_output import ConsoleOutput, stream_process


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--interactive', action='store_true', help='Expose eight PTYs and run until Ctrl-C')
    parser.add_argument('--serial-control', type=Path, help='Interactive modem control socket (default: run/serial-control.sock)')
    parser.add_argument('--serialsim', action='append', default=[], metavar='PORT=DEVICE',
                        help='Use an existing serialsim pipe TTY for this port; repeatable, independent of --interactive')
    parser.add_argument('--ethernet-pcap', type=Path, help='Capture TAP packets (default: logfile with .pcap suffix)')
    parser.add_argument('--tap', help='Attach LANCE to this existing, bridged Linux TAP (default: offline)')
    parser.add_argument('--seconds', type=int, default=None)
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Show the full live trace on console (logfile is always complete)')
    parser.add_argument('--log-file', type=Path,
                        help='Raw trace path (default: run/bringup.log)')
    parser.add_argument('--uart-probe-port', type=int, default=0, choices=range(9),
                        help='Diagnostic FIFO input on port 1..8 (0 disables)')
    parser.add_argument('--uart-probe-hex', default='0d0d0d',
                        help='Up to 128 diagnostic bytes in hex, one per second (default: three CRs)')
    parser.add_argument('--uart-probe-at', type=int, default=20, choices=range(1,56),
                        help='Simulated second of first diagnostic FIFO injection')
    parser.add_argument('--ram-wait-cycles', type=int, default=0, choices=range(17),
                        help='Experimental extra CPU cycles per 16-bit external RAM transfer')
    parser.add_argument('--rom-alignment-assist', action='store_true',
                        help='Experimentally substitute unaligned data transfers for ROM exception handling')
    parser.add_argument('--nvram-directory', type=Path,
                        help='Separate persistent store for an isolated boot experiment')
    args = parser.parse_args()
    serialsim = {}
    for assignment in args.serialsim:
        port, separator, path = assignment.partition('=')
        if not separator or port not in map(str, range(1, 9)) or not path or int(port) in serialsim:
            parser.error('--serialsim requires a distinct PORT=DEVICE with port 1..8')
        serialsim[int(port)] = str(Path(path).resolve())
    if len(set(serialsim.values())) != len(serialsim):
        parser.error('Each serialsim port must use a distinct device')
    if args.ethernet_pcap and not args.tap:
        parser.error('--ethernet-pcap requires --tap')
    if args.tap:
        try:
            bridge = validate_tap(args.tap)
        except (OSError, ValueError) as error:
            parser.error(str(error))
    if args.seconds is None:
        args.seconds = 0 if args.interactive or serialsim else 1
    try:
        probe_data = bytes.fromhex(args.uart_probe_hex)
    except ValueError:
        parser.error('--uart-probe-hex must contain hexadecimal byte pairs')
    if not 1 <= len(probe_data) <= 128:
        parser.error('--uart-probe-hex must encode between 1 and 128 bytes')
    if not ((args.interactive or serialsim) and args.seconds == 0) and not 1 <= args.seconds <= 60:
        raise SystemExit('--seconds must be between 1 and 60')
    firmware = ROOT/'firmware/MNENG3.SYS'
    digest = hashlib.sha256(firmware.read_bytes()).hexdigest()
    if digest != 'a3764087d79df64eb7124056824652cf23b558fcae2029f887e4a37a3db49ad3':
        raise SystemExit('Unexpected MNENG3 image; this handoff is image-specific')
    run = ROOT/'run'
    roms = run/'roms/ds90tl'
    roms.mkdir(parents=True, exist_ok=True)
    image_link = roms/'mneng3.sys'
    if not image_link.exists():
        image_link.symlink_to(firmware)
    env = os.environ.copy()
    for port in range(1, 9):
        env.pop(f'DS90_SERIALSIM_{port}', None)
    for port, path in serialsim.items():
        env[f'DS90_SERIALSIM_{port}'] = path
    env['DS90_ROM_ALIGNMENT_ASSIST'] = '1' if args.rom_alignment_assist else '0'
    env['DS90_RAM_WAIT_CYCLES'] = str(args.ram_wait_cycles)
    env['DS90_UART_PROBE_PORT'] = str(args.uart_probe_port)
    env['DS90_UART_PROBE_AT'] = str(args.uart_probe_at)
    env['DS90_UART_PROBE_HEX'] = probe_data.hex()
    env['DS90_SERIAL_CONTROL'] = str((args.serial_control or run/'serial-control.sock').resolve())
    env['DS90_SERIAL_PTY'] = '1' if args.interactive else '0'
    env.pop('DS90_TAP_NAME', None)
    env.pop('DS90_TAP_PCAP', None)
    if args.tap:
        env['DS90_TAP_NAME'] = args.tap
    env.update(SDL_VIDEODRIVER='dummy', SDL_AUDIODRIVER='dummy')
    command = [str(ROOT/'build/mame-ds90tl'), 'ds90tl', '-noreadconfig',
               '-rompath', str(run/'roms'), '-bench', str(args.seconds),
               '-skip_gameinfo', '-cfg_directory', str(run/'cfg'),
               '-networkprovider', 'taptun' if args.tap else 'none',
               '-nvram_directory', str((args.nvram_directory or run/'nvram').resolve())]
    if args.interactive or args.tap or serialsim:
        index = command.index('-bench')
        command[index:index + 2] = ['-video', 'none', '-sound', 'none', '-throttle', '-seconds_to_run', str(args.seconds)]
    log_path = (args.log_file or run/'bringup.log').resolve()
    log_path.parent.mkdir(parents=True, exist_ok=True)
    if args.tap:
        pcap_path = (args.ethernet_pcap or log_path.with_suffix('.pcap')).resolve()
        if pcap_path == log_path:
            parser.error('Ethernet capture and text log paths must differ')
        pcap_path.parent.mkdir(parents=True, exist_ok=True)
        env['DS90_TAP_PCAP'] = str(pcap_path)
    console = ConsoleOutput('unlimited' if not args.seconds else args.seconds, args.verbose)
    console.say(f'Starting MNENG3 / 4 MiB; {"unlimited" if not args.seconds else str(args.seconds) + " simulated seconds"}; Ctrl-C to stop')
    for port, path in serialsim.items():
        console.say(f'Serial port {port}: serialsim {path} (DTR/DSR through TTY ioctls)')
    console.say(f'Configuration store: {(args.nvram_directory or run/"nvram").resolve()}')
    console.say(f'Full live trace: {log_path}')
    console.say(f'Ethernet: TAP {args.tap}, bridge {bridge}; capture: {pcap_path}' if args.tap else 'Ethernet: offline')
    try:
        # Host MAME cfg must not silently restore a previous network interface.
        # Guest settings remain in the selected persistent NVRAM directory.
        with tempfile.TemporaryDirectory(prefix='cfg-', dir=run) as cfg:
            command[command.index('-cfg_directory') + 1] = cfg
            status = stream_process(command, run, env, log_path, console, timeout=None if not args.seconds else 120)
    except subprocess.TimeoutExpired:
        raise SystemExit(f'Host timeout; simulator stopped. Inspect {log_path}')
    except KeyboardInterrupt:
        raise SystemExit(f'Interrupted; simulator stopped. Log: {log_path}')
    if status == 0 and args.seconds:
        console.say(f'Timed run completed ({args.seconds} simulated seconds); simulator stopped')
    console.say(f'Firmware unchanged: {hashlib.sha256(firmware.read_bytes()).hexdigest() == digest}')
    console.say(f'MAME exit status: {status}; log: {log_path}')
    raise SystemExit(status)


if __name__ == '__main__':
    main()
