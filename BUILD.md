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
omitting unrelated generated 68000/68008 engines. CPU implementation code is
unchanged. It builds the `ds90tl` subtarget and copies the result to
`build/mame-ds90tl`. Source and outputs in `.deps/`, `build/` and `run/`
are ignored by this repository.

## Bounded offline run

```sh
python3 tools/run_mneng3.py --seconds 1
```

The wrapper verifies the original MNENG3 hash and uses SDL dummy drivers and
MAME's bounded benchmark mode. No bridge or modem backend is attached. The
log is `run/bringup.log`. A fatal unsupported-access report is currently useful
evidence, rather than proof of a working boot. The wrapper preserves MAME's
exit status and reports whether the firmware file changed.

## Explicit experimental choices

- Exactly 4 MiB external RAM, tentatively at physical `0x800000..0xbfffff`.
- Provisional 24-bit program-space decode.
- Image copied unchanged to RAM offset `0x5000`.
- Synthetic reset vectors transfer to the recovered MNENG3 startup at
  `0x078713f8`, with initial SP `0x07bff000` and VBR zero.
- The handoff memory-size field at `0x078051b6` is set to 4 MiB. This is a
  RAM handoff write, not a modification of the firmware file.
- Inherited exception vectors target identifiable sentinel loops.
- SIM/QSM/TPU registers are traced. TPU host requests provisionally complete
  after a scheduled delay; TPU function semantics are not implemented.
- Unknown external accesses stop the experiment with a PC/address report.
- UART writes are observed at the transmit holding registers; this does not
  yet establish completed transmission or an interactive serial endpoint.

The first milestone remains a working original-firmware `Local>` prompt.
Until the unresolved handoff and board behavior are validated, these
experiments must not be described as a booted DECserver.
