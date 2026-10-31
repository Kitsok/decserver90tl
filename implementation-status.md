# Implementation status — first firmware execution

2026-10-31. The executable builds and MNENG3 executes under MAME CPU32
with 4 MiB RAM. With the opt-in ROM alignment assist, startup passes the
previous 0x543 failure, initializes all four DUARTs and reaches the scheduler.
With one extra RAM wait cycle, the 60-second bounded run also avoids the
scheduler idle error. The diagnostic login sequence now reaches Local on
port 1. External serial/network endpoints are still absent, and firmware
reports server-parameter warnings with defaults in effect.

## Verified

- Build output: `build/mame-ds90tl`; MAME machine validation passes.
- ROM audit passes: `romset ds90tl is good`.
- Original firmware SHA-256 remains unchanged.
- Startup executes the internal-register initialization table, waits for the
  provisional TPU request completion, sets VBR to `0x0783b6ac`, services the
  watchdog and reaches configuration-store checksum routines.
- Python wrappers compile and `git diff --check` passes.

## Execution findings

The initial run stops on a byte read at `0x101238` in the checksum loop at
`0x07872152`. The access callback reports PC `0x07872154` (the next
instruction). That routine constructs its address as `0x100c00 + offset`.
Nearby routines compare storage bytes against RAM copies and prepare writes.
This strongly suggests the configuration-store interface. The physical
capacity and actual write protocol remain unconfirmed.

An erased 8 KiB window at `0x100000` advanced execution until a read at
`0x102000`. The provisional window is now 64 KiB and file-backed through
MAME NVRAM, saved under `run/nvram/ds90tl/configram`. It survives resets and
invocations; it starts FF only if the backing file is absent. Actual storage
technology/capacity, write-enable gating and programming delays are unresolved.

The first illegal instruction at `0x079423c2` was a bounds assertion:
startup used the file-header word `0x1c00` as a port mask, selected port 12,
and the lookup routine accepts only 0..7. The handoff initially used `0x00ff`, but follow-up showed this is a
diagnostic/inhibit mask, not a presence mask. Current handoff clears both
`0x0780500e` and `0x0780501e` to report healthy ports.

The six-byte reader at `0x079409e2` reads `0x200000..0x200005`. The simulator
supplies synthetic locally administered MAC `02:90:00:00:00:01` there.
An earlier startup probe also reads `0x200000`; its side effects are unknown.

Boot metadata flags 19..21 at `0x07805016` select three firmware defaults.
The experimental handoff requests those defaults until boot-ROM metadata
validation is reproduced. This is an explicit bring-up substitution, not
proof of the original ROM handoff. It may overwrite metadata on each boot.

The firmware has run for 10 simulated seconds without an exception while
writing configuration bytes. The file contained 17,424 non-FF bytes afterward.
A longer run, and then the metadata-default experiment, reached further
configuration-record bounds errors. The earlier bounds check rejected offset
`0x0e00` in record 22 (declared size `0x0c00`). Firmware error code is 0x543.
The error handler originally jumped through a zero inherited boot callback.
The synthetic handoff now supplies a diagnostic sentinel callback at 0x1400
through field 0x078051a2. Verified output: code `0543`, caller `0787260e`,
parameter `00000e00`, report SP `079dbdf0`.
Both a fresh FF store and an isolated zero-filled store reproduce the bounds
error, so changing the initial byte pattern does not resolve it. The opt-in alignment assist now avoids this bounds failure, demonstrating
that silently aligned CPU accesses corrupted this path. No Local prompt yet.

Execution logs are preserved in `analysis/mneng3-*.log`, including the port-mask
assertion, identity-read stop, persistent-store runs and metadata experiments.
A MAME status 0 for a bounded run only establishes that its time limit expired,
not that DECserver startup completed.

## Remaining provisional behavior

Clocks, boot handoff, address decoding, UART wiring and board selection need
validation. SIM/QSM/TPU behavior is incomplete; the TPU completion timer only
clears requests. Synthetic inherited exception vectors provide diagnostic
sentinels. Network and modem integration follow a working firmware startup.

## Build notes

The resumed build exposed an incomplete cached memory-dispatch object from
the previous forced pause. Rebuilding that object fixed linking. The wrapper
now copies MAME's actual `ds90tl` output name. ROM staging uses lowercase
`mneng3.sys`, as required by MAME validation; the source image retains its
original repository filename.

