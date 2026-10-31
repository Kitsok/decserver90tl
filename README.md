# DECserver 90TL emulator investigation

Static investigation started 2026-10-31. No firmware has been executed or loaded onto physical hardware.

## Contents

- `firmware/`: original downloaded images, unchanged.
- `analysis/`: hashes, statistical inventory, printable strings (with file offsets), and selected disassembly.
- `tools/inspect_firmware.py`: reproducible inspection script; needs Python 3 and Capstone (`capstone` was already available in the environment).
- `reference/DS90TL-Top.jpg`: user-supplied board photograph.
- [First-look findings](first-look.md).

Run from any working directory:

```sh
python3 /home/kostik/work/decnet/decserver90tl/tools/inspect_firmware.py
```

## Firmware provenance

Retrieved 2026-10-31 from Terri Kennedy's DECserver archive. Local filenames normalized to uppercase for consistency; bytes retained unchanged.

| Local file | Source |
|---|---|
| `firmware/MNENG1.SYS` | https://www.glaver.org/DECserver/Pre-DNAS%20DECserver%20Models%20and%20Firmware/DECserver%2090TL/MNENG1.SYS |
| `firmware/MNENG2.SYS` | https://www.glaver.org/DECserver/DNAS%20(DECserver%20Network%20Access%20Software)/V2.4/Firmware%20Images/mneng2.sys |
| `firmware/MNENG3.SYS` | https://www.glaver.org/DECserver/DNAS%20(DECserver%20Network%20Access%20Software)/V2.4/Firmware%20Images/mneng3.sys |

Sizes and SHA-256 values are in `analysis/inventory.json`. Download hashes establish local identity, not independent authentication against vendor checksums. Firmware remains subject to its original copyright and terms.
