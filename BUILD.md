# MNENG3 / 4 MiB bring-up build

The machine is an experimental MAME driver, not yet a working terminal
server. It uses MAME's CPU32, Am7990 and MC68681 models. Board clocks,
boot handoff, some address decoding and TPU behavior remain provisional.

## Prerequisites

Linux, GCC with C++ support, Make, Python 3, Git and these system development
packages (Ubuntu/Debian names):

```sh
sudo apt-get install pkg-config libsdl2-dev libsdl2-ttf-dev libfontconfig-dev libegl-dev
```

Do system package installation explicitly. The build script does not install
packages, unpack a local sysroot, or modify the host network configuration.
MAME's build consumes substantial disk space and several minutes on its
first invocation, even with one machine selected.

## Pinned dependency

Run in the repository root:

```sh
mkdir -p .deps/mame
git -C .deps/mame init
git -C .deps/mame remote add origin https://github.com/mamedev/mame.git
git -C .deps/mame fetch --depth 1 origin 2692d09218b67df92b9eb26b7c0c0cc04ca4c72e
git -C .deps/mame checkout --detach FETCH_HEAD
python3 tools/build_mame.py -j 2
```

The script verifies `mame-revision.txt`, copies the driver into the ignored
checkout and registers it in MAME's driver list. It also restricts the
M680X0 group's build file list to the CPU32/Musashi engine and common code,
omitting unrelated generated 68000/68008 engines. The upstream CPU implementation code is unchanged; the board-specific
CPU adapter provides the documented alignment/timing substitutions. Local
MAME device corrections in `patches/mame-*.patch` are applied reproducibly;
see `patches/README.md`. It builds the `ds90tl` subtarget and copies the result to
`build/mame-ds90tl`. Source and outputs in `.deps/`, `build/` and `run/`
are ignored by this repository.

## Bounded offline run

```sh
python3 tools/run_mneng3.py --seconds 1
# Explicitly enable the provisional ROM alignment-service substitute:
python3 tools/run_mneng3.py --seconds 60 --rom-alignment-assist --ram-wait-cycles 1
```

The wrapper verifies the original MNENG3 hash and uses SDL dummy drivers and
MAME's bounded benchmark mode. No bridge or modem backend is attached. The
log is `run/bringup.log`. A fatal unsupported-access report is currently useful
evidence, rather than proof of a working boot. The wrapper preserves MAME's
exit status and reports whether the firmware file changed.

The assisted command above completed a 60-second run with the current
provisional board model. One extra RAM wait cycle per 16-bit transfer avoids
the observed scheduler idle timeout; this setting is experimental, not a
measured hardware value. Default wait cycles remain zero. For an independent
persistent-store experiment, add `--nvram-directory run/nvram-new` using a
new directory. The no-input run alone does not establish a Local prompt;
use the login recipe below to exercise that milestone.

## Explicit experimental choices

- CPU clock inferred as 14,680,064 Hz from SYNCR=0x9b00 and an assumed
  32,768 Hz reference crystal; actual reference is unconfirmed.
- Exactly 4 MiB external RAM, tentatively at physical `0x800000..0xbfffff`.
- Provisional 24-bit program-space decode.
- Image copied unchanged to RAM offset `0x5000`.
- Synthetic reset vectors transfer to the recovered MNENG3 startup at
  `0x078713f8`, with initial SP `0x07bff000` and VBR zero.
- The handoff memory-size field at `0x078051b6` is set to 4 MiB. This is a
  RAM handoff write, not a modification of the firmware file.
- Metadata default flags 19..21 at `0x07805016` are set as a temporary
  substitute for boot-ROM validation of board configuration records.
- Port diagnostic fields at `0x0780500e` (long) and `0x0780501e` (word)
  are cleared to report healthy ports. The earlier `0x00ff` presence-mask
  interpretation was incorrect and prevented normal UART setup.
- Synthetic MAC `02:90:00:00:00:01` is read at `0x200000..0x200005`.
- Inherited exception vectors target identifiable sentinel loops. The ROM
  fatal-report callback at handoff field `0x078051a2` targets another sentinel
  that prints firmware error code, caller and parameter.
- Unaligned data transfers stop by default. `--rom-alignment-assist` enables
  word/longword transfers as a substitute for the inherited ROM exception
  service; it does not emulate exception frames or timing.
- A provisional 8,192 Hz board interrupt source drives level 6 while TPU
  channel 14 has a nonzero priority. Reading the identity base acknowledges it.
  The ISR divides pulses to approximately 512 guest clock updates per second.
  The physical clock source and precise timing are still unresolved.
- SIM/QSM/TPU registers are traced. TPU host requests provisionally complete
  after a scheduled delay; TPU function semantics are not implemented.
- A provisional 64 KiB configuration-store window at `0x100000` starts erased
  when no backing file exists. MAME saves it to `run/nvram/ds90tl/configram`;
  it survives resets and invocations. Capacity and programming behavior remain
  unconfirmed. Remove or move that file while the simulator is stopped to
  repeat an erased-store boot.
- Unknown external accesses stop the experiment with a PC/address report.
- UART writes are observed at the transmit holding registers; this does not
  yet establish completed transmission or an interactive serial endpoint.

The original firmware now reaches `Local>` through a diagnostic FIFO input
sequence, with the explicit substitutions above. It is not yet connected to
a host serial endpoint, and hardware/ROM fidelity remains incomplete.

## Diagnostic receive probe

```sh
python3 tools/run_mneng3.py --seconds 30 --rom-alignment-assist --ram-wait-cycles 1 --uart-probe-port 1 --nvram-directory run/nvram-uart1-fresh-20261031
```

Use a store initialized by firmware; a fresh store may spend most of its
first 60-second run initializing configuration. `--uart-probe-at` selects
when the probe starts (default 20 simulated seconds). The probe places three
CR bytes, one second apart, directly into the selected receive FIFO. Port 0
disables it. This bypasses receiver enable, baud sampling, parity/framing and
modem signals; it is an ISR/register-path test, not a serial-wire endpoint.

The provisional TPU status adapter exposes receive-ready bits 0..7 and
combined DUART interrupt bits 8..11, and implements clear-on-zero status
writes. Exact pin routing, capture/edge behavior and TPU microcode remain
unmodeled. Observe `FIFO-INJECT`, `SERIAL-STATUS`, and `UART-RX` log entries.

## Verified Local prompt recipe

Use an initially absent NVRAM directory for a fresh-store reproduction.
The first run allows firmware to initialize persistent records; the second
supplies three CRs, then SIMULATOR and CR, at one byte per simulated second.

```sh
python3 tools/run_mneng3.py --seconds 60 --rom-alignment-assist --ram-wait-cycles 1 --nvram-directory run/nvram-local-repro-20261031
python3 tools/run_mneng3.py --seconds 50 --rom-alignment-assist --ram-wait-cycles 1 --nvram-directory run/nvram-local-repro-20261031 --uart-probe-port 1 --uart-probe-at 30 --uart-probe-hex 0d0d0d53494d554c41544f520d
```

Both verified runs exit 0. Port-1 TX-register output includes
`Enter username> SIMULATOR` and `Local>`. The firmware also reports error
messages 602/603 for server parameters and defaults in effect. Their cause
is unresolved. Logs, a printable transcript and source hashes are preserved
in `analysis/local-prompt-verification.json` and the referenced files.

`--uart-probe-hex` accepts 1..128 bytes. The injector waits for an empty FIFO
before the next byte, and the run remains bounded even if input is not
consumed. This diagnostic bypasses serial framing, receiver-enable checks
and modem pins. It is not an interactive external serial interface.