Only the pinned MAME checkout/cache and build lock remain in `.deps/`.
The earlier paused checkpoint is recorded in
`analysis/build-paused-2026-10-31.log`. No host networking was changed.

## Follow-up: alignment and boot-ROM search

A diagnostic guard now catches an odd-address CPU word read at 0x079dbed5,
PC 0x0788667c, before the earlier bounds failure. MAME CPU32's aligned
16-bit accessor otherwise reads the neighboring word. Original CPU32
address-error handling, and whether the inherited ROM supplies an alignment
service, remain unresolved. Do not attribute the earlier failure solely to
missing persistent records. See `boot-rom-search.md` for evidence and the
related 90M+ MNBOOT.SYS candidate, which is not a verified 90TL ROM.
MAC-window evidence is in `mac-window.md`. An opt-in alignment assist now implements unaligned word/longword reads
and writes at CPU memory callbacks; it substitutes data-transfer semantics
without reproducing ROM exception frames/timing. Default diagnostics stop
on odd-address word/longword transfers.

## Follow-up: scheduler clock

With alignment assistance, startup reaches UART initialization and scheduler
idle. An idle-loop counter then reports firmware error 0x298. The board-clock
substitution asserts level 6 and acknowledges it on a read of 0x200000,
matching the firmware interrupt path. TPU channel-14 priority bits gate the
source. At 512 incoming pulses/second, the guest time counter ran about 16
times too slowly; at 8192 pulses/second, it advances near simulated elapsed
time. Thus the ISR includes a software pulse divider. With zero extra RAM wait cycles the idle error still occurs, so correct
average guest time alone is insufficient. The wait-cycle experiment below
provides the current stable checkpoint. Clock-source hardware, CPU instruction-cycle
accuracy and external-memory wait states need further investigation.

CPU clock is now inferred as 14,680,064 Hz from SYNCR=0x9b00, assuming a
32768 Hz reference: 32768 * 4 * (27+1) * 2^(2*1+0). This is not a measured
crystal frequency. The earlier 16 MHz setting was provisional.

## Stable assisted checkpoint and timing experiment

Command verified with the current executable:

```sh
python3 tools/run_mneng3.py --seconds 60 --rom-alignment-assist --ram-wait-cycles 1 --nvram-directory run/nvram-zero-experiment
```

Both 30- and 60-second assisted runs finish with MAME status 0, continuing
scheduler/clock execution and unchanged firmware hash. Logs:
`analysis/mneng3-ram-wait1-30s.log` and
`analysis/mneng3-ram-wait1-60s.log`. This is not evidence of a Local prompt.
A fresh all-FF store also completed a 30-second assisted run, still in
configuration initialization; it did not reproduce 0x543.

Without added waits, the fixed idle loop consumed 159295 cycles, about
10.851 ms at 14,680,064 Hz. A 10 ms periodic deadline sampled on roughly
1.953 ms ticks can take about 11.719 ms to service. Adding one CPU cycle
per 16-bit external RAM transfer, including instruction fetches, avoids
the observed timeout while retaining the firmware checks. This demonstrates
timing sensitivity; it does not identify the real RAM wait count. The option
is explicit and defaults to zero. No idle counter or bounds checks are patched.

Default strict-mode control now stops at the earlier odd longword write
PC 0x078ed000, address 0x0799f21f. The opt-in alignment service handles that
operation and later odd reads/writes. The separate living runtime map is
`firmware-organization.md`; serial IRQ details collected so far are recorded
there. UART interrupt integration is next, after committing this checkpoint.

## UART receive checkpoint

A diagnostic mapping supplies TPU CISR receive-ready bits 0..7 and combined
DUART interrupt bits 8..11, with clear-on-zero writes. The clock ISR polls
these signals; electrical routing and TPU edge/capture behavior remain
unmodeled. A paced FIFO-injection probe is opt-in.

With the old port-diagnostic handoff, probes remained unread and the UART
stayed at CSR/MR reset settings. Clearing the header's diagnostic fields
permits normal UART setup. In the verified port-1 run, CSR=0xbb, MR1=0x13,
MR2=0x07 and baud=9600; all three injected CR bytes are read by the original
firmware at PC 0xfffff2a0. The 30-second run finishes normally. This is a
functional receive-path result, not serial-wire or modem emulation. An initial
TX CR is observed; no completed prompt yet. Port 8 likewise consumes all three CRs. Its transmit holding-register trace
contains the DS90TL V2.4 banner and `Enter username>` prompt. The port-1
trace contains only an initial CR; transmit behavior differs between channels
and is the next investigation. There is no external endpoint or wire capture.


