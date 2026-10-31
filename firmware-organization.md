# MNENG3 firmware organization and runtime map

Living investigation notes, started 2026-10-31. Target: original MNENG3.SYS,
DNAS V2.4, DECserver 90TL-like board with 4 MiB RAM. Addresses below are
linked CPU addresses unless explicitly identified as physical or file offsets.
This describes recovered behavior, not vendor symbols or a complete memory map.

## Evidence and notation

- **Observed:** executed in the simulator or directly decoded from matching
  instructions/data. Simulation proves behavior under the current model,
  not electrical equivalence to a physical 90TL.
- **Inferred:** consistent with code and documents but not independently
  established on hardware.
- **Substitution:** an explicit simulator approximation of missing ROM or
  peripheral behavior. These must remain distinguishable from discoveries.

Firmware SHA-256:
`a3764087d79df64eb7124056824652cf23b558fcae2029f887e4a37a3db49ad3`.
The file remains unchanged. Runtime header writes are made only in guest RAM.

## Image, linking and address decoding

MNENG3 is a downloaded operating image, not a complete reset/boot ROM.
Its size is 0x18b600 bytes. The recovered mapping is:

```
linked address = file offset + 0x07805000
physical address in current model = linked address & 0x00ffffff
```

Examples: file 0x2a00 maps to linked 0x07807a00, physical 0x807a00;
startup at linked 0x078713f8 maps to file 0x6c3f8, physical 0x8713f8.
The 24-bit external mask is inferred. Do not assume the high bits of all
pointers can be discarded for instruction semantics, signed comparisons,
CPU-space accesses or internal exception processing.

| Physical range/address | Current interpretation | Confidence/limitations |
|---|---|---|
| 0x000000..0x001fff | Synthetic inherited vectors and diagnostic loops | Substitution, not original ROM |
| 0x100000..0x10ffff | File-backed configuration-store window | Accesses relative to 0x100c00 observed; capacity/technology provisional |
| 0x200000..0x200005 | Six-byte identity/MAC reader | Observed reader; synthetic MAC supplied |
| 0x200000 read strobe | Possible clock/interrupt acknowledge | Inferred from ISR; simulated acknowledge is provisional |
| 0x300000/0x300002 | LANCE RDP/RAP | Strong firmware evidence |
| 0x400000..0x40007f | Four dual UART blocks, 0x20 bytes each | Strong driver-table/register evidence |
| 0x800000..0xbfffff | 4 MiB external RAM | Current model; aliases/timing not fully recovered |
| 0xfff000..0xfff7ff | MCU internal RAM, interrupt code and state | Observed firmware use |
| 0xfffa00..0xfffbff | SIM and related MCU register area | MC68332-style register evidence |
| 0xfffc00..0xfffdff | QSM area and software/internal state | Individual registers must be identified separately |
| 0xfffe00..0xfffe27 | TPU control/status registers | Explicit firmware accesses |
| 0xffff00..0xffffff | TPU channel parameter RAM, 16 bytes/channel | Explicit initialization table |

Other candidate windows, including flash/control, are covered in
`internal-structure.md`; they have not all been exercised by this simulator.

## Boot handoff and initialization

The current reset shim copies the image to physical 0x805000 and enters
0x078713f8. A NOP/JMP stub at image file offset 0x2a00 also points there.
This bypasses actual ROM diagnostics, image loading and ROM setup.

Observed startup sequence:

1. Save the inherited SP in the image header and select SP=0x079dbfc0.
2. Copy 256 inherited vectors into RAM at 0x0783b6ac; set VBR there.
3. Run board initialization through 0x079404a8 and 0x0794458c.
4. Apply the internal-register table at 0x0786c2ec. It initializes SIM,
   QSM and TPU control/parameter registers, then waits for TPU host requests.
5. Zero BSS-like RAM from 0x0798f9ac up to the startup stack.
6. At 0x079404f6, build the configuration-record table, inspect persistent
   checksums and initialize memory/model-dependent state.
