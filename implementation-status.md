# Implementation status — first firmware execution

2026-10-31. The executable builds and MNENG3 executes under MAME CPU32
with 4 MiB RAM. Startup is incomplete: no Local prompt, network backend or
external modem endpoint is available.

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
configuration-record bounds errors. The latest bounds check rejects offset
`0x0e00` in record 22 (declared size `0x0c00`). Firmware error code is 0x543.
The error handler originally jumped through a zero inherited boot callback.
The synthetic handoff now supplies a diagnostic sentinel callback at 0x1400
through field 0x078051a2. Verified output: code `0543`, caller `0787260e`,
parameter `00000e00`, report SP `079dbdf0`.
Both a fresh FF store and an isolated zero-filled store reproduce the bounds
error, so changing the initial byte pattern does not resolve it. No Local
prompt yet; the configuration-record size/offset disagreement remains open.

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
