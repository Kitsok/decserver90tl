# Performance investigation

2026-11-01. Static review of the pinned MAME and project sources; no changes
to the running build on nanovax. Findings below distinguish observed behavior
from proposed optimizations. No profiler samples have been collected yet.

## Measurements and their limits

On nanovax (Cortex-A53), a three-simulated-second offline run from erased
configuration took 13.561 seconds with tracing disabled, and 13.914 seconds
with tracing enabled: 0.221x and 0.216x end-to-end speed. These numbers include
process startup and shutdown. CPU temperature and frequency differed between
runs; the approximately 2.6% elapsed-time difference is not an isolated measure
of logging cost. Both runs exited normally. Earlier network-attached startup
also progressed at about 0.22x, with one CPU core saturated.

Those tests used fresh configuration stores. They do not establish normal
idle-server or active-modem speed. The first network setup attempt stopped
before console login; no IP configuration commands were issued.

The tests used /tmp, which was subsequently verified to be on nanovax's
flash-backed overlay root, not tmpfs. Future short runtime/profiling tests
should use /dev/shm (475 MiB capacity when checked), including NVRAM state.

## Ranked suspects

### 1. Configuration initialization executes a firmware programming delay

The repeatedly sampled PC, 0x07940c2c, disassembles as:

```text
07940c22  movem.l d4, -(a7)
07940c26  move.l  #$960, d4
07940c2c  dbra    d4, $07940c2c
07940c30  movem.l (a7)+, d4
07940c34  rts
```

This is 2,401 DBRA executions per invocation, used between storage programming
operations (already identified in firmware-organization.md). The interpreted
CPU pays instruction dispatch and fetch overhead on each iteration, although
the loop performs no useful host work. This explains what the sampled startup
PC is doing; it does not yet establish its percentage of total host CPU time.

First compare a completed, initialized store against erased startup. If this
loop remains dominant, a specialized acceleration could batch iterations
while charging the same guest cycles. It must preserve interrupt boundaries,
the loop counter, condition codes, final branch timing and scheduler behavior.
Skipping the loop or reducing its guest-time cost would invalidate timing.
The checksum/scheduler idle loop at 0x07941610 is a different routine with
memory side effects and must not be treated as an equivalent no-op delay.

### 2. Nested memory callbacks on the instruction-fetch path

ds90_cpu_device::device_start wraps all seven Musashi memory callbacks,
including m_readimm16. They are std::function objects; each wrapper captures
the previous std::function and calls it again after wait/alignment checks.
Consequently instruction words pass through two callback layers, plus address
masking/range checks and adjust_icount for RAM transfers. Data accesses also
take alignment branches. Even with zero configured wait cycles, wrappers
remain installed. This affects millions of accesses, unlike sparse log writes.

Possible improvement: specialize callbacks at initialization for the chosen
alignment/wait settings and avoid nested callbacks using the appropriate
MAME accessors. Validate opcode-space versus data-space access, endianness,
odd-address handling and wait-cycle accounting before substituting accessors.
The existing wait count is a firmware timing correction, not a speed knob.

### 3. Build explicitly uses OPTIMIZE=1

tools/build_mame.py passes OPTIMIZE=1; pinned scripts/genie.lua translates
this to -O1. The CPU interpreter and memory dispatch contain large inline
paths for which stronger optimization may matter. This is an obvious build
experiment, but no speedup has been measured and -O2/-O3 may increase compile
memory and binary size. Test one optimized build on dev after profiling;
do not modify the active nanovax build. Removing frontend files reduces build
work but does not remove interpreter or memory-access costs at runtime.

### 4. Timer and interrupt workload

The inferred board clock generates 8,192 level-6 pulses per guest second.
This slices CPU execution and repeatedly invokes the guest ISR. There is also
a 1 kHz observer even with diagnostic output disabled. The observer still
reads PC/SP and checks fatal-report paths, so it is not merely a logger.
Configuration persistence polls at 20 Hz and writes only dirty settled state;
it is not fsyncing on every emulated memory write.

