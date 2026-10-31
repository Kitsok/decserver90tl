#!/usr/bin/env python3
"""Run an isolated AM7990 register/DMA/interrupt component test, without a TAP."""
import json
import os
from pathlib import Path
import subprocess
import tempfile

from build_mame import ROOT


def main():
    log_path = ROOT / 'run/ethernet-loopback.log'
    env = os.environ.copy()
    env.update(DS90_ROM_ALIGNMENT_ASSIST='1', DS90_RAM_WAIT_CYCLES='1',
               DS90_SERIAL_PTY='0', SDL_VIDEODRIVER='dummy', SDL_AUDIODRIVER='dummy')
    env.pop('DS90_TAP_NAME', None)
    env.pop('DS90_TAP_PCAP', None)
    with tempfile.TemporaryDirectory(prefix='ds90-ethernet-') as temporary:
        work = Path(temporary)
        command = [str(ROOT / 'build/mame-ds90tl'), 'ds90tl', '-noreadconfig',
                   '-rompath', str(ROOT / 'run/roms'), '-video', 'none', '-sound', 'none',
                   '-seconds_to_run', '3', '-skip_gameinfo', '-networkprovider', 'none',
                   '-cfg_directory', str(work / 'cfg'), '-nvram_directory', str(work / 'nvram'),
                   '-autoboot_delay', '1', '-autoboot_script', str(ROOT / 'tests/ethernet-loopback.lua')]
        with log_path.open('w') as log:
            result = subprocess.run(command, cwd=ROOT / 'run', env=env, stdout=log,
                                    stderr=subprocess.STDOUT, timeout=30)
    output = log_path.read_text()
    assert result.returncode == 0 and 'DS90 ETHERNET-LOOPBACK-PASS' in output, output[-4000:]
    assert 'DS90 LANCE-IRQ asserted=1' in output and 'DS90 LANCE-IRQ asserted=0' in output
    report = dict(kind='isolated AM7990 register component test; no host network',
                  initialization=True, csr3=6, dma_address_bits=24, transmit_bytes=32,
                  receive_bytes_including_fcs=36, payload_byte_order=True,
                  descriptor_ownership=True, receive_transmit_interrupts=True,
                  interrupt_acknowledgement=True)
    text = json.dumps(report, indent=2) + '\n'
    (ROOT / 'analysis/ethernet-loopback-verification.json').write_text(text)
    print(text, end='')


if __name__ == '__main__':
    main()
