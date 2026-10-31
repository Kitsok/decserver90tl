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

MAME loads the file before starting firmware. Guest writes update the simulated
NVRAM in memory. The current backend writes the complete 65,536-byte memory
image to the host file during **normal simulator shutdown**, not on each
`DEFINE` or `CHANGE`. Ctrl-C in the interactive launcher requests normal MAME
exit and saving. Forced termination, a crash or power loss before that save can
lose changes made during the run. This is a limitation of the current host
persistence mechanism, not the intended durability of real NVRAM.

The file is a raw memory backing image, not JSON, an INI file or firmware.
MAME's implementation directly serializes the shared host-memory bytes and
explicitly notes unresolved width/endianness handling. Treat it as opaque;
firmware records and checksums make direct text editing inappropriate. The
original `firmware/MNENG3.SYS` is never rewritten by configuration commands.

Host MAME menu configuration (historically `run/cfg`, now isolated in a temporary
directory by the runner) is separate from guest settings. The `--tap` host
interface selection is a launcher option, not a guest database record.

## Backup and separate instances

Stop the instance normally before backing up or replacing its store, so the
host file contains the latest completed guest writes. Copying the entire chosen
NVRAM directory preserves its device file and layout. Starting another instance
with a different directory gives it independent persistent settings. Do not run
two instances using the same directory: the last shutdown can overwrite the
other instance's saved image. The simulator currently has no store-sharing lock.

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

The host file remained unchanged while the simulator was running, then changed
on normal exit. The saved image contained DS90SAVED, and after restart firmware
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
