# Proposed DECserver 90TL internal structure

2026-10-31. Static inference from the downloaded DNAS 2.4 MNENG3 image,
MNENG1 comparison, board photograph, DEC owner's manual, and Motorola
documentation. No firmware execution or hardware probing has been performed.

## Practical emulation boundary

The useful target is CPU-visible behavior, not an IC-by-IC electrical replica:

```text
                       local image loader
                              |
                     RAM + persistent config
                              |
                 CPU32 + interrupt/event scheduler
                    /          |           \
             Ethernet       SIM/QSM/TPU    four dual UARTs
             registers      register      = eight serial ports
             and DMA        behavior             |
                |                           modem adapters
             TAP/bridge                  bytes + control signals
```

Clock oscillators, Ethernet PHY/coax circuitry, RS-232 transceivers, individual
buffers, DRAM refresh, LEDs and PCB glue logic do not need independent models.
Their effects need representation only where guest-visible. Ethernet DMA,
interrupt acknowledgements, UART register side effects, and persistent settings
cannot simply be omitted.

The current working hypothesis is **an MC68332-like CPU32 microcontroller,
four 68681-style dual UART blocks, an external Ethernet controller, external
RAM/ROM/persistent storage, and board control registers**. Exact IC identity
is still unconfirmed. The schematic is a proposed software architecture, not
an established board schematic.

## Address conventions and a significant decoding limitation

References below use the inferred MNENG3 mapping:

```
linked address = file offset + 0x07805000
```

This is supported by coherent jumps and data references; the MOP header and
transfer parameters are not decoded. Addresses such as `0xfffffa26` are formed
by sign-extension of 16-bit absolute operands. Explicit long operands also
access `0x00fffa26`. If the board exposes a 24-bit bus, both reach the same
device. CPU32 pointer addresses above 24 bits also suggest aliasing must be
investigated: `0x07805000` would appear externally as `0x805000` under a simple
24-bit mask. Do not treat this masking policy as proven until the CPU/board
address decoding is confirmed.

Capstone's 68020 decoder sometimes prints invalid register names for full-format
PC-relative addressing. An example at `0x07944590` is bytes
`41 fb 01 70 ff f2 7d 5a`. Manually interpreting its suppressed-index,
long-base-displacement effective address gives a table at `0x0786c2ec`.
The table contents and consuming loop are coherent. Raw bytes and operands
must be checked before trusting automated whole-file disassembly. Tables and
padding must not be counted as executable instructions.

## CPU and integrated peripheral evidence

The low-level startup routine at `0x0794458c` writes **69 value/address pairs**
from that initialization table. Each pair is a 16-bit value followed by a
16-bit address, sign-extended by `MOVEA.W`, and written as a word.

Important decoded entries, with addresses normalized to 24 bits:

| Address | Initial value | Interpretation |
|---|---:|---|
| `0xfffa00` | `0x60cf` | SIM configuration |
| `0xfffa04` | `0x9b00` | Clock synthesis control |
| `0xfffa44` / `46` | `0x3a56` / `0x0155` | Chip-select pin assignment |
| `0xfffa48` through `76` | multiple pairs | Boot and external chip-select configuration |
| `0xfffa10`, `14`, `16` | `0`, `0x000d`, `0x00f2` | Port E data/direction/pin assignment |
| `0xfffa18`, `1c`, `1e` | `0`, `0x0037`, `0x0048` | Port F data/direction/pin assignment |
| `0xfffc00` | `0x4081` | QSM module configuration |
| `0xfffc08`, `0a` | `0x0030`, `0x202c` | SCI control |
| `0xfffc14`, `16` | `0x0008`, `0x0034` | QSPI control |
| `0xfffb04` | `0xfff0` | Internal RAM base configuration |
| `0xfffe00` | `0x00c3` | TPU module configuration |
| `0xfffe0c` | `0x9988` | TPU function selection for channels 15–12 |
| `0xfffe0e`, `10`, `12` | `0x8888` each | TPU function selection for channels 11–0 |
| `0xfffe14`, `16` | `0x0900`, `0` | TPU host sequence |
| `0xfffe18`, `1a` | `0xa3ff`, `0xffff` | TPU host service requests |
| `0xfffe1c`, `1e` | `0xf555`, `0xaaaa` | TPU channel priorities |

The table additionally initializes per-channel parameter words at `0xffff00`,
`0xffff10`, ... `0xfffff0`. Channels 0–11 initially receive `0x000b` at the
start of their parameter blocks; channels 12–15 receive other parameters.
This establishes use of the TPU host interface, not the exact TPU functions
or their mask-dependent microcode semantics.

Later routines explicitly use the same modules:

