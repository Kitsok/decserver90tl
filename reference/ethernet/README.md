# Ethernet investigation reference snapshots

Retrieved 2026-10-31. These are supporting references, not DECserver firmware.
Original copyright and license notices are retained. `inventory.json` records
the snapshot sizes and SHA-256 hashes; these are local identity records,
not independent publisher authentication.

| Local file | Origin |
|---|---|
| `Am7990-LANCE-Technical-Manual-1986.pdf` | https://bitsavers.trailing-edge.com/components/amd/Am7990/1986_Am7990_Local_Area_Network_Controller_LANCE_Technical_Manual.pdf |
| `Am7990-LANCE-Technical-Manual-1986.txt` | Local `pdftotext -layout` extraction of that PDF |
| `mame-am79c90.cpp` | https://raw.githubusercontent.com/mamedev/mame/master/src/devices/machine/am79c90.cpp |
| `simh-vax_xs.c` | https://raw.githubusercontent.com/simh/simh/master/VAX/vax_xs.c |

The main `www.bitsavers.org` host rejected the direct download; the listed
Bitsavers mirror supplied the PDF. Upstream source URLs refer to mutable
`master` branches; the saved files and hashes preserve what was inspected.
They are not dependencies or compiled components of this repository.

The source snapshots demonstrate existing LANCE models. They have not been
adapted, built or run against DECserver 90TL firmware.
