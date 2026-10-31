# Simulated DECserver 90TL: implementation concept

2026-10-31. Proposed design based on the static investigation in this
repository. This is not an implemented or validated emulator.

## Intended result

A Linux process runs the original DECserver firmware and presents one
Ethernet station and eight asynchronous serial ports. Ethernet attaches
to a Linux bridge through TAP. Each serial port can connect to a virtual
modem, a PTY, or a test endpoint. Firmware loads from local storage without
an external MOP/BOOTP/TFTP server. Configuration survives a simulated
power cycle.

The original firmware implements LAT, Telnet, management commands, session
handling and protocol behavior. The simulator implements CPU-visible board
behavior. It does not reimplement the DECserver command interpreter or LAT
stack in host code.

Initial targets:

- MNENG3 DNAS 2.4 as the first implementation target, with 4 MB simulated RAM.
- MNENG1 V1.1C retained for diagnostic comparisons with the physical server.
- One virtual machine instance per DECserver identity.

The emulated RAM size, addresses and device details below remain subject to
the unresolved board decoding and ROM handoff. Exact physical-chip branding
is not required when a compatible register-level model is sufficient.

## Architecture

```text
 Linux bridge
      |
     TAP <---- Ethernet frames ----> LANCE-compatible controller
                                      | registers, DMA, IRQ
                                      |
                       CPU32 + board memory + event scheduler
                          |                    |
                    SIM/QSM/TPU           four dual UARTs
                    NVRAM/control         eight channels
                          |                    |
                  local image store        serial adapters
                                             /        \
                                           PTY     modem socket
                                                       |
                                           courier-emu / other modem
                                                       |
                                             modem's own media path
```

Keep modem execution outside the DECserver process. A modem crash or restart
then becomes a serial disconnection instead of corrupting the terminal
server. The DECserver simulator handles the DTE connection; the modem
backend continues to own AT behavior, modulation, DSP and its audio/SIP
connection as applicable.

## CPU and runtime choice

Recommended first implementation: **a headless MAME machine using its
CPU32 core and Am7990-compatible device model**, with a new 90TL machine
definition, board devices and serial adapters. The source investigation
established that both CPU/device families exist in MAME; compatibility with
these images remains to be tested.

This avoids treating standalone Musashi's 68020 mode as full CPU32 support
and avoids extracting the MAME CPU from its framework during bring-up.
Do not make a standalone rehosting effort a prerequisite for reaching the
DECserver prompt. Keep board behavior in separate devices/helpers so the
choice can be reconsidered later if deployment constraints justify it.

SIMH is a viable alternative framework, particularly for terminal and Ethernet
infrastructure, but its inspected 68k configurations lack a CPU32 selection.
Its VAX LANCE implementation is useful as a reference or adaptation source.
Do not combine a MAME CPU, SIMH scheduler and two competing Ethernet models
in the initial implementation.

## Board model

### Memory and CPU

Use a CPU32 execution core with supervisor state, VBR, function-code/control
registers, exceptions, interrupt acknowledgement, STOP/wakeup and bus faults.
Model RAM with explicit address translation shared by CPU and DMA.

The tentative external RAM layout is 4 MB beginning at physical `0x800000`;
this is consistent with the linked pointer convention and 24-bit DMA, but
must be checked before being treated as a board specification. For example,
linked `0x07873e04` corresponds to DMA `0x873e04`. CPU RAM pointers and
MMIO addresses must not be translated with one indiscriminate OR operation.

Represent internal RAM separately. Unmapped accesses should be recorded
and, outside explicitly documented bootstrap experiments, produce the
appropriate fault. Returning zero from every unknown device would conceal
missing behavior and cause misleading startup progress.

### Ethernet

Expose the recovered 16-bit RDP/RAP pair at `0x300000`/`0x300002`.
Reuse a LANCE-compatible model for CSR0–CSR3, initialization, DMA,
descriptors, filtering, completion and errors. Connect its interrupt output
provisionally to CPU level 3, matching the installed vector at VBR+`0x6c`.

The guest supplies ring addresses and lengths. Do not hard-code MNENG3's
observed 32 RX and 8 TX entries into the controller model. Handle the
CSR3 payload swap separately from descriptor/initialization-word access.
Adapt frames and FCS/count conventions at the host-network boundary.

Give each instance its own MAC and configurable firmware node/IP identity.
TAP carries Ethernet frames, including LAT and MOP, rather than only IP
traffic. Host-side networking setup should be an explicit deployment step;
the simulator can accept an already-created TAP interface.

### Serial

Expose four dual-UART register blocks at:

```
0x400000  0x400020  0x400040  0x400060
```

Their paired-channel organization is strongly supported by firmware tables.
Use 68681-style behavior as the starting point, validating the exact variant,
FIFO depth, access aliases and physical-port numbering against the image.
The optimized receive window remains an explicit investigation item.

Model data/status registers, command effects, interrupt masks, readiness,
receive/transmit buffers, errors, BREAK and modem-input changes. A host
write does not instantly transmit an unlimited stream: schedule guest-visible
completion according to baud and framing. Represent firmware-observed
queue depth and flow control without generating electrical waveforms.

### Integrated peripherals and board state

Implement the observed SIM, QSM, TPU and GPIO interfaces:

- SIM configuration, watchdog service and periodic interrupt behavior.
- QSM operations that startup or persistent configuration actually reaches.
- TPU parameter RAM, host requests, completion and interrupt state.
- Board identity/control bits, reset and the recovered persistent-storage path.

The initial TPU model should implement the services used by the firmware
as scheduled operations. It need not execute TPU microcode. A request must
complete with meaningful state changes; merely clearing every request bit
immediately is not a validated behavioral model.

## Local boot and simulated flash

Use a file-backed local image store, initially large enough for the selected
images with configurable capacity. A 4 MB store is a reasonable initial
design parameter, not a claim about physical 90TL flash hardware.

On reset, a small **simulator-owned boot shim** loads the selected image into
the recovered RAM layout, constructs the required ROM handoff state, then
transfers control to the actual operating-software startup. The handoff must
be reconstructed: stack, vectors, memory-size/board records and any ROM
service dependencies cannot be guessed away. Failed assumptions should be
visible in a boot report.

Two distinct capabilities are involved:

1. **Boot without a network load host:** the local loader provides this first.
2. **Guest-visible flash operations:** a later model exposes the candidate
   flash window at `0x600000` and associated control at `0x440000`, with a
   supported device ID, command protocol, geometry and durable contents.

The first capability does not prove the second. Preserve that distinction in
documentation and acceptance tests. A real 90TL ROM dump would allow a more
faithful boot path and should replace parts of the shim if available.

For guest-visible flash, follow a device protocol actually supported by the
firmware and validate that the chosen board profile reaches it. Increasing
capacity alone is insufficient. Publish updates to the backing file through
a safe persistence boundary, and make reset/power-loss semantics explicit.

Configuration storage is a separate backing file. Its guest interface is
still unresolved; do not substitute host-side command parsing to fake
permanent firmware settings.

## Virtual modem attachment

A raw PTY is useful for initial AT-command/data testing. It does not provide
a dependable cross-process transport for all required modem signals.

For full integration, define a versioned Unix-domain socket protocol with
length-delimited events:

| Event | Direction | Purpose |
|---|---|---|
| DATA | Both | Binary serial bytes |
| LINE_CONFIG | Server to modem | Baud, data bits, parity, stop bits |
| CONTROL | Server to modem | DTR/RTS state where present |
| STATUS | Modem to server | DSR/carrier/ring/CTS information where applicable |
| BREAK | Both, as supported | Explicit break start/end or duration |
| RESET/DETACH | Both | Lifecycle and connection-state synchronization |

Map only the signals the 90TL firmware and board actually expose. The
physical 90TL's documented DSR/DTR semantics must guide the mapping; generic
PC modem-control assumptions may differ. Preserve binary bytes and bounded
backpressure. Do not consume XON/XOFF in a terminal/PTY driver when those
bytes must reach the guest or modem.

The protocol describes DTE events, not audio samples. Modem modulation or
interoperability defects remain outside the DECserver simulator's scope.

## Time and observability

Use one guest-time event scheduler for UART completion, timer/TPU events,
watchdog and Ethernet interrupts. Pace execution against host time during
live networking/modem use. Provide bounded execution and tracing for offline
bring-up, without assuming the CPU core's instruction timing is a perfect
physical clock.

Record CPU faults with PC/registers and recent instructions; log MMIO,
DMA descriptors, interrupt transitions and serial control changes selectively.
Offer packet capture and per-port byte traces. Keep original firmware bytes
unchanged; any temporary bootstrap substitutions must be named and reported.

## Staged delivery and acceptance

| Stage | Deliverable | Acceptance evidence |
|---|---|---|
| 1 | CPU, RAM, loader and startup traces | Execute recovered startup with explicit handoff; resolve faults and required device reads without blanket dummy responses |
| 2 | One serial console, SIM/TPU minimum | Original firmware displays its banner and accepts Local commands through the emulated UART |
| 3 | LANCE and isolated TAP network | Initialization DMA/IDON works; original firmware exchanges real frames; a LAT session and Telnet session work |
| 4 | Eight ports and durable configuration | Concurrent binary data streams on all ports; flow control/BREAK/modem transitions; DEFINE settings survive simulated power cycle |
| 5 | Virtual modem and operational service | Dial/answer/disconnect through a working modem backend; remote session carries data; clean restart and reconnect behavior |
| 6 | Guest-visible flash, if required | Firmware recognizes supported flash, updates it and local boot uses the stored image with defined persistence semantics |

Where possible compare commands, counters, packets and port behavior against
the existing physical 90TL. Test the board boundaries and end-to-end behavior;
avoid tests that merely repeat register constants without exercising effects.

The first useful milestone is **an original-firmware Local prompt from one
emulated UART**. The next is **a real LAT connection over TAP**. Those prove
the CPU/peripheral and network boundaries before investing in complete modem
integration or detailed flash behavior.

## Open decisions requiring evidence

Exact CPU derivative and memory aliases; ROM handoff and any ROM callbacks;
UART variant/optimized receive accesses; TPU service semantics; permanent
configuration storage; precise modem-pin mapping; and boot diagnostic
requirements. The Ethernet programming interface is sufficiently identified
to start from an existing LANCE model.
