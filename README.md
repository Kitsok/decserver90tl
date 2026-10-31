# DECserver 90TL emulator investigation

Investigation started 2026-10-31. Original MNENG3 reaches `Local>` in an
experimental CPU32 simulator with 4 MiB RAM, using diagnostic FIFO input and
provisional ROM/timing substitutions. External serial and network backends
are not yet attached. Server-parameter defaults are reported during login.
No firmware has been loaded onto physical hardware.

## Contents

- `firmware/`: original downloaded images, unchanged.
- `analysis/`: hashes, statistical inventory, printable strings (with file offsets), and selected disassembly.
- `tools/inspect_firmware.py`: reproducible inspection script; needs Python 3 and Capstone (`capstone` was already available in the environment).
- `reference/DS90TL-Top.jpg`: user-supplied board photograph.
- [First-look findings](first-look.md).
- [Proposed internal structure and register-level evidence](internal-structure.md).
- [Ethernet controller identification and DMA interface](ethernet-controller.md).
- [Firmware organization and runtime map](firmware-organization.md).
- [Simulator implementation concept](simulator-concept.md).
- [MAC-window access findings](mac-window.md).
- [Boot-ROM requirements and search results](boot-rom-search.md).
- [Build instructions](BUILD.md).
- [Implementation status](implementation-status.md).

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

Interactive serial: run `./run.sh --interactive` to expose all eight ports as
local PTYs. Connect a terminal to the printed path, e.g.
`screen /dev/pts/7 9600`. See [BUILD.md](BUILD.md#interactive-serial-ports)
for startup, login and transport limitations.

DTR/DSR modem signaling and firmware XON/XOFF flow control are now supported.
Use `python3 tools/serial_control.py get all` to inspect lines, or
`python3 tools/serial_control.py set 1 dsr 0` to lower port 1 DSR.
See [modem-lines.md](modem-lines.md) for the host API and hardware evidence.

Ethernet: `./run.sh --interactive --tap ds90tap` uses the existing LANCE
model and a prepared, user-owned TAP on a bridge. See [network.md](network.md)
for lab setup, guest IP commands, packet captures and verified ARP/ping/Telnet
negotiation. Without `--tap`, networking stays offline.

Configuration command semantics, NVRAM file paths, host save timing and the
corrected startup handoff are documented in
[settings-storage.md](settings-storage.md).
