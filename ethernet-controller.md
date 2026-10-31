# DECserver 90TL Ethernet controller investigation

2026-10-31. Local-file and online reference searches were performed before
tracing the firmware. **The downloaded MNENG1 and MNENG3 images both use an
AMD Am7990 LANCE-compatible controller interface at `0x00300000`.** This is
strong static identification of the programming interface. The chip's exact
manufacturer, physical part number and revision are not established.

No firmware execution, device access or network traffic was used in this work.

## 1. Documentation and board evidence first

Searched the parent workspace's DECserver 90TL owner's manual, collected
90TL reports and evidence filenames, existing firmware strings, and the
user-supplied board photograph. The owner's manual establishes ThinWire
Ethernet, DEChub backplane connectivity and network loopback self-testing;
it does not identify the MAC controller or its registers. The available
firmware strings do not expose a useful LANCE/SONIC/8390 part name.

Online searches included DECserver 90TL/90M with Ethernet-controller,
LANCE, Am7990, SONIC, DP8390 and DC93 terms. No direct vendor document naming
the 90TL's controller was found. An older DECserver 300 technical description
discusses a LANCE driver, but a different model is not proof for the 90TL.

On the local board photograph, the small DIP next to the coax assembly
appears to read **DP8392CN-2**. Treat that as a tentative visual reading at
this resolution. A coax transceiver is not the Ethernet MAC/DMA controller;
that marking cannot establish that the board uses a DP8390 controller.
Other controller markings are not sufficiently legible. The DEC DC93 chip
has not been assigned a function.

Primary evidence used after the firmware fingerprint was found:

