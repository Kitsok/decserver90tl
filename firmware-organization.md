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
| 0x0780500e, long | Accumulated port diagnostic/inhibit status, copied to 0x0798faaa | 0: healthy synthetic ports |
| 0x0780501e, word | Transient diagnostic/recovery port mask, consumed at 0x078714d6 and 0x07871520 | 0; disk 0x1c00 selects invalid indices; earlier 0x00ff setting inhibited all ports |
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
| TPU low-byte status | Fast receive handling for eight ports | Functional receive-ready mapping implemented; electrical routing unresolved |
| TPU status bits 8..11 | Four DUART combined interrupt paths | Functional combined-IRQ mapping implemented; board routing unresolved |

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
need reconstruction before serial-wire emulation is demonstrated. A functional
status adapter now supplies RX-ready bits 0..7 and combined DUART IRQ bits
8..11. CISR writes clear bits where zero is written.

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
- Firmware configures port 1 for CSR=0xbb, MR1=0x13, MR2=0x07 (9600, 8N1)
  and consumes three diagnostic FIFO-injected CR bytes through its ISR.
- Port 8 also consumes three diagnostic CRs and writes the DS90TL banner
  and `Enter username>` prompt to its transmit holding register.
- A subsequent login test reaches Local on port 1; see the recipe and
  limitations below. No decoded serial-wire output or external endpoint yet.
- Transmit behavior differs between ports 1 and 8 and is the next
  investigation. Physical UART/TPU interrupt wiring remains unresolved. A holding-register trace is not a modem backend.
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

## Corrected port-diagnostic handoff and receive probe

The header word at 0x0780501e was initially mislabeled as a presence mask.
At 0x07871584..0x07871598, startup ORs it into both halves of the longword
at header +0x0e and copies the result to 0x0798faaa. The earlier 0x00ff
handoff therefore marked all eight ports in both halves (observed combined
value 0xcbffcbff), while DUARTs remained at reset CSR/MR settings.

Clearing header +0x0e and +0x1e reports healthy diagnostic status. Under the
same assisted timing model and warm store initially seeded from FF, this
causes normal UART configuration. Port 1 changes to CSR 0xbb, MR1 0x13,
MR2 0x07, with MAME reporting 9600 baud. Three paced CR bytes injected into
its FIFO are read at callback PC 0xfffff2a0, within the internal-RAM receive
path. The earlier zero-filled store was not a reconstructed factory image;
fresh/warm erased-store comparisons were retained separately.

`--uart-probe-port` and `--uart-probe-at` control this diagnostic only.
Direct FIFO injection deliberately bypasses receiver enable and framing,
so it cannot establish wire-level receive, baud detection or modem handling.
The port-1 holding-register TX trace contains only an initial CR. The port-8
validation run, however, consumes all three injected CRs and emits the full
DS90TL V2.4 banner and `Enter username>` prompt. Register-level transcripts
are saved beside the corresponding logs. They are not decoded wire captures.
Investigation of transmit asymmetry follows the receive-path checkpoint commit.

## DUART transmit-rate update correction

Channel controls showed that ports 2, 3 and 8 produced the username banner,
while port 1 stopped after its initial CR despite transmitter enable and
TX-ready at that write. This was a model defect, not a firmware flow-control
requirement: MAME's ACR write handler refreshed both serial rates, and the
unchanged-rate refresh reset an active shift register and its timer while
leaving the DUART's separate ready status stale.

The pinned dependency patch now changes serial-interface rates only when
their numeric values change. A subsequent identical port-1 probe emits the
full banner and Enter username prompt, with TX-ready asserted between
holding-register writes. The 30-second run exits normally. Command/status
traces are included in the regression log, and `patches/README.md` explains
the change and its limits. That regression reached the username prompt;
the later login test below reaches Local through FIFO injection.

## First Local prompt: reproducible diagnostic login

The injector now accepts a bounded byte sequence rather than only CRs.
Three leading CRs, followed by SIMULATOR and CR, yield an accepted username
and Local prompt on port 1. A single leading CR control did not establish
that login state; initialization/autobaud interaction remains to be mapped.
The working sequence begins at simulated second 30, one byte per second.

A fresh-store reproduction first ran 60 seconds from absent NVRAM, then
rebooted with the same store for a 50-second login experiment. Both exited 0
and the original firmware hash stayed unchanged. The report and complete
commands are in `analysis/local-prompt-verification.json`; the register-level
transcript is `analysis/mneng3-local-repro-login-50s.tx.txt`.

Observed tail:

```
Enter username> SIMULATOR
Local -602- Internal memory error in server parameters
Local -603- Communications server defaults in effect
Local>
```

