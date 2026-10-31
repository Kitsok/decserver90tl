# Running and saved settings

## DEC command semantics

The DECserver 90TL Owner's Manual (DSRVE-OM-001), Management sections 3–21
and 3–24, distinguishes two databases:

| Command | Operational database in RAM | Permanent database in NVRAM |
|---|---|---|
| `SET` | Changes it | Does not change it |
| `DEFINE` | Does not change it | Changes it |
| `CHANGE` | Changes it | Changes it |
| `SHOW`, `MONITOR` | Displays it | — |
| `LIST` | — | Displays it |

These are original firmware semantics, not commands parsed by the simulator.
The manual is available in the parent project's
`docs/DECserver-90TL-Owners-Manual.pdf` and extracted `.txt`.

## Simulator storage

`run.sh` uses `run/my-decserver` as the default NVRAM directory. The resulting
host file is:

```text
/home/kostik/work/decnet/decserver90tl/run/my-decserver/ds90tl/configram
```

An alternative directory given to `run.sh`, or `--nvram-directory` given to the
Python runner, selects a separate store; the relative suffix remains
`ds90tl/configram`. The Python runner's own default is `run/nvram`, rather than
`run/my-decserver`. `run.sh` interprets relative paths from the repository root;
the Python runner resolves explicitly supplied relative paths from its caller's
working directory.

The driver maps a 64 KiB file-backed memory window at CPU physical addresses
`0x100000..0x10ffff`, shared as `configram`, with erased bytes initially 0xff.
Recovered firmware accesses configuration records through helpers relative to
`0x100c00`. Firmware manages the record layout, write queue and checksums itself;
its low-level byte writer is at `0x07940c00`. Exact physical storage technology
and capacity on the real board remain unconfirmed, despite the manual naming
the permanent store NVRAM.

The emulated memory device loads the file before firmware starts. Any changed
byte in the NVRAM window marks it dirty; no command handler is intercepted.
The device checks the MNENG3 pending-write queue at 0x0798fb20 and its pending
flag at 0x0798fa86, and checkpoints after both are idle and writes have been
quiet for at least **250 simulated milliseconds**. The check runs every 50 ms.
`DEFINE` and `CHANGE` therefore reach disk while the simulator is still running,
after firmware programming/checksum work completes. `SET` does not write NVRAM.
Other firmware NVRAM writes and initial factory provisioning are handled too.

Each checkpoint writes the complete 65,536-byte image to a unique temporary
file beside `configram`, syncs it, atomically renames it over `configram`, then
syncs the parent directory. Existing file permission bits are preserved; a new
store starts with mode 0600. The console prints `STORAGE checkpoint saved` only
after these steps complete. A crash before a new checkpoint retains the previous
completed image; the in-progress change can still be lost. Completed checkpoints
survive forced process termination without requiring a normal-exit save.

On a normal exit, completed dirty work is also saved without waiting for the
quiet interval. If firmware writes remain pending, the device retains the last
checkpoint and reports that pending work was not saved. There is no generic
MAME shutdown writer that can then overwrite it with partial data. The direct
MAME option `-nonvram_save` disables checkpoints and exit saving when explicitly
selected; the standard launcher enables persistence.

A stable `configram.lock` file supplies an advisory exclusive writer lock for
this build. A second writing instance using the same store fails before loading
or changing it. The lock is released by the OS even on SIGKILL; the empty lock
file intentionally remains. Checkpoint I/O failures are reported as fatal errors,
and malformed backing files are rejected without reinitializing or replacing
them. Old builds without this lock must be stopped before sharing their store
with a new build.

The file is a raw memory backing image, not JSON, an INI file or firmware.
The memory device retains the previous MAME format by serializing native shared
CPU-memory bytes. Cross-host width/endianness portability is not established.
Treat it as opaque;
firmware records and checksums make direct text editing inappropriate. The
original `firmware/MNENG3.SYS` is never rewritten by configuration commands.

Host MAME menu configuration (historically `run/cfg`, now isolated in a temporary
directory by the runner) is separate from guest settings. The `--tap` host
interface selection is a launcher option, not a guest database record.

## Backup and separate instances

After a checkpoint notice, the regular `configram` file can be backed up while
the instance runs: an atomic replacement never modifies the old inode in place.
A single-file copy therefore sees a completed checkpoint. The chosen NVRAM
directory also preserves the device-file layout. Stop the instance before
restoring/replacing its store, and use a different directory for an independent
instance. Two instances of this build cannot write the same store concurrently.