- [AMD Am7990 LANCE Technical Manual, 1986](https://www.bitsavers.org/components/amd/Am7990/1986_Am7990_Local_Area_Network_Controller_LANCE_Technical_Manual.pdf):
  address/data ports, CSR0–CSR3, initialization block, rings, byte ordering.
  A local PDF and extracted text are in `reference/ethernet/`.
- [MAME Am7990/Am79C90 model](https://github.com/mamedev/mame/blob/master/src/devices/machine/am79c90.cpp).
- [SIMH VAX LANCE model](https://github.com/simh/simh/blob/master/VAX/vax_xs.c).

See `reference/ethernet/README.md` for download sources and hashes. Search
results alone were not used to identify the 90TL chip.

## 2. Register-level fingerprint

Linked addresses below use the established working mapping:

```
linked CPU address = firmware file offset + 0x07805000
```

The external Ethernet interface is:

| CPU address | Width | Role |
|---|---|---|
| `0x00300000` | 16 bits | Register Data Port (RDP): selected CSR data |
| `0x00300002` | 16 bits | Register Address Port (RAP): select CSR0–CSR3 |

### MNENG3 initialization, linked `0x078744f6`, file `0x6f4f6`

The routine performs this sequence:

1. Load `A0 = 0x00300000`.
2. Write `1` to RAP, then low word of `0x07873e04` to RDP: CSR1,
   the initialization block's low address.
3. Write `2` to RAP, then the swapped high word to RDP: CSR2,
   whose meaningful address portion is the low eight bits.
4. Write `3` to RAP, then `6` to RDP: **CSR3 = BSWP | ACON**.
5. Select CSR0 and write **`0x0041 = INEA | INIT`**.
6. Poll bit 8, **IDON**, in CSR0. The observed loop has a bounded
   delay before checking and a fatal-error branch if initialization fails.
7. Write **`0x0042 = INEA | STRT`** to CSR0.

The stop routine at `0x078744c8` selects CSR0 and writes **`0x0004 = STOP`**.
The transmit path sets **`0x0008 = TDMD`**, preserving the interrupt-enable
bit. Error processing tests CSR0 bits 9–15 at the positions specified by AMD.

The combined register selection, values and status bits identify classic
LANCE programming much more strongly than any single constant. This is not
an NE2000/DP8390-style paged register/remote-DMA interface or a SONIC-style
register interface. A compatible implementation could still be used instead
of an AMD-branded physical chip.

### Independent MNENG1 confirmation

MNENG1's routine at linked `0x07835cf0`, file `0x30cf0`, accesses the same
`0x00300000`/`+2` ports, selects CSR1/2/3, supplies initialization address
`0x07835880`, and writes CSR3 = 6. It then issues INIT, polls IDON,
clears IDON with `0x0100`, starts with `0x0002`, and enables interrupts
with `0x0040`.

MNENG1 is the same firmware family recorded running on the physical 90TL.
This confirmation avoids relying only on a possible unused shared-driver
path in the later DNAS image. The downloaded and installed image bytes have
not been compared directly; version identity is the available baseline.

## 3. Initialization block, DMA and ring layout

The AMD initialization block is **24 bytes**:

| Offset | Size | Purpose |
|---|---:|---|
| `+0x00` | 2 | Mode |
| `+0x02` | 6 | Physical station address |
| `+0x08` | 8 | Logical multicast address filter |
| `+0x10` | 4 | RX ring pointer and ring-size exponent |
| `+0x14` | 4 | TX ring pointer and ring-size exponent |

In MNENG3 the block is at linked CPU address **`0x07873e04`**. Its ring
pointer fields initially contain size flags `0xa000` and `0x6000`; startup
fills the addresses and sets those flags in the high pointer words.

At `0x078741c2` onward the firmware builds:

| Ring | Linked CPU base | 24-bit DMA base | Entries | Bytes per entry |
|---|---|---|---:|---:|
| RX | `0x0799ec08` | `0x99ec08` | **32** (`2^5`) | **8** |
| TX | `0x0799ed08` | `0x99ed08` | **8** (`2^3`) | **8** |

These are the initial addresses in this particular image, not fixed
architectural constants an emulator should hard-code. The controller must
read the block and respect the addresses the guest programs.

Classic descriptors contain four 16-bit words:

1. Buffer address bits 15–0.
2. Buffer address bits 23–16 and status/ownership flags.
3. Negative buffer byte count.
4. Received length or transmit completion/error information.

At `0x078745a6` the receive-buffer return routine writes `0xfa12` at
descriptor offset `+4`: two's-complement **−1518**. It constructs the
24-bit buffer address and sets OWN before writing the address/status
longword. Descriptor cursors advance by eight and wrap at recorded ring
limits.

The initialization path at `0x07874352` initially offers 16 receive buffers
at a `0x600` (1536-byte) stride. A 32-entry RX ring does not mean every
descriptor is initially controller-owned. Respect OWN instead of assuming
the entire ring is populated.

### Address aliases

The firmware explicitly masks descriptor addresses with **`0x00ffffff`**.
On receive, at `0x07874e30` onward, it rebuilds the address from the two
descriptor words and ORs **`0x07800000`** into it for CPU access.

This is direct evidence of separate CPU pointer conventions and 24-bit
Ethernet DMA addresses. It strengthens the earlier memory-alias hypothesis.
The board's complete bus decoding remains unresolved: provide a deliberate
DMA-to-RAM translation, not a 128 MB array just because pointers begin
with `0x07`. Do not blindly apply OR `0x07800000` to every MMIO address.

### Byte ordering

CSR3 = 6 enables payload byte swapping. The AMD manual explicitly says
the initialization block and descriptors **are not swapped by BSWP**;
only packet-buffer DMA through the FIFO is affected.

The firmware independently arranges the six physical-address bytes into
byte pairs when filling the initialization block (`0x07874198` onward),
and stores descriptor low-address words before high-address/status words.
This is consistent with the standard 68000/LANCE layout.

The emulator therefore needs separate rules for:

- CPU big-endian memory access.
- Numeric 16-bit controller reads/writes of initialization words and descriptors.
- Payload DMA with BSWP applied.
- Frame byte order on the TAP side.

Swapping the complete descriptor or initialization block because CSR3 bit 2
is set would be incorrect. Odd-length packets also need deliberate handling.

## 4. Transmit and receive behavior observed

At `0x07874bd0`, a transmit path prepares a descriptor, places the byte
count at `+4`, and ORs **`0x8300`** into its status/high-address word:
**OWN | STP | ENP**. It then selects CSR0 and writes TDMD with the current
INEA state. The path shown uses a `0xffc4` (−60) minimum-size transmission;
other packet lengths and any chained transmit paths still require a full
driver audit.

At `0x07874e1c`, receive processing tests OWN and the STP, ENP and error
bits, reads the receive byte count at `+6`, reconstructs the CPU buffer
address, and returns processed buffers to the controller. Subsequent code
examines destination addresses and protocol type/length fields. This is
actual Ethernet frame processing, rather than only a boot-time controller
self-test stub.

The controller model must update ownership, status, counts and interrupt
causes. TAP normally provides Ethernet frames without their preamble/FCS;
the LANCE side's FCS/count behavior must follow the manual and whichever
existing emulator backend is reused. This boundary has not been dynamically
tested. Do not assume a raw frame memcpy alone satisfies the driver.

## 5. Interrupts

MNENG3 setup at `0x07874c86` initializes a controller object at
`0x0799ed48`, records base `0x00300000`, and installs handler
**`0x07874cd0` at `VBR + 0x6c`**.

The raw write instruction is:

```
21 bc 07 87 4c d0 01 70 00 00 00 6c
```

It uses a full-format indexed destination with the index suppressed and
long displacement `0x6c`. Capstone's rendering includes an invalid-register
placeholder; interpreting the extension word is necessary. Offset `0x6c`
means vector **27**, corresponding to **level-3 autovector**.

This strongly suggests a level-3 interrupt delivery model. Exact external
pin wiring, any glue logic and interrupt acknowledgement circuitry are
not proven from software alone.

The immediate handler:

1. Saves registers.
2. Writes zero to the selected CSR data port, disabling INEA without
   writing ones to the latched cause bits.
3. Schedules deferred processing and returns with RTE.

The deferred handler at `0x07874d02` calls `0x07874d18` to process status,
then writes `0x0040` to re-enable controller interrupts. It tests:

| CSR0 mask | Meaning |
|---|---|
| `0x0200` | Transmit interrupt |
| `0x0400` | Receive interrupt |
| `0x0800` | Memory error |
| `0x1000` | Missed packet |
| `0x2000` | Collision/heartbeat error |
| `0x4000` | Babble |
| `0x8000` | Error summary |

Preserve interrupt causes while INEA is clear. Model an asserted interrupt
condition, including reassertion on re-enable, rather than firing one host
callback per received packet and discarding its state.

## 6. Multicast filter

MNENG3 routine `0x07874a02` clears four words beginning at
**`0x07873e0c`**, the initialization block's 64-bit logical address filter.
It iterates over configured addresses, calls the CRC-related routine
`0x07941aa0`, reduces the result to a six-bit index and sets the appropriate
filter bit. This is another independent LANCE fingerprint.

LAT uses multicast reception, so the controller/backend must support it.
Implement station-address, broadcast, logical hash filter and any requested
promiscuous/loopback mode in the controller. The host bridge's multicast
forwarding is a separate integration concern.

## 7. Reuse options

### MAME

`src/devices/machine/am79c90.cpp` explicitly implements **Am7990 and
Am79C90**, with a network interface, DMA callbacks and an interrupt callback.
Its source uses the AMD controller manuals. This is a close match to the
firmware interface and pairs naturally with MAME's CPU32 core. The model
has TODOs, including external loopback; this may matter for a future
boot-ROM diagnostic path even if operating-software startup works.

### SIMH

`VAX/vax_xs.c` is explicitly a **LANCE Ethernet simulator**. This materially
improves SIMH's usefulness for the project compared with considering only
its CPU support. It implements initialization, descriptor processing,
Ethernet queues and CSR behavior.

It is VAX-specific: its `GETW`/`GETL` helpers decode little-endian bytes,
its DMA accesses use `XS_READB`/`XS_WRITEB`, it ORs platform address bits
into DMA addresses, and it raises VAX interrupts. A 90TL adaptation needs
new memory/endianness/DMA/interrupt glue and a review of CSR3/BSWP effects.
It is not directly usable unchanged on this big-endian CPU32 board.

### QEMU

`hw/net/pcnet.c` includes classic LANCE-compatible operation within a newer
PCnet model. It is another reference, but the MAME implementation is a
more direct device-family fit and QEMU still lacks a demonstrated CPU32
configuration in our investigation.

No emulator model has been compiled or validated against the 90TL image yet.

## 8. Minimum implementation now justified

The Ethernet side can be bounded to:

1. Four 16-bit CSRs behind RDP/RAP at `0x300000`/`0x300002`.
2. Reset/STOP/INIT/STRT/TDMD behavior and CSR0 status/clear semantics.
3. DMA of the 24-byte initialization block, 8-byte descriptors and packet buffers.
4. RX/TX ring ownership, buffer lengths, completion/error state and wraparound.
5. Payload byte swap, physical address and multicast filtering.
6. Stateful IRQ output wired provisionally to CPU level 3.
7. Ethernet-frame backend attached to TAP/bridge.

No separate coax transceiver, Manchester encoder, collision-detection IC,
oscillator or analog PHY model is needed for normal frame-level operation.
Diagnostic loopback and error/status behavior may still be required.

## 9. Remaining uncertainty

- Exact LANCE-compatible physical chip and revision; Am7990 versus C-LANCE
  or a compatible implementation.
- Factory station-address storage. The six-byte read at `0x00200000`
  remains a plausible MAC source, but its caller chain was not resolved.
- Full RAM/bus alias map and controller interrupt wiring.
- All multicast/mode changes, ring restart, receive chaining and error recovery.
- Boot-ROM initialization and network self-test, because only load images
  have been analyzed.

For an initial emulator, select a documented Am7990-compatible model and
validate against these observed register/DMA sequences before pursuing
physical-chip identification further.

## Reproduction and artifacts

Run `python3 tools/inspect_ethernet.py` from any directory. It verifies the
known image SHA-256 values before using fixed offsets, and writes:

- `analysis/MNENG1.ethernet.asm`
- `analysis/MNENG3.ethernet.asm`
- `analysis/ethernet-summary.json`

Raw instruction bytes are included. Fixed-offset analysis is tied to the
downloaded images in `analysis/inventory.json`. Capstone 68020 mode is a
decoding aid, not a claim that the chip is a 68020; its full-format address
rendering and bit-operation size suffixes require care.