7. Create the startup task through 0x0786fefc; its continuation is 0x078714ac.
8. Continue subsystem/port initialization, eventually entering the scheduler.

| Linked handoff field | Consumer/meaning | Current supplied value |
|---|---|---|
| 0x07805016, long | Validity/default flags; bits 19..21 select three metadata defaults at 0x07940696 onward | OR with 0x00380000; provisional substitute for ROM validation |
| 0x0780501e, word | Port-presence mask, consumed at 0x078714d6 and 0x07871520 | 0x00ff; disk value 0x1c00 selects unsupported port indices |
| 0x07805027, byte | Board/profile discriminator | Firmware initialization behavior, not an independently verified hardware ID |
| 0x078051a2, long | Inherited ROM fatal-report callback | 0x1400 diagnostic sentinel |
| 0x078051b6, long | External RAM size consumed at 0x07940578 | 0x00400000 |
| 0x078051ba, long | Optional ROM/board metadata pointer | Not reconstructed |
| 0x078051e4, byte | Board revision/profile used to choose model ID 0x10 versus 0x11 | Produced/consumed by image initialization; handoff incomplete |
| 0x078051e6 | Saved inherited SP | Written by startup |

The initial synthetic SP is 0x07bff000. These settings establish a useful
bring-up contract, not a proven reproduction of the original boot ROM.

## Exceptions and inherited ROM services

Startup inherits exception vectors rather than constructing every handler
from scratch. VBR=0x0783b6ac is observed after early initialization.

The downloaded 90M+ MNBOOT.SYS reference is NOT a verified 90TL ROM.
Its plausible payload begins after a 512-byte wrapper; vector 3 targets
0x408. That code implements byte-wise transfers and instruction handling
for address errors, with additional code at 0x8c0. This provides concrete
related-model evidence for an inherited alignment service.

CPU32 does not directly support odd-address word/longword operands. MAME's
generic 16-bit CPU32 memory interface otherwise uses aligned accessors,
which can silently touch neighboring addresses. MNENG3 does perform odd
word/longword data accesses. Examples observed in the trace:

- Longword writes at 0x0799f21f and 0x0799f223, PCs 0x078ed000/0x078ed004.
- Word read at 0x079dbed5, callback PC 0x0788667c, from
  `MOVEA.W -0x37(A6),A5` at 0x07886678.

`--rom-alignment-assist` substitutes unaligned data-transfer semantics at
CPU callbacks. It does NOT execute the ROM handler or model exception-frame
and cycle costs. The default stops on these accesses for diagnosis.
With the assist, the previous configuration error 0x543 is avoided.

### Fatal-report path

At 0x07948438, the firmware stores:

| Field | Meaning |
|---|---|
| 0x07805028 | Caller/return address, or directly supplied failure location |
| 0x0780502c | Saved SP on this entry path; some other fatal paths do not populate it |
| 0x07805030 | SR |
| 0x07805032 | Parameter |
| 0x07805036 | Error code |

The common path at 0x07948474 jumps through header pointer 0x078051a2.
Some failure paths populate the fields directly before entering it. The
simulator's callback prints the report instead of attempting ROM dump/reboot.
Inherited-vector sentinels separately identify exceptions before replacement
handlers have been installed.

## Task queues and scheduler

The system has deferred work queues as well as startup/task context creation;
calling every callback a separate thread would overstate what is known.

| Routine/data | Recovered role |
|---|---|
| 0x0786fefc | Creates startup task/context with supplied stack and continuation |
| 0x078ecde8 | Scans and dispatches deferred queues |
| 0x079ab514 | First queue descriptor; eight priority slots, stride 0x40 |
| Queue +0/+4 | Head/tail linkage |
| Queue +8/+0xc | Pending count/dispatch count |
| Queue +0x10/+0x14 | Timestamp words written at dispatch |
| Task node +0 | Link; self-reference when detached, zero at end of queued chain |
| Task node +4 | Entry callback; dispatcher calls it with A2 pointing at node |
| 0x078ecf88 | Enqueue work at priority D3, validate node linkage, clear idle flag |
| 0x078ecfbc | Related enqueue-if-not-already-queued path |
| 0x079ab714, byte | Idle/wait flag; enqueue routines clear it |
| 0x07941610 | Idle/checksum loop, fixed counter 0x708 |
| 0x078eced0 | Error 0x298 when that idle counter expires |