Profile scheduler/ISR costs before changing these. Reducing the 8,192 Hz rate
alone breaks the guest clock, whose ISR divides pulses by approximately 16.
Any aggregation must preserve the firmware's serial/clock semantics. Observer
frequency could be revisited separately while retaining fatal-error handling.

### 5. Serial host polling and per-byte I/O

With serial endpoints active, a 1 kHz poll scans eight ports, attempts one
nonblocking read per eligible port, and drains output with one write per byte.
Serialsim additionally issues TIOCMGET per port per tick; DTR writes occur only
when the value changes. These syscalls can matter with seven modems. Batching
I/O and polling readiness are candidates, with FIFO and flow-control limits
preserved. The offline benchmark used neither interactive PTYs nor serialsim,
so this cannot explain its low baseline speed.

## Next measurement

After the user's build finishes, profile a short trace-disabled run from
/dev/shm with the CPU frequency/temperature recorded. Identify the hot symbols
before implementing changes. Compare erased initialization and a completed
configuration boot; avoid claiming modem-service capacity from startup alone.
perf and gdb are now installed. Keep captures in RAM and leave existing DEC
and telephony services running. Do not compare results during compilation.

## Implemented candidates, pending build and firmware validation

The CPU adapter now installs callbacks that call the pinned CPU32 init16
accessors directly instead of capturing and invoking the previous callback.
Instruction fetches retain m_oprogram16's cache; data accesses retain
m_program16, including the original byte-write mask. Odd accesses retain the
alignment assist, and transfer wait-cycle charges are unchanged. Idle-budget
instrumentation is also gated before state inspection when tracing is disabled.

The programming-delay fast path runs only on a steady-state opcode fetch at
0x07940c2c, with prefetch at PC+4, the expected DBRA/displacement words and a
counter within the known routine's range. It does not run during debugging,
CPU tracing, reset/stop, address/bus error or an eligible pending interrupt.
For each batched taken iteration it charges the CPU32 cycle-table cost plus
the taken-branch adjustment and three instruction-fetch RAM waits. The three
fetches follow pinned m68ki_read_imm_16: opcode miss, displacement prefetch,
then PC+4 prefetch while consuming the displacement. There is no CPU32 cache
hit optimization in m68ki_ic_readimm16 that would change this fetch count.

Batching leaves a positive current-slice cycle budget and at least one normal
instruction for the core. It never batches the terminal DBRA iteration: the
core retains its different cycle cost, prefetch state and loop exit. D4's
upper word and condition codes are preserved. No instruction bytes are patched
and guest time is not shortened. `--no-delay-acceleration` disables batching
independently of tracing; direct binary launches use DS90_DELAY_ACCEL=0.

An offline differential model compares ordinary DBRA/prefetch execution with
batching over counter, budget, upper-register-word and wait-cycle boundaries;
it also checks the original firmware instruction bytes. These checks passed,
but do not compile or exercise the C++ adapter. No new performance result or
firmware validation is claimed until the user rebuilds and target tests run.

## First native execution comparison

The user successfully compiled bd54036 on dev with GCC 13.3.0 for x86_64.
Two three-simulated-second offline runs used separate erased stores and
tracing enabled so progress records could be compared. Acceleration enabled
took 3.613 wall seconds; ordinary delay interpretation took 3.360 seconds.
Both exited with status zero. All emitted progress records were identical,
as were saved configuration-file hashes. At 3,000 ms both reported PC
0x07940c2c, SP 0x079dbf34, SR 0x2500, 24,552 clock ticks and guest_us 0x00290219.
Artifacts are on dev under /tmp/ds90-delay-ab-as3y7u08.

This supports sampled timing/state equivalence only; it does not establish
complete architectural-state equivalence or a completed configuration boot.
It shows no speed gain, and the enabled startup flag does not prove that
iterations were actually batched. Check the fast-path guards and instruction
budget with a debugger before another optimization or AArch64 rebuild. GDB
was absent on dev when checked; installation was requested from the user.

