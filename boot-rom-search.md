# Boot ROM requirements and search results

Search date: 2026-10-31. No verified DECserver 90TL boot-ROM dump was found.
This is a search result, not evidence that no public dump exists.

## Does the simulator require the ROM?

A dump is required for executing the original ROM, but a direct-loaded
simulator can instead implement the services and handoff that the operating
image expects. The current synthetic handoff is incomplete. Confirmed
inherited dependencies include the initial exception vectors, runtime header
fields and fatal-report callback at header offset 0x1a2. ROM assistance for
misaligned data accesses is confirmed in the related 90M+ candidate, while
the exact 90TL implementation remains unavailable.

The latest CPU trace catches a word read at odd address 0x079dbed5, callback
PC 0x0788667c, from MOVEA.W -0x37(A6),A5 at 0x07886678. NXP's MC68332
manual states that CPU32 does not support misaligned transfers. MAME's
fscpu32 initializes the generic 16-bit interface, whose read_word accessor
rounds the address down, and its generic alignment checks exclude this CPU
class. Thus the previous experiment could silently read a neighboring word.
A diagnostic guard now stops that read rather than silently returning the
wrong word. This changes the current stopping point; the earlier record-22
bounds error may be downstream corruption. Its complete cause is not proven.

Manufacturer reference:
https://www.nxp.com/docs/en/user-guide/MC68332UM.pdf

## Candidate downloaded, NOT a 90TL dump

`reference/boot-rom-search/mnboot.sys`

- Source: https://www.glaver.org/DECserver/DNAS%20(DECserver%20Network%20Access%20Software)/V3.3/Firmware%20Images/mnboot.sys
- Size: 131584 bytes (128 KiB + 512 bytes).
- SHA-256: a9b96708a472fea90042554b75860489ae6005f95a1901ca43b9dcf4c34b2ca2
- Embedded identifiers include DS90M+ and DS90M+ (Lazer).
- The archive README identifies this as a 90M+ boot EEPROM image, distinct
  from operating firmware. The README also cautions that its model
  identification generally comes from image inspection, not hardware tests.
- It has not been executed or installed into the 90TL memory map. Compatibility,
  load mapping and usefulness of individual routines are unresolved.

README:
https://www.glaver.org/DECserver/DNAS%20(DECserver%20Network%20Access%20Software)/V3.3/Firmware%20Images/000-README.TXT

The original README and hash/provenance metadata accompany the download.
Firmware remains under its original copyright and terms.

## Sources checked

- Glaver 90TL directory: MNENG1.SYS, software kit and documentation, no
  boot-ROM file listed.
- Glaver DNAS directory listings across V2.0, V2.4, V3.3, V3.6, Others and
  Cabletron sections. Listings and errors are saved in
  `reference/boot-rom-search/glaver-listings.json` (18 directories total,
  including the classic 700 branch). Documentation/kit subtrees were not
  exhaustively traversed, and ISO contents were not downloaded for this search.
- Glaver classic 700 Boot EPROMs: genuine related-model dumps, including
  23-021EA V3.4-9, 23-028EA V4.0-0 and 23-052EA V6.3-0. They are NOT
  90TL ROMs; no claim of compatibility. Not downloaded in this search.
- 9track ROM catalogue: 100/200/250/300/700 entries, no 90TL/90M entry.
  https://www.9track.net/roms/
- PCjs assorted DEC ROM catalogue: no 90TL entry.
  https://www.pcjs.org/machines/dec/roms/assorted/
- Both user-supplied VCFed threads were fetched directly and inspected for
  ROM references/attachment links. The shared MNENG files are downloadable
  operating images. The visible collection-thread ROM offer concerns 700
  hardware, not 90TL. No 90TL ROM attachment found on fetched thread pages;
  later pagination was not exhaustively traversed.
- Bitsavers DEC binary index returned HTTP 403, including direct retrieval.
  Search-engine indexed results did not provide a 90TL ROM dump. This archive
  has not been exhaustively ruled out.
- Searches for 90TL/DSRVE boot-ROM, EPROM and ROM-dump variants, plus related
  90M images, found documentation/software loads but no verified 90TL dump.

Collection thread:
https://forum.vcfed.org/index.php?threads/large-collection-of-decserver-documentation-and-firmware.1253189/

Operating-image thread:
https://forum.vcfed.org/index.php?threads/looking-for-decserver-mneng2-sys-mneng3-sys-and-mneng4-sys-boot-files.62810/

## Next options

Inspect the 90M+ boot image statically for reusable handoff or alignment
routines, explicitly checking differences before using anything in the
90TL model. A dump from a physical 90TL remains the most reliable source for
its exact ROM services and factory configuration setup. Nobody has been
contacted and no forum message has been posted.

## Follow-up: candidate alignment service and controlled substitution

The candidate payload appears to start after a 512-byte wrapper with
vectors based at address zero. Its address-error vector points to 0x408.
That routine inspects an exception status word and uses byte-wise transfers,
then RTE or a continuation handler at 0x8c0. Disassembly is saved in
`analysis/mnboot-address-error.asm`. This is evidence for a ROM alignment
service in this related model, not proof of identical 90TL exception frames.

The simulator now offers `--rom-alignment-assist`. It substitutes unaligned
word/longword transfers at the CPU memory callbacks, without executing the
ROM handler or reproducing its cycles, exception frame or register side
effects. It is opt-in; the default stops at an odd-address transfer instead
of silently reading/writing a neighboring aligned address. Both reads and
writes require assistance: the earliest observed odd longword writes are
at 0x0799f21f/0x0799f223, before the later odd word reads.

With the assist, the ten-second isolated-store run finishes without error
0x543 and reaches later initialization. A subsequent longer run initializes
all four DUARTs and reaches scheduler idle, then reports error 0x298 when
its fixed-count idle loop receives no clock interrupt. These results revise
the earlier interpretation of the record-22 bounds error: incorrect aligned
accesses were a demonstrated cause; missing factory records may still matter
elsewhere. See the alignment-assist execution logs under `analysis/`.
