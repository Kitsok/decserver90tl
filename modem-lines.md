# DECserver 90TL modem lines and flow control

## Connector capabilities

The 90TL has **DTR output and DSR input on each of eight ports**. Its modem
interface does not expose RTS, CTS, DCD or RI. DTR/DSR can serve either modem
control or hardware flow control; XON/XOFF is handled by the original firmware.
These conclusions come from the [DEC product description, SPD 38.71.04, pages
6–8](https://www.glaver.org/DECserver/Pre-DNAS%20DECserver%20Models%20and%20Firmware/DECserver%2090TL/Documentation/DS9C011_SPD.PDF)
and the owner's manual, section 3, “Specifying Flow Control”. A local copy of
the owner's manual exists in the parent project's `docs` directory.

The UART's internal pin names differ from connector names: its RTS output is
used for connector DTR, and its CTS-controlled transmitter implements DSR flow
control. The exact UART part and physical PCB routing are still unconfirmed.

## Recovered firmware mapping

Firmware bytes remain unchanged. See [selected disassembly](analysis/MNENG3.modem.asm).
Each block at `0x400000 + 0x20*n` contains channels A and B. Register bytes
occupy the high byte of the 16-bit bus, at even addresses.

| Function | Channel A | Channel B |
|---|---|---|
| Mode registers | block + 0x00 | block + 0x10 |
| Command register | block + 0x04 | block + 0x14 |
| Transmit/receive holding register | block + 0x06 | block + 0x16 |
| DSR status bit, shared input register at block + 0x1a | bit 0 | bit 2 |
| DTR output, shared output port | OP0 | OP1 |
| DTR assertion command | 0x80 | 0x80 |
| DTR negation command | 0x90 | 0x90 |

The tables at `0x079423c4` and `0x079423c8` contain masks `00 01 01` and
`00 10 04`. Initialization at `0x07942282` copies their third bytes to the
per-channel DSR masks at object + 0x141a. The routines at `0x07944318` and
`0x0794426e` read those masks from the shared input port; asserted DSR reads
as zero. `0x079442d4` writes 0x90 for logical output off, and 0x80 for on.
The fast input sampler at `0x07945300` accumulates shared input states.
The earlier suggestion that the nearby SIM GPIO table directly maps the eight
DTR lines is superseded by this command-register evidence.

These extra command codes match the [NXP SCC2692 datasheet, command register,
page 15](https://www.nxp.com/docs/en/data-sheet/SCC2692.pdf). The generic MAME
68681 implementation masks command bit 7, so it previously ignored 0x80 and
misinterpreted 0x90 as resetting the mode-register pointer. The board now
translates these commands into the appropriate output-port set/reset operation,
passing their low receiver/transmitter control bits to the existing model.
This establishes needed 2692-compatible behavior, not the exact installed IC.

## Simulator behavior

- DSR input defaults to asserted for an ordinary connected terminal. A modem
  backend must set the input explicitly, including its initial disconnected
  state; attaching or detaching a PTY does not change DSR automatically.
- The board drives active-low input bits and input-change latches/interrupts
  through the DUART APIs. Channel B's DSR is mirrored to IP1 for conventional
  CTS use and IP2 for the firmware's recovered status mask. This fan-out is a
  functional substitution; its physical realization has not been established.
- With MR2 bit 4 set, negated DSR prevents a holding-register byte from entering
  the transmit shift register. A character already started finishes normally.
  The held byte keeps TxRDY clear and resumes when DSR is asserted. Clearing
  the mode bit also releases a held byte; resetting the transmitter discards it.
- DTR follows the output latch. With MR1 bit 7 set, a full three-byte receive
  FIFO deasserts DTR; draining a slot restores it. Explicit command 0x90 keeps
  DTR deasserted even if the FIFO later drains. This covers the recovered
  firmware's DTR/DSR modes; automatic transmit-end RTS modes remain unmodeled.
- PTY output is now captured when a byte enters the transmit shift register,
  after gating, rather than on every CPU write to the holding register.
  `UART-THR` records CPU writes, `UART-TX` records bytes started, and `PTY-TX`
  records successful host delivery. The console reconstructs `UART-TX` text.
- XON/XOFF bytes pass unchanged through the transport. Firmware handles its
  configured input controls and emits receive throttling as needed. A peer
  modem/terminal must honor firmware-generated flow-control requests itself.
  No unconditional transport filter consumes 0x11/0x13 in binary sessions.

Host receive delivery remains assisted: it polls every simulated millisecond,
places one byte in the FIFO when a slot is free, and bypasses receiver-enable,
wire baud/framing and input error detection. It stops draining the host PTY
while the FIFO is full. It does not automatically gate peer input on DTR:
respecting DTR is the peer's responsibility. Modem emulator adapters themselves
are not implemented by this change.

## Host interface

An optional [serialsim backend](serialsim.md) carries bytes and modem signals
through a kernel pipe TTY instead of the PTY/control-socket combination below.
Select it per port with `--serialsim PORT=DEVICE`; it is independent of
interactive mode. Unmapped ports keep their existing behavior.

`./run.sh --interactive` exposes the eight data PTYs and prints the modem control
socket path. The default is `run/serial-control.sock`, with filesystem mode 0600.
It is a local Unix datagram socket. Normal shutdown removes it. An existing path
causes startup to fail without deleting it; for a stale socket after a crash,
remove the stale path after checking that its simulator has stopped. For another
instance use the Python runner's `--serial-control PATH` and a separate store/log.
Unix socket pathname length is limited by the host (108 bytes including NUL on
Linux).

Linux PTYs do not provide these modem lines through normal TIOCMGET/TIOCMSET
ioctls. Use the sideband interface while continuing to carry data through PTYs:

```sh
python3 tools/serial_control.py get all
python3 tools/serial_control.py get 1
python3 tools/serial_control.py set 1 dsr 0
python3 tools/serial_control.py set 1 dsr 1
```

`--socket PATH` selects another instance's socket. State replies include DTR,
DSR, flow-mode bits, raw MR1/MR2/SR and input pins, and the host output queue
length. DTR and modem mode are guest-controlled; host commands only set DSR.
Read state repeatedly to observe DTR changes. This version offers polling
snapshots, not a lossless signal-transition subscription.

For a backend, bind a private local Unix datagram client address and connect to
the printed socket. Send ASCII `GET 1` or `SET 1 DSR 0` (ports 1–8); each request
gets a JSON datagram reply. Invalid requests return an `error` object. Inputs
persist across client disconnects. RTS/CTS/DCD/RI requests are rejected rather
than pretending the 90TL exposes them. The helper's `ModemControl` class can also
be used from Python adapters. Requests are bounded to 16 per emulation tick.

Firmware example at `Local>`:

```text
SET PORT FLOW CONTROL DSR
```

Then lower DSR through the helper, type a command, and assert DSR again: output
should pause and resume. With default software flow control, Ctrl-S and Ctrl-Q
pause and resume output instead. For direct transport testing, turn off the
terminal client's own XON/XOFF interception so those bytes reach the firmware.

## Verification

The recorded [firmware test](analysis/modem-verification.json) uses a copied,
initialized configuration store, logs in through the PTY to `Local>`, verifies
per-port DSR isolation and input polarity on all eight ports, rejects invalid
requests, checks firmware XOFF/XON, selects DSR flow control, verifies held
TxRDY and resume, then checks normal shutdown and socket cleanup.

The separate [register component test](analysis/modem-register-verification.json)
uses a Lua fixture to stop guest execution in a private RAM loop and exercise
the register model. It verifies byte output on all eight PTYs, DSR gating and
resume, DTR commands, full-FIFO DTR throttling/recovery, transmission with flow
control disabled, and reset of a held byte. This is not a claim that the normal
firmware exercised all those states on every port.

```sh
python3 tools/verify_modem.py --nvram-seed run/my-decserver \
  --report analysis/modem-verification.json
python3 tools/verify_modem_registers.py \
  --report analysis/modem-register-verification.json
```

These checks use temporary stores and their own control sockets. Logs are
`run/modem-verification.log` and `run/modem-register-verification.log`. Both
reserve the lowest available PTY to avoid a reconnecting terminal client on a
previous simulator's port-1 path consuming test data. The tests require local
Unix socket access, which some execution sandboxes prohibit.
