# Firmware first look, 2026-10-31

## Findings

| Image | Size, bytes | Identifying text | Shannon entropy, bits/byte | zlib size, bytes |
|---|---:|---|---:|---:|
| MNENG1 | 593408 | DECserver 90TL V1.1C, BL46-13 | 6.7448 | 284633 |
| MNENG2 | 891904 | Network Access SW V2.4 BL50 for DS90TL | 7.8047 | 849246 |
| MNENG3 | 1619456 | Network Access SW V2.4 BL50 for DS90TL | 6.8023 | 695941 |

MNENG1 and MNENG3 expose extensive readable text and Motorola 68k instructions. MNENG2 retains a readable initial region, but has much higher whole-image entropy and barely compresses with zlib. This supports the forum explanation that MNENG2 contains a compressed payload. The compression algorithm and compressed extent have not been identified; no decompression was attempted.

The `file` utility incorrectly labels MNENG1/MNENG3 as OpenPGP secret keys. That magic match is not a useful description of these firmware images.

## Address layout and startup

Coherent absolute references support an inferred mapping:

```
guest address = file offset + 0x07805000
```

This is a mapping inferred from code, not a decoded MOP container or proven physical RAM map. The loader header, actual transfer address, potential aliases, and initial registers remain unresolved. Do not blindly remove the first 512 bytes or start execution at the first apparent code.

All three images have 68k code at file offset `0x200`. It saves SP and VBR, copies 64 vector entries, fills another 192 entries with `0xffffffff`, and jumps to `0x0780535c`. Following that code reveals debugger/monitor-like logic; this is not established as the normal operating-software entry point.

MNENG3 has a NOP followed by an absolute JMP at file offset `0x2a00`. The JMP targets `0x078713f8`, corresponding to file offset `0x6c3f8`. The target is a convincing operating-software startup path:

- Saves incoming SP at `0x078051e6` and sets SP to `0x079dbfc0`.
- Reads the incoming VBR and copies 256 longword vectors to `0x0783b6ac`.
- Sets VBR to that new table and SR to `0x2600`.
- Calls low-level initialization at `0x079404a8`.
- Clears a substantial RAM region beginning at `0x0798f9ac`, servicing a watchdog during the loop.
- Continues through additional initialization and apparent execution-context setup.

MNENG1 has a JMP at file offset `0x2a00` to `0x07832b94`. Selected disassembly is saved for comparison. A boot-ROM handoff contract must be reconstructed before local loading is dependable: inherited stack, vectors, low memory data, and hardware state can matter.

## Processor/peripheral clue

At `0x07941656`, MNENG3 executes:

```asm
move.w #$55, $00fffa26.l
move.w #$aa, $00fffa26.l
rts
```

On a big-endian bus the low byte reaches `0x00fffa27`. This matches the MC68331/MC68332 SIM software-watchdog service register and required sequence. Startup also modifies words at `0x00fffa18` and `0x00fffa10`, consistent with the SIM Port F and Port E register locations.

Primary reference: [NXP MC68331 Technical Summary](https://www.nxp.com/docs/en/data-sheet/MC68331TS.pdf), SIM register map and software watchdog section. [MC68332 Technical Summary](https://www.nxp.com/docs/en/data-sheet/MC68332TS.pdf) describes the related SIM/watchdog.

These accesses are strong evidence for a Motorola CPU32/683xx platform, particularly a 68331/68332-like SIM. They do not distinguish the exact chip. MOVEC VBR/SFC/DFC instructions independently rule out a plain baseline 68000 execution model. Selected code also includes a long BSR encoding compatible with CPU32/68020-class decoding. The inspection script uses Capstone's 68020 mode as a decoding aid; this is not a claim that the physical processor is a 68020 or that an unmodified 68020 core fully emulates CPU32.

## Features exposed in strings

MNENG3 contains flash-presence, write-protection, invalid-image, unknown-device-ID, erase/program failure, and update-completion diagnostics. Examples at file offsets:

- `0x1461b`: flash not installed or unsupported.
- `0x5821f`: flash update complete.
- `0x5b2a9`: unknown flash device ID.
- `0x5b35d`: image too large for available flash.
- `0x13cb3a`: DS90TL version banner.

This establishes flash-related software paths in the image, not working flash hardware support on the 90TL board profile. Board-dependent dispatch and ROM support still need analysis. Other strings include LAT, Telnet, SLIP, SNMP and shared code/features for additional server models; string presence alone is not proof that a feature is enabled for 90TL.

## Implications and next work

Use MNENG1 as a known hardware reference and MNENG3 as the readable DNAS 2.4 target. The first look materially narrows CPU selection, but does not yet justify reducing the emulator estimate: Ethernet/UART hardware, interrupt routing, memory aliases and boot handoff remain unknown.

Next: decode the load header and transfer parameters; trace low-level initialization and peripheral accesses; identify the exact CPU and serial/Ethernet controllers; recover the ROM handoff data and decide whether a synthetic loader suffices. No emulator execution, network bridge, firmware patches or physical-device changes have been made.