## Debugger finding: DUART timer activity prevents batching

After GDB was installed on dev, the existing bd54036 executable was examined
without rebuilding. Release type information was incomplete for the Musashi
base class; field offsets were derived from this executable's disassembly,
not assumed portable between builds or architectures.

The fast-path function is called, and its steady-state guards can pass. In
twelve consecutive entries, however, its cycle budgets were -1 (initial
prefetch), then 2, 3, 4, 5, 1, 1, 1, 1, 2, 3, 4. The counter decremented
normally from 0x95f to 0x955; interrupt level, trace and debugger flags were
zero. A stop at the batch update confirmed iterations=0 with cost=7 cycles.
Thus the short comparison did not demonstrate useful batching: these slices
are shorter than one taken iteration. Changing or ignoring slice boundaries
would hide the problem by violating the intended timing guarantee.

The existing trace identifies a much stronger performance suspect than the
8,192 Hz board clock: firmware programs each DUART ACR to 0xe0 and its counter
preset to 2 (CTUR=0, CTLR=2). Pinned get_ct_rate selects the direct 3,686,400 Hz
clock for this mode. duart_timer_callback runs every two clocks, toggles its
half-period and reschedules itself: 1,843,200 callbacks per chip per guest
second, or 7,372,800 across four chips once configured. These event deadlines
are consistent with the tiny observed CPU budgets.

The sampled firmware settings select OPCR=0x80, channel CSR=0xcc and IMR=0x11:
the timer is not routed to OP3, serial TX/RX use fixed baud rates rather than
counter output (selector 0xd), and counter-ready interrupts are masked. The
callbacks can still latch ISR counter-ready, and software can read the timer
count or change routing/masks later. Therefore simply disabling the timer or
changing its rate is not a correct general fix.

Next candidate: lazy evaluation/coalescing of unobserved counter half-periods,
retaining readable count, phase, ready-latch timing, interrupt behavior and
reactivation when a serial/output consumer is selected. This needs a focused
DUART model change and validation before another performance build. Debugger
artifacts are on dev under /tmp/ds90-gdb-guards-sw2e9zjv and
/tmp/ds90-gdb-budget-yp8xqtii. A separate attempt to wait for a nonzero batch
was bounded at 30 wall seconds; no timing measurements use debugger runs.

## Lazy DUART implementation ready for rebuild

The project now supplies an opt-in MAME patch that suppresses scheduler
callbacks for masked, unconsumed internal counter half-periods. DECserver's
four fixed-clock MC68681 instances opt in. Timer-mode register accesses
synchronize the deferred phase and ready latch; count reads use the retained
next-edge deadline. Register writes synchronize under the old configuration
before changing the preset/source/routing/mask. Enabling any edge consumer
restores the scheduled callback at the original next deadline. Counter mode,
external sources and four-channel variants retain ordinary scheduling.

The initial pending edge keeps its previous deadline even when presets or
source selection change; subsequent reloads use the new period. Long gaps
are handled in bounded u32-sized batches. Save states retain the lazy flag
and next-edge time. An explicit start resets phase/deadline; clearing ready
in timer mode does not stop its progression. No clock frequency is reduced.

Four offline differential model tests cover boundaries, latch clearing,
preset/source changes, restarts, consumer/IRQ reactivation, state restoration
and long gaps. The new patch applies to the pinned source alongside the
existing active-serial correction, and both reverse checks succeed afterward.
These checks are not native C++ compilation or a firmware/serial regression.

After rebuilding on dev, compare short erased-store runs with the default
settings and with `--precise-duart-timers`. Use `--trace` only when checking
guest timing/state records; use the default disabled trace for speed. Then
validate an initialized boot and console before building the AArch64 bundle.
Keep the programming-delay acceleration independently selectable with
`--no-delay-acceleration` to isolate its benefit after timer coalescing.