The idle loop also checksums chunks of image memory through pointers at
0x079ab718/1c/20. It is not simply a CPU STOP instruction. Interrupt arrival
alone need not resume foreground work; ready work must clear the idle flag.

### Clock-driven work

The clock-work object at 0x079b69f8 contains two deferred nodes. Setup at
0x07944720 registers their callbacks:

- Node at +0: approximately 10 ms work, priority 3, callback 0x079448b6.
- Node at +8: approximately 100 ms work, priority 0, callback 0x0794488c.
- +0x10/+0x14: last scheduled times for 100 ms/10 ms work.

The service at 0x0794479e compares the internal microsecond counter against
these deadlines and enqueues detached nodes. One callback reaches the wider
periodic maintenance routine at 0x07871af4; another reaches queue/timer
maintenance at 0x078ecef8. Their entire call trees are not yet mapped.

## Interrupts and timekeeping

| Source/path | Recovered behavior | Model status |
|---|---|---|
| LANCE | VBR+0x6c, vector 27, level-3 autovector candidate; handler 0x07874cd0 | AM7990 model connected to CPU level 3; network backend absent |
| Board clock/serial aggregate | VBR+0x78, vector 30, level-6 autovector; installed target 0xfffff184 | Provisional external interrupt source |
| TPU low-byte status | Fast receive handling for eight ports | Routing to actual DUART outputs not yet implemented |
| TPU status bits 8..11 | Four DUART combined interrupt paths | Firmware dispatcher identified; board routing unresolved |

The level-6 implementation includes code/stubs copied into MCU internal RAM.
The clock entry at 0x07944a48 reads physical 0x200000 and updates software
counters; this is evidence for acknowledge side effects at that address.
It does not establish the physical clock IC or wire routing.

Routine 0x07944aba adds 1953 microseconds plus a fractional correction to
0xfffff024, carrying into 0xfffff020. Related internal state is at
0xfffff028/2c and 0xfffff0cc..d1. The path performs software pulse division.
Sending only 512 interrupts/second makes guest time roughly 16 times slow;
8192 input pulses/second yields close-to-real-time guest time in tests.

The simulator gates this source using TPU CPR0 bits 13:12, corresponding to
channel 14 priority. Firmware disables those bits during setup and enables
them at 0x07944788. Reading the identity base clears the simulated level-6
request. This is a functional substitution, not TPU microcode emulation.
An external timer or a TPU-generated pulse routed externally are both still
possible physical implementations.

## UART organization and scaled addressing

Four dual UART blocks have bases 0x400000, 0x400020, 0x400040, 0x400060.
The image initializes all four in the assisted runs. Device byte registers
occupy even addresses on the 16-bit bus. See `internal-structure.md` for
RAM-object/descriptor pairs and `src/mame/decserver90tl.cpp` for adapters.

Fast receive code at 0x07944b12 reads TPU interrupt status and scans the low
eight bits. At 0x07944b44 it doubles the selected port number into D0.
The instruction at 0x07944b48 has raw bytes `41f1 0602`. Its brief extension
0x0602 selects D0.W * 8, so its effective address is:

```
A0 = 0x400000 + (port * 2) * 8 + 2
   = 0x400000 + port * 0x10 + 2
```

Capstone's printed operand omitted the scale. This explains the previously
suspected compact alias: ordinary per-channel status/data offsets suffice.
The code reads status at A0 and receive data at A0+4, matching the dual UART
layout. Raw extension bits must be checked when printed disassembly looks
inconsistent.

