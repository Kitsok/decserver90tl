#!/usr/bin/env python3
"""Run MNENG3/4 MiB with timed diagnostics or eight interactive serial PTYs."""
import argparse
import hashlib
import os
from pathlib import Path
import subprocess

from build_mame import ROOT
from run_output import ConsoleOutput, stream_process


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--interactive', action='store_true', help='Expose eight PTYs and run until Ctrl-C')
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
    if args.seconds is None:
        args.seconds = 0 if args.interactive else 1
    try:
        probe_data = bytes.fromhex(args.uart_probe_hex)
    except ValueError:
        parser.error('--uart-probe-hex must contain hexadecimal byte pairs')
    if not 1 <= len(probe_data) <= 128:
        parser.error('--uart-probe-hex must encode between 1 and 128 bytes')
    if not (args.interactive and args.seconds == 0) and not 1 <= args.seconds <= 60:
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
    env['DS90_ROM_ALIGNMENT_ASSIST'] = '1' if args.rom_alignment_assist else '0'
    env['DS90_RAM_WAIT_CYCLES'] = str(args.ram_wait_cycles)
    env['DS90_UART_PROBE_PORT'] = str(args.uart_probe_port)
    env['DS90_UART_PROBE_AT'] = str(args.uart_probe_at)
    env['DS90_UART_PROBE_HEX'] = probe_data.hex()
    env['DS90_SERIAL_PTY'] = '1' if args.interactive else '0'
    env.update(SDL_VIDEODRIVER='dummy', SDL_AUDIODRIVER='dummy')
    command = [str(ROOT/'build/mame-ds90tl'), 'ds90tl', '-noreadconfig',
               '-rompath', str(run/'roms'), '-bench', str(args.seconds),
               '-skip_gameinfo', '-cfg_directory', str(run/'cfg'),
               '-nvram_directory', str((args.nvram_directory or run/'nvram').resolve())]
    if args.interactive:
        index = command.index('-bench')
        command[index:index + 2] = ['-video', 'none', '-sound', 'none', '-throttle', '-seconds_to_run', str(args.seconds)]
    log_path = (args.log_file or run/'bringup.log').resolve()
    log_path.parent.mkdir(parents=True, exist_ok=True)
    console = ConsoleOutput('unlimited' if not args.seconds else args.seconds, args.verbose)
    console.say('Starting MNENG3 / 4 MiB; eight interactive PTYs; Ctrl-C to stop' if args.interactive else f'Starting MNENG3 / 4 MiB; limit {args.seconds} simulated seconds, 120 seconds host time')
    console.say(f'Configuration store: {(args.nvram_directory or run/"nvram").resolve()}')
    console.say(f'Full live trace: {log_path}')
    try:
        status = stream_process(command, run, env, log_path, console, timeout=None if args.interactive else 120)
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