Receive checkpoint evidence: `analysis/mneng3-uart1-healthy-handoff-probe.log`
and `analysis/mneng3-uart8-healthy-handoff-probe.log`, with corresponding
`.tx.txt` holding-register transcripts. Both runs finish 30 simulated seconds
with status 0. The firmware file remains unchanged. Default diagnostics,
configuration validation, ROM audit, Python compilation and whitespace checks
pass. Commit this checkpoint before investigating transmit asymmetry.

## UART transmit checkpoint

The port-1 asymmetry is resolved by the pinned MC68681-family dependency
patch. An ACR refresh of unchanged baud rates had reset active serial shift
registers/timers and stalled TX-ready. Rates now update only when changed.
Controls on ports 2 and 3 emitted the same username banner as port 8;
port 1 now does so as well. See `patches/README.md` and
`analysis/mneng3-uart1-tx-rate-fix.log` plus its `.tx.txt` transcript.
The patched port-1 probe exits 0 after 30 simulated seconds and consumes
all three diagnostic CRs. The next milestone is supplying a username and
reaching Local through a reproducible input path. This fix is committed
before that next investigation; no external serial endpoint is claimed.

## Local prompt checkpoint

Original MNENG3 accepts username SIMULATOR and reaches Local on port 1
with alignment assistance and one RAM wait cycle. This was reproduced from
an absent NVRAM directory using a 60-second initialization run followed by
a 50-second login run. Both exit 0. Diagnostic input is three CRs followed
by SIMULATOR and CR, starting at second 30, one byte per second.

The bounded probe accepts 1..128 hex-encoded bytes and applies backpressure
when its FIFO is nonempty. Malformed, oversized and empty inputs are rejected
before simulator launch. It continues to bypass real serial framing and
modem signals. All source/image hashes, commands, evidence paths and limits
are in `analysis/local-prompt-verification.json`.

The firmware emits warnings 602/603 for server parameters and uses defaults.
That is unresolved and is not hidden by the successful prompt test. No host
serial endpoint or network backend is attached. Commit this milestone before
investigating the parameter warnings or external serial integration.

## Interactive host serial transport

`run.sh --interactive` now exposes all eight UART ports as independent local
PTYs and runs continuously, with host pacing and live trace logging. The driver
polls host input every simulated millisecond, delivers a byte when the channel's
RX FIFO is empty, and forwards transmit-register writes to the corresponding
PTY. PTYs stay open across terminal disconnects. SIGINT/SIGTERM in interactive
mode requests normal simulator shutdown and NVRAM saving. This extends the
existing diagnostic byte-level UART model; modem signals and serial wire timing
remain unimplemented. See BUILD.md for terminal connection commands.

## DTR/DSR and software flow control

All eight interfaces now expose DSR input and DTR output via a local control
socket alongside their data PTYs. The board translates recovered 2692-compatible
DTR commands; the DUART model holds transmit bytes while DSR is negated when
configured, and automatic receive throttling drops DTR at FIFO full. Firmware
XOFF/XON was verified through the PTY. See [modem-lines.md](modem-lines.md) and
the recorded firmware/component tests. Physical pin routing remains provisional;
PTY modem ioctls, input framing and modem emulator adapters remain unimplemented.

## Ethernet TAP milestone

The existing AM7990 model now attaches to an explicitly selected, user-prepared
TAP using MAME's taptun provider. The runner requires an UP bridged TAP, keeps
offline mode explicit, paces networked runs, and records full packet PCAPs.
`network.sh` prepares an isolated bridge/TAP without modifying existing
interfaces. Host MAME configuration is isolated per run so it cannot silently
restore an old interface selection. Guest NVRAM selection remains persistent.

Verified with MNENG3/4 MiB and a copied NVRAM store: ARP, three ICMP echo
replies, TCP port 23 connection/Telnet negotiation and outgoing LAT multicast.
An independent register loopback fixture verified DMA byte order, descriptor
ownership and interrupt cause/acknowledgement. Full Telnet login and inbound
LAT sessions remain untested. See [network.md](network.md) and the two recorded
Ethernet verification reports for scope and commands.
