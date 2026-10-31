#!/usr/bin/env python3
"""Reproduce selected static evidence for the 90TL LANCE-compatible interface.

No firmware is executed. Addresses are linked addresses inferred in first-look.md.
Requires the already-used Python capstone package.
"""
import hashlib
import json
from pathlib import Path

from capstone import Cs, CS_ARCH_M68K, CS_MODE_BIG_ENDIAN, CS_MODE_M68K_020

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'analysis'
BIAS = 0x07805000
EXPECTED = {
    'MNENG1': 'd4f5b755514cde7bb4840f27e35e3ea6a129bf1f8266f587aae3e708023e2226',
    'MNENG3': 'a3764087d79df64eb7124056824652cf23b558fcae2029f887e4a37a3db49ad3',
}
RANGES = {
    'MNENG1': [('LANCE initialize/start', 0x07835cf0, 0x62)],
    'MNENG3': [
        ('Operating software initializes network interface', 0x078740fa, 0x3e),
        ('Stop controller, prepare station address and RX ring', 0x07874144, 0xc0),
        ('TX ring and ring clearing', 0x07874204, 0x40),
        ('Initial receive buffer population', 0x07874352, 0x2c),
        ('Stop controller', 0x078744c8, 0x22),
        ('LANCE initialize/start', 0x078744f6, 0x6e),
        ('Return receive buffer ownership', 0x078745a6, 0x3e),
        ('Transmit descriptor and demand', 0x07874bd0, 0x5e),
        ('Interrupt setup, immediate and deferred handlers', 0x07874c86, 0x92),
        ('CSR0 status processing', 0x07874d18, 0x104),
        ('Receive descriptor and DMA address processing', 0x07874e1c, 0x3c),
        ('Multicast CRC hash and logical address filter', 0x07874a02, 0x86),
        ('Six-byte board identity read; MAC role still tentative', 0x079409e2, 0x1a),
    ],
}

md = Cs(CS_ARCH_M68K, CS_MODE_BIG_ENDIAN | CS_MODE_M68K_020)
for name, ranges in RANGES.items():
    data = (ROOT / 'firmware' / (name + '.SYS')).read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if digest != EXPECTED[name]:
        raise SystemExit(f'{name}: unexpected firmware hash; fixed offsets unsafe')
    lines = [f'{name}: SHA-256 {digest}',
             'Static disassembly, Capstone 68020 mode; not proof of exact CPU.',
             'Register bit-operation suffixes/full-format EA text may be misleading.',
             'Raw bytes are authoritative; see ethernet-controller.md for interpretation.']
    for title, address, length in ranges:
        offset = address - BIAS
        lines.append(f'\n# {title}: linked 0x{address:08x}, file 0x{offset:x}')
        for ins in md.disasm(data[offset:offset+length], address):
            lines.append(f'{ins.address:08x}  {ins.bytes.hex():28} {ins.mnemonic:10} {ins.op_str}'.rstrip())
    (OUT / f'{name}.ethernet.asm').write_text('\n'.join(lines)+'\n')

summary = {
    'scope': 'Static inference; no firmware execution or controller emulation',
    'controller_interface': 'AMD Am7990 LANCE compatible; exact silicon unconfirmed',
    'rdp': '0x00300000', 'rap': '0x00300002',
    'mneng3_init_block_cpu': '0x07873e04',
    'mneng3_init_block_dma24': '0x873e04',
    'mneng1_init_block_cpu': '0x07835880',
    'csr3': '0x0006 = BSWP | ACON',
    'mneng3_rx_ring': {'cpu': '0x0799ec08', 'dma24': '0x99ec08',
                       'entries': 32, 'entry_bytes': 8},
    'mneng3_tx_ring': {'cpu': '0x0799ed08', 'dma24': '0x99ed08',
                       'entries': 8, 'entry_bytes': 8},
    'mneng3_rx_buffer_capacity': 1518,
    'mneng3_irq': {'vector_table_offset': '0x6c', 'vector_number': 27,
                   'inference': 'level-3 autovector', 'handler': '0x07874cd0'},
    'unresolved': ['Exact controller vendor/revision', 'Board-level interrupt wiring',
                   'Factory MAC readout source', 'Dynamic filtering and all error paths',
                   'Boot ROM Ethernet self-test behavior'],
}
(OUT / 'ethernet-summary.json').write_text(json.dumps(summary, indent=2)+'\n')
print(json.dumps(summary, indent=2))