The higher-bit path at 0x07944c16 scans four DUART sources and reads ISR
at block+0x0a. Bits 0/4 select transmitter A/B; transmit data is written at
block+0x06 or +0x16. Other branches handle status/input-change conditions.
The physical wiring and precise TPU interrupt-generation semantics still
need reconstruction before interactive serial I/O is demonstrated.

## Persistent configuration organization

The record table at 0x079ac16c has 16-byte entries, initialized by
0x07940c36 and its continuation. Recovered entry fields:

| Offset | Meaning inferred from lookup/checksum code |
|---|---|
| +0, word | Record stride/size unit |
| +2, word | Primary count |
| +4, long | Primary base offset |
| +8, long | Secondary base offset |
| +0xc, word | Secondary count |
| +0xe, word | Payload/checksum boundary metadata; 0xffff marks special cases |

Lookup at 0x078725b2 checks logical record/index bounds. Reads eventually
map logical offsets into physical storage relative to 0x100c00; conversion
includes multiplication/division by 1/2. Do not assume table offsets are
already physical byte offsets.

| Routine | Role |
|---|---|
| 0x078720ce | Check record checksum, preserving caller registers |
| 0x0787240e | Read a block, including pending-write overlays |
| 0x078724de | Read a byte, including pending-write overlays |
| 0x07872344 | Submit configuration write operation |
| 0x078721ac | Progress pending writes/readback/checksum updates |
| 0x07940c00 | Set QSM bit 2 at 0xfffc14, write byte through A2, clear bit |
| 0x07940c22 | Firmware delay loop between programming operations |
| 0x0798fb20 | Pending-operation list head |

The store is file-backed in the simulator and separate from MNENG3.SYS.
Neither all-FF nor all-zero bytes are a reconstructed factory image.
The earlier record-22 offset 0x0e00 versus size 0x0c00 failure is avoided
with alignment assistance; it was not evidence of insufficient physical
storage capacity. Additional factory metadata dependencies remain possible.

## CPU and external-bus timing

The firmware writes SYNCR=0x9b00: W=1, X=0, Y=27. With an assumed
32768 Hz reference, the documented formula gives 14,680,064 Hz. The model
now uses that rate instead of provisional 16 MHz. The reference crystal
frequency is inferred, not measured.

With no added RAM waits, the idle budget measured 159295 emulated CPU
cycles, about 10.851 ms. A 10 ms deferred deadline sampled on approximately
1.953 ms clock ticks can require six ticks, about 11.719 ms. This is a
plausible explanation for the observed idle timeout; exact bus/CPU timing
is not established. Some configured chip selects request external DSACK.

`--ram-wait-cycles 1` adds one experimental CPU cycle per 16-bit external
RAM bus transfer, including instruction fetches. Wider/odd transfers are
charged for their component bus accesses. The default remains zero. With
alignment assistance and this wait setting, both 30- and 60-second runs
complete without the earlier fatal errors. This demonstrates a timing
sensitivity, not a measured real-board wait count. No firmware timeout
checks are patched out.

## Current checkpoint and open work

- Original MNENG3 executes with 4 MiB RAM and unchanged file hash.
- Alignment and RAM-wait substitutions permit a 60-second bounded run,
  with DUART initialization and continuing scheduler/clock activity.
- No Local prompt or external serial endpoint has been demonstrated.
- UART/TPU interrupt wiring, receive injection and completed transmit output
  are the next investigation. A holding-register trace is not a modem backend.
- Ethernet driver identification is strong, but DMA/ring behavior and host
  networking have not yet been validated by live packets.
- ROM handoff, true persistent-storage technology/capacity, exact clocks,
  bus waits and exception fidelity remain provisional.

Companion files: `internal-structure.md`, `ethernet-controller.md`,
`mac-window.md`, `boot-rom-search.md`, `implementation-status.md`, and
`analysis/mneng3-*.log`.

Manufacturer references:
https://www.nxp.com/docs/en/user-guide/MC68332UM.pdf
https://www.nxp.com/docs/en/reference-manual/SIMRM.pdf