- `0x07941656`: writes `0x55`, then `0xaa`, as words at `0x00fffa26`;
  the low byte reaches the documented watchdog service register `0xfffa27`.
- `0x079446f4`: disables SIM periodic interrupts using `0xfffa22`/`24` and
  alters TPU channel priorities at `0xfffe1c`.
- `0x079445f8`: requests a TPU operation by setting `0x0c00` in host service
  register `0xfffffe18`, then waits for the TPU to clear those bits.
- `0x07944a5e`: reads TPU interrupt status at `0xfffffe20`.

These combined SIM, QSM, TPU and internal RAM addresses are considerably
stronger evidence for MC68332-like hardware than the watchdog sequence alone.
The earlier MC68331/68332 ambiguity is narrowed by the TPU evidence.

References: [MC68332 User's Manual](https://www.nxp.com/docs/en/user-guide/MC68332UM.pdf)
and [Technical Summary](https://www.nxp.com/docs/en/data-sheet/MC68332TS.pdf).

## Eight serial ports: four dual UART blocks

This is now a strong inference from **explicit device tables**, not merely
from the physical connector count.

At `0x0794253c`, four pairs associate RAM driver objects with descriptors:

| Driver object | Descriptor | Descriptor's hardware base |
|---|---|---|
| `0x079ac754` | `0x079424ec` | `0x00400000` |
| `0x079aeff4` | `0x07942500` | `0x00400020` |
| `0x079b1894` | `0x07942514` | `0x00400040` |
| `0x079b4134` | `0x07942528` | `0x00400060` |

The objects are spaced `0x28a0` bytes apart. Initialization at `0x07942560`
walks these four pairs and calls `0x07942318`, which copies the hardware
base and next-object link into the RAM object and initializes two channel
substructures. The descriptor flags are `0xfeff`, `0xfdff`, `0xfbff`,
`0xf7ff`, consistent with four distinct interrupt/status masks.

The disable/configuration routine `0x079425aa` treats each block as two
channels. Relative to the hardware base it writes:

- `+0x04` and `+0x14`: command-like values `0x90` for the two channels.
- `+0x08`: auxiliary-control-like value `0xe0`.
- `+0x0a`: interrupt-mask-like state.
- `+0x1a`: input/output configuration-related state.

The transmit service at `0x07944c64` selects byte output at `base+0x06`
or `base+0x16`, depending on which channel is ready. It checks bits 0
and 4 of a value obtained through `base+0x0a`, matching the layout expected
for paired transmit interrupt indications in a 68681-style DUART.

The register arrangement is a strong match to a **68681-family DUART with
each register spaced two bytes apart**. Exact vendor, variant, FIFO depth,
pin wiring, and logical-to-physical port ordering remain unverified.

The modem-input routine at `0x07945300` reads `0x0040001a` and advances
by `0x20` for four iterations. This is consistent with one shared input
port per dual UART. SIM GPIO routines at `0x07941e50` and `0x07941e72`
also clear/set selected bits through a port/bit mapping table; individual
DTR/DSR assignments must still be traced.

### TPU involvement

The serial interrupt paths use TPU channel interrupt status and mask bits,
then operate external serial registers. This suggests the TPU provides
interrupt sensing/aggregation or related timing services. It is **not
evidence that the eight terminal UARTs are implemented in TPU microcode**.

An optimized receive path at `0x07944b12` also accesses a compact group
relative to `0x00400000`, selecting channels with `base + 2 + 2*n` and
reading a data byte four bytes beyond that address. Its relationship to the
four normal DUART windows is unresolved. Possible explanations include
hardware aliases or a special access window. Do not implement only the
normal windows and assume this path will work automatically.

For emulation: implement byte queues and the register-visible status,
commands, masks, acknowledgement and interrupt behavior. Schedule byte
completion according to configured baud/framing. Convert modem events
to guest-visible pin changes. There is no need to synthesize RS-232
voltages or individual start/stop-bit edges unless firmware behavior later
shows it observes those edges.

## Ethernet: less established than the serial side

**Later investigation, 2026-10-31:** the uncertainty below is superseded by
[Ethernet controller identification](ethernet-controller.md). Both MNENG1
and MNENG3 implement a LANCE/Am7990-compatible interface at `0x00300000`
(RDP) and `0x00300002` (RAP). MNENG3 uses 32 RX and 8 TX descriptors,
24-bit DMA, CSR3 byte swapping and an apparent level-3 autovector. Exact
silicon identity and factory MAC storage remain unresolved. The paragraphs
below preserve the earlier investigation state.

An external Ethernet controller remains the working assumption. The exact
controller, register base, DMA descriptors, byte ordering and interrupt
vector are **not yet established**. The board photograph is insufficient
to assign the DC93 chip or another chip to this role confidently.

A routine at `0x079409e2` copies six consecutive bytes beginning at
`0x00200000` into a caller-supplied buffer while masking interrupts. This
is a plausible station-address ROM/readout routine, but the caller's use
must be confirmed before labelling it a MAC-address source. Reading the
same region also appears in interrupt-related code; a dual purpose or
board-specific acknowledgement effect remains possible.

Do not yet label `0x00200000` as the Ethernet controller. A shared driver
can obtain register addresses through tables or RAM pointers, so lack of
obvious absolute I/O operands is not proof a device is absent.

The eventual Ethernet model needs frame-level TX/RX, DMA or shared RAM,
ownership/status transitions, interrupts, reset, station address, and
multicast reception. TAP/bridge supplies Ethernet frames; the firmware
continues to implement LAT/Telnet and other network protocols itself.

## Flash and board controls

The flash-probe routine near `0x079471c6` sets bit 0 of the control word
at `0x00440000`, waits, writes `0x9090` at `0x00600000`, and reads words
at `0x00600000` and `0x00600002`. It tests manufacturer byte `0x89`
and includes an alternate unlock sequence using `0x00600aaa` and
`0x00600554`. Other routines clear the same control bit after programming.

This strongly identifies:

- `0x00600000`: a parallel flash candidate window.
- `0x00440000` bit 0: a flash-programming-enable/control candidate.
- Support for more than one flash command protocol.

This is code in a shared image and does **not** prove flash exists on the
physical 90TL or that its board profile enables this path. The flash window
size and erase geometry remain unresolved. It provides a promising route
to an emulated flash extension if the project requires genuine guest-visible
flash rather than only a simulator-side local loader.

`0x0040003a` is also probed during board identification: the routine clears
it, reads it, and tests bits 4 and 6. It lies within one serial block's
input/configuration area, so board straps may be visible through serial
GPIO. This is an inference requiring confirmation.

## RAM, persistence and boot

DEC's Owner's Manual distinguishes the volatile operational database from
the permanent database in NVRAM. Runtime bring-up now locates byte-addressed
configuration checksum/readback operations relative to `0x100c00`. The
write helper at `0x07940c00` sets QSM register `0xfffc14` bit 2, writes one
byte through A2, then clears bit 2. The delay helper at `0x07940c22` runs
DBRA with 0x960 iterations between operations. This is consistent with
write-enable gating for nonvolatile memory; EEPROM versus battery-backed
RAM/RTC remains unresolved. User also identifies a nonvolatile storage
component on the real board, with its technology still uncertain.

The simulator provisionally provides a file-backed 64 KiB window at
`0x100000`, initially erased to FF, without write-enable/timing enforcement.
This is an implementation approximation, not established chip capacity.
The firmware image itself is separate from persistent configuration.

MNENG3's startup sets SP to `0x079dbfc0`, copies the inherited vector table,
and initializes its own VBR. The mapping suggests a useful starting point
of 4 MB external RAM, based on the successful physical boot reports, but
the precise RAM boundaries and aliases still need reconstruction.

The code copies a table/code region to `0xfffff000`; subsequent optimized
serial/timing routines use internal RAM locations around `0xfffff000`,
`0xfffff020`, `0xfffff024`, `0xfffff02e` and `0xfffff030`. This is guest
RAM/code, not a collection of external MMIO registers. The initialization
table's RAM base register and the Motorola RAM module documentation are
consistent with an on-chip RAM mapping here.

A simulator-side local loader is still the simplest way to avoid network
boot. It must provide a valid inherited stack/vector table and any ROM
handoff records the image consumes. A real boot-ROM dump would make this
boundary much less speculative.

## Minimum models and confidence

| Block | Proposed implementation | Confidence |
|---|---|---|
| CPU | Existing CPU32 core; validate exception frames/control instructions | High for family; exact chip unresolved |
| External/internal RAM | Byte-addressable backing with validated aliases | High necessity; boundaries incomplete |
| SIM | Register state, watchdog servicing, GPIO, periodic interrupt, chip selects as needed | High |
| QSM | SCI/QSPI register behavior actually reached | High presence; workload role incomplete |
| TPU | Host requests, parameter RAM, completion and interrupt semantics | High presence; function details incomplete |
| Serial | Four dual UARTs at `0x400000 + 0x20*n`; optimized access path separately resolved | High topology; exact variant unresolved |
| Ethernet | LANCE-compatible RDP/RAP, CSR0–3 and DMA model connected to TAP | High interface confidence; exact silicon unresolved (see later report) |
| Board controls | Only observed bits/straps and side effects | Medium |
| Configuration storage | File-backed NVRAM accessed through recovered interface | Documented persistence; interface unknown |
| Local firmware | Host-side loader initially; optional parallel flash model later | Design choice |

This is a tractable behavioral model. Full TPU microengine emulation and
IC-by-IC board reconstruction should not be assumed necessary. However,
simply returning constants from all unfamiliar registers will hang the
observed host-request polling loops or suppress required interrupts.

## Next discriminating checks

1. Trace the six-byte read routine's callers and Ethernet driver's device
   table to identify MAC storage, controller registers and DMA layout.
2. Recover UART register initialization and mapping tables, including the
   compact receive window and DTR/DSR pin assignments.
3. Decode TPU function selection using the actual silicon mask or observed
   request/completion behavior; initially model only those services.
4. Decode loader/header handoff and RAM/chip-select configuration, and trace
   permanent-database writes to establish the NVRAM interface.

## Emulator selection research

Upstream source inspected 2026-10-31:

- **MAME:** explicit `M68K_CPU_TYPE_FSCPU32` and `fscpu32_device` initialization.
  Strongest confirmed CPU-family match among the candidates inspected.
  Its MC68340 device provides related integration examples, not a substitute
  for the 68332 peripheral map. Implementing a MAME machine avoids extracting
  its CPU from the surrounding C++ framework, but is a product/design choice.
  [CPU32 source](https://github.com/mamedev/mame/blob/master/src/devices/cpu/m68000/fscpu32.cpp),
  [core definitions](https://github.com/mamedev/mame/blob/master/src/devices/cpu/m68000/m68kmusashi.h).
- **Standalone Musashi:** embeddable C CPU engine with memory callbacks,
  interrupt support and register access. Its published CPU enum does not
  include CPU32. A 68020 configuration is a prototype approximation, not
  validated CPU32 compatibility.
  [Header](https://github.com/kstenerud/Musashi/blob/master/m68k.h).
- **SIMH:** AltairZ80 embeds Musashi and its inspected enum also lacks CPU32;
  the surrounding machine targets CP/M-68K. The SAGE subtree has another 68k
  implementation, not a demonstrated 90TL model. SIMH's TMXR infrastructure
  supports raw streams, serial timing, BREAK and modem-control bits and may
  be useful for a final server simulator. Combining it with a CPU32-capable
  core requires integration work.
  [Core](https://github.com/simh/simh/blob/master/AltairZ80/m68k/m68k.h),
  [integration](https://github.com/simh/simh/blob/master/AltairZ80/m68ksim.c),
  [SAGE core](https://github.com/simh/simh/blob/master/SAGE/m68k_cpu.c),
  [TMXR](https://github.com/simh/simh/blob/master/sim_tmxr.h).
- **QEMU:** general 68k support is present, but no CPU32 model was found in
  the inspected CPU definitions. Not currently the leading target for this
  board. [CPU definitions](https://github.com/qemu/qemu/blob/master/target/m68k/cpu.c).

No candidate has yet been built or run against these images. CPU-family
support does not establish exception-frame fidelity or board compatibility.

Source context: local `docs/DECserver-90TL-Owners-Manual.txt` in the parent
workspace; user-supplied `reference/DS90TL-Top.jpg`; firmware provenance and
hashes in this repository's README and analysis inventory. No firmware
changes, active network tests, physical resets or deployment were performed.

## RTC hypothesis and configuration-store capacity

The user suggested a DS1287-style battery-backed RTC/RAM module. The
DS12887, documented as a DS1287 replacement, exposes 128 total locations
including clock/control registers and 114 bytes of RAM. That capacity cannot
by itself explain the several-kilobyte linear configuration-store operations
seen here. A separate RTC remains possible; no RTC register interface has
been established. The simulator must not identify its provisional 64 KiB
store as a DS1287.

Reference: https://www.analog.com/en/products/ds12887.html

Runtime handoff also needs a valid port mask at image offset 0x1e. With the
on-disk word 0x1c00, startup selects port 12 and the routine at 0x079423ac
asserts because only indices 0..7 are accepted. The synthetic handoff writes
0x00ff in guest RAM. Board metadata defaults are selected by bits 19..21 of
the longword at offset 0x16; initialization at 0x07940696 tests those flags
and copies three default records. The experimental handoff requests those
defaults because boot-ROM metadata validation has not been reproduced.

The firmware fatal-report path at `0x07948438` stores code at `0x07805036`,
parameter at `0x07805032`, return address at `0x07805028`, SR at `0x07805030`
and SP at `0x0780502c`, then jumps via inherited pointer `0x078051a2`.
The simulator supplies a stopping diagnostic callback for this ROM service.
The current reproducible error is code 0x543, reached from the storage bounds
checker at `0x07872602`. Both fresh-FF and zero-filled storage reproduce an
out-of-range record-22 offset 0x0e00 against declared size 0x0c00. Do not
expand that record or bypass its check without resolving the mismatch.
