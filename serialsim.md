# Serialsim serial-device backend

The optional per-port setting attaches an existing kernel serialsim pipe TTY
instead of creating a PTY for that port:

```sh
./run.sh --interactive --serialsim 2=/dev/ttyPipeA0
```

Courier uses the opposite end, selected either by its CLI
`--serialsim /dev/ttyPipeB0`, or `[modem] serialsim = /dev/ttyPipeB0` in its INI.
Other DECserver ports retain their PTYs in interactive mode, including management
port 1. Repeat the DECserver option with distinct port/device pairs for additional
modems. Device ownership is protected with advisory flock; permissions must
allow both emulators to access their respective ends.

Serialsim does not require interactive mode. A bounded example is:

```sh
python3 tools/run_mneng3.py --serialsim 2=/dev/ttyPipeA0 --seconds 10 \
  --rom-alignment-assist --ram-wait-cycles 1
```

Without `--interactive`, only explicitly mapped serialsim ports are opened, and
no PTYs or modem-control socket are created. With no explicit time limit, a
serialsim run continues until stopped. An attached external device selects
real-time pacing rather than an unpaced benchmark. Existing offline and PTY
defaults remain available. Inherited per-port backend environment settings are
cleared by the runner, so an ordinary invocation cannot attach one accidentally.

Each endpoint uses raw binary mode and a 115200-baud kernel transport. This
transport setting does not replace emulated UART configuration. The DECserver
publishes emulated DTR using TIOCMBIS/TIOCMBIC and reads physical host TIOCM_DSR
into the existing DUART DSR input. Automatic FIFO DTR throttling is included in
that output. Signal sampling uses the existing one-millisecond serial poll.

Courier reads the peer DTR using serialsim's remote-control ioctl and feeds its
existing firmware DTR pins. Its initial DSR policy is endpoint-ready while the
worker is attached; the exact firmware-driven ASIC DSR output remains unmodeled.
Courier drives its local host DTR as the null-modem source for the DECserver's
DSR. HUPCL handles descriptor closure, and normal shutdown explicitly clears it.
The emulated DTR/DSR directions remain distinct despite that host-side mapping.
The driver's simultaneous DCD mirror has no corresponding 90TL connector signal.

No separate control connection is used for mapped ports. In mixed PTY mode the
legacy socket remains for inspection and other ports, but SET DSR is rejected
on serialsim ports because the TTY owns that input. Invalid/non-serialsim devices
are rejected using the driver's remote-control ioctl before data transfer.

Nanovax's DKMS installation is documented in packaging/serialsim/README.md.
One real-driver check of Courier's backend passed all 256 byte values in both
directions, remote DTR changes, and DSR assertion/deassertion on normal close.
MAME rebuilt locally. A complete firmware-to-firmware session is pending native
AArch64 deployment; emulator software was not built on nanovax. No broad modem
or network sweep was repeated for this transport change.
