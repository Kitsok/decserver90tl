#!/usr/bin/env python3
"""Static first-look inventory; requires capstone for selected disassembly."""
import collections
import hashlib
import math
from pathlib import Path
import re
import zlib
from capstone import Cs, CS_ARCH_M68K, CS_MODE_BIG_ENDIAN, CS_MODE_M68K_020

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'analysis'
OUT.mkdir(exist_ok=True)
md = Cs(CS_ARCH_M68K, CS_MODE_BIG_ENDIAN | CS_MODE_M68K_020)
# Inferred from coherent absolute references, not a decoded loader header.
BIAS = 0x07805000
summary = []
for path in sorted((ROOT / 'firmware').glob('*.SYS')):
    data = path.read_bytes()
    counts = collections.Counter(data)
    entropy = -sum((n/len(data))*math.log2(n/len(data)) for n in counts.values())
    summary.append(dict(name=path.name, size=len(data),
                        sha256=hashlib.sha256(data).hexdigest(),
                        entropy=round(entropy, 4),
                        zlib_size=len(zlib.compress(data))))
    strings = [f'{m.start():08x} {m.group().decode("ascii")}'
               for m in re.finditer(rb'[ -~]{8,}', data)]
    (OUT / (path.stem + '.strings.txt')).write_text('\n'.join(strings)+'\n')
    ranges = [(0x200, 0x38), (0xa9a, 0x9e)]
    op = 0x2a00 + (2 if data[0x2a00:0x2a02] == b'\x4e\x71' else 0)
    if data[op:op+2] == b'\x4e\xf9':
        target = int.from_bytes(data[op+2:op+6], 'big')
        ranges.append((op, 6))
        if 0 <= target-BIAS < len(data):
            ranges.append((target-BIAS, 0xb0))
    if path.stem == 'MNENG3':
        ranges.extend((addr-BIAS, size) for addr, size in
                      [(0x079404a8, 0x4e), (0x07941656, 0x12), (0x07807a68, 0x28),
                       (0x079409e2, 0x1a), (0x07941e50, 0x44),
                       (0x07942318, 0x4c), (0x07942560, 0x2a),
                       (0x079425aa, 0x40), (0x0794458c, 0x116),
                       (0x07944690, 0x64), (0x079446f4, 0x2c),
                       (0x07944a48, 0x40), (0x07944b12, 0x66),
                       (0x07944c16, 0x94), (0x07945300, 0x26),
                       (0x079471a8, 0xb0)] )
        # Manually validated full-format PC-relative LEA at 0x07944590.
        table = 0x0786c2ec - BIAS
        pairs = ['# MNENG3 startup register writes (in order)',
                 '# table 0x0786c2ec, 69 pairs; absolute-short addresses sign-extended']
        for index in range(69):
            pos = table + index * 4
            value = int.from_bytes(data[pos:pos+2], 'big')
            addr = int.from_bytes(data[pos+2:pos+4], 'big', signed=True) & 0xffffffff
            pairs.append(f'{index:02d}  0x{addr:08x} <- 0x{value:04x}')
        (OUT / 'MNENG3.init-registers.txt').write_text('\n'.join(pairs)+'\n')
    lines = ['Selected code only. Addresses use inferred file bias 0x07805000.',
             '68020 decoder mode does not establish the exact installed CPU.',
             'These ranges do not establish the MOP transfer address.']
    for offset, size in ranges:
        lines.append(f'\nFile offset 0x{offset:x}:')
        for ins in md.disasm(data[offset:offset+size], offset+BIAS):
            lines.append(f'{ins.address:08x}  {ins.bytes.hex():24} {ins.mnemonic:10} {ins.op_str}'.rstrip())
    (OUT / (path.stem + '.selected.asm')).write_text('\n'.join(lines)+'\n')
import json
(OUT / 'inventory.json').write_text(json.dumps(summary, indent=2)+'\n')
print(json.dumps(summary, indent=2))
