# Implementation status — first firmware execution

2026-10-31. The executable builds and MNENG3 executes under MAME CPU32
with 4 MiB RAM. With the opt-in ROM alignment assist, startup passes the
previous 0x543 failure, initializes all four DUARTs and reaches the scheduler.
With one extra RAM wait cycle, the 60-second bounded run also avoids the
scheduler idle error. Startup remains incomplete: no Local prompt, network
backend or external modem endpoint is available.

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
and the lookup routine accepts only 0..7. The synthetic handoff now writes
`0x00ff` to `0x0780501e` in guest RAM.

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