Do not interpret the parameter warnings as a proven physical RAM fault or
as a fully diagnosed NVRAM problem. The guest reports defaults in effect;
the underlying validity/initialization cause is the next investigation.
No firmware warning is suppressed. Input bypasses receiver-enable, framing,
baud sampling and modem pins; output is a TX-register trace, not decoded wire
capture. This establishes the original command interpreter's prompt under
the current assisted model, not a complete eight-modem/network appliance.

### Host PTY transport (simulator extension)

Interactive mode exposes eight PTYs, indexed one-to-one with firmware UART ports
1–8. A 1 ms emulated timer transfers host input to an empty DUART RX FIFO; output
is captured at transmit-register writes. This does not change the inferred
firmware address map or implement receiver-enable, baud/framing or modem pins.
The PTYs are simulator facilities, not inferred hardware components.

### DTR/DSR command and status paths

The 90TL connector exposes DTR output and DSR input. Pin-mask tables at
0x079423c4/c8 contain DSR masks 0x01 (channel A) and 0x04 (channel B), copied
to driver object +0x141a. The DSR query at 0x07944318 reads shared input
register base+0x1a with active-low polarity. DTR setter 0x079442d4 issues
command 0x90 to negate and 0x80 to assert the output. These match 2692-family
extended commands, which the generic 68681 model previously misdecoded.
MR2 bit 4 enables DSR gating of the transmitter, and MR1 bit 7 enables DTR
receive throttling. `SET PORT FLOW CONTROL DSR` produced MR1=0x93/MR2=0x17
in the firmware verification; default XON/XOFF mode used 0x13/0x07.
See [modem-lines.md](modem-lines.md) for disassembly, sources, modeled behavior,
provisional B-channel routing, sideband API and verification. This supersedes
the earlier statement that modem pins were entirely unimplemented.

### Ethernet verified against host traffic

The assisted MNENG3 model has now exchanged live frames through the existing
AM7990 and a host TAP/bridge. With the test copy configured as 192.0.2.90/24,
ARP and all three pings from 192.0.2.1 succeeded, TCP port 23 returned Telnet
negotiation, and a LAT advertisement used destination 09:00:2b:00:00:0f with
EtherType 0x6004. The observed source MAC was 02:90:00:00:00:01. These results
supersede the earlier absence of live networking validation; full Telnet login
and inbound LAT sessions are still untested. The register-level DMA callbacks
and active-low level-3 interrupt wiring required no changes for these exchanges.
The loopback fixture independently checks CSR3=6 byte order, ownership, RX/TX
interrupt flags and acknowledgement. See network.md and the Ethernet reports.

### Permanent database survives; operational startup restoration does not

A two-boot isolated test established SET/DEFINE/CHANGE behavior using distinct
server names. In-session SHOW and LIST expose the correct operational and
permanent values. After CHANGE, normal host shutdown and restart, LIST retains
the changed name but SHOW uses the generated LAT_029000000001 default, with
-602/-603 startup warnings. This narrows the open problem: the host NVRAM file
is saved and reloaded, and the permanent value is readable, while applying the
saved server parameters during startup fails. Additional queued-write drain
time did not resolve it. The validation/restoration cause and other record types
remain unverified. See settings-storage.md and analysis/settings-verification.json.

### Settings startup restoration fixed

The previously forced boot-header bits 19–21 invoked metadata fallback at
0x079406de, which also sets bit 18 in header +0x16 (BSET #2 at byte +0x17).
That bit overrides the successful record-5 checksum and selects server defaults
at 0x078715d4. It also causes the -602/-603 reports at 0x0787ae20 onward.
The old boot-handoff description is superseded: the model now fills only erased
factory fields from image constants, without forcing those flags.

Record 49 reads the reserved region starting at 0x100c00. Its relevant fields
are offsets +0x08 (14 bytes, defaults at 0x0786c264), +0x1e (20 bytes, defaults
at 0x0786c272), and +0x32 (8 bytes, defaults at 0x0786c286). The second group
contains the length-prefixed default boot-image label MNENG1. Exact factory
hardware contents remain unknown; these are explicit synthetic values.

Record 5 has logical base 0x0adc, stride 0x0194 and checksum boundary 0x0192.
The byte-storage conversion maps its 201-byte payload to 0x10116e..0x101236
and its 8-bit additive checksum to 0x101237. Both firmware checksum validation
and actual corrupt-record fallback remain intact. Repeated SET/DEFINE/CHANGE
and restart checks now restore the changed server name in both databases,
without -602/-603. See analysis/settings-handoff-verification.json and the
updated analysis/settings-verification.json.