A backup of NVRAM does not preserve operational-only `SET` values. It also does
not replace the firmware image or host bridge setup.

## Verified behavior and corrected startup handoff

A two-boot experiment used a disposable copy of the previously initialized
MNENG3 store, without Ethernet. It logged in with factory privileged credentials
and used server names to distinguish the databases:

| Operation | Subsequent SHOW SERVER | Subsequent LIST SERVER |
|---|---|---|
| `SET SERVER NAME DS90VOL` | DS90VOL | Not queried in this step |
| `DEFINE SERVER NAME DS90DEFINED` | DS90VOL | DS90DEFINED |
| `CHANGE SERVER NAME DS90SAVED` | DS90SAVED | DS90SAVED |
| Clean exit and restart (fixed handoff) | DS90SAVED | DS90SAVED |

The original diagnostic, before runtime checkpoints were implemented, observed
the host file changing only on normal exit. The saved image contained DS90SAVED, and after restart firmware
could still read it through LIST. Thus persistence to the host file and loading
it back into the permanent database work for this tested value.

The earlier handoff forced header bits 19–21 to request fallback values for
three factory metadata groups. Firmware routine 0x079406de copies those values
but also sets bit 18, marking server parameters invalid. That overrides the
successful checksum of the saved server record and forces operational defaults.

The corrected model provisions only fully erased factory fields, using the same
fallback constants already embedded in MNENG3, and no longer forces those three
flags. Populated fields remain untouched. The firmware still validates server
checksums and rejects genuinely corrupt records; no checksum comparison or
warning has been suppressed. Factory identity remains synthetic pending exact
hardware identification.

The repeated two-boot test now restores DS90SAVED in both SHOW and LIST with no
-602/-603 warnings. Focused checks also verify a valid saved record, a deliberately
corrupt record, preserving populated metadata, and a genuinely erased store.
Other record types and every possible setting have not been exhaustively tested.

The diagnostic matches actual command prompts at the start of a line, so SHOW's
displayed `Prompt: Local>` setting cannot prematurely end a response.

See [analysis/settings-verification.json](analysis/settings-verification.json)
for before/after hashes, command responses and restart evidence. The raw backing
file is 65,536 bytes in this model. To repeat the diagnostic on an isolated copy:

```sh
python3 tools/verify_settings.py --nvram-seed run/my-decserver --assert-restored
python3 tools/verify_settings_handoff.py --nvram-seed run/my-decserver
```

The diagnostic uses the factory privileged password SYSTEM, never modifies the
seed, and writes `run/settings-write.log`, `run/settings-restart.log` and the
JSON report. `--assert-restored` makes the two-boot diagnostic fail if database
semantics or startup restoration regress. Without it, the tool records observations
including failures. A user-owned initialized seed with
other credentials needs a corresponding test adaptation.

## Likely real memory device

New firmware-layout inspection points to 32 KiB of useful physical storage,
with a parallel 28C256-class EEPROM the leading candidate. A compatible
battery-backed SRAM remains possible. The 64 KiB simulator file is deliberately
unchanged. See [nvram-device.md](nvram-device.md) for the capacity arithmetic,
write/polling evidence, datasheet comparisons and uncertainty.

## Runtime durability verification

`tools/verify_nvram_runtime.py` uses three boots and a copied initialized store.
It confirms that SET leaves the backing file unchanged, DEFINE checkpoints
before exit, DEFINE survives killing the MAME child with SIGKILL while the SET
value is discarded, CHANGE also checkpoints before SIGKILL, and the final
restart restores CHANGE in both SHOW and LIST without -602/-603. It also checks
file-mode preservation and leaves the original seed unchanged.

The separate `tools/verify_nvram_checkpoint.py` component fixture holds the CPU
in a RAM loop and independently checks each firmware queue guard, checkpoint
release when idle, rejecting a second writer, preserving the completed image
on a normal exit with pending writes, refusing malformed files and preserving
the old checkpoint on a permission-denied write failure. These are memory-device
checks, not claims that real firmware naturally exercised every failure case.

```sh
python3 tools/verify_nvram_runtime.py --nvram-seed run/my-decserver
python3 tools/verify_nvram_checkpoint.py --nvram-seed run/my-decserver
```

Results are in [analysis/nvram-runtime-verification.json](analysis/nvram-runtime-verification.json)
and [analysis/nvram-checkpoint-verification.json](analysis/nvram-checkpoint-verification.json).
The crash test removes only its own stale serial-control socket after killing
its MAME child, and runs entirely offline. The failure test should be run as a
normal user so the permission-denied scenario is meaningful.
