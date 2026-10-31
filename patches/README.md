# Pinned MAME corrections

The build wrapper checks the exact MAME revision in `mame-revision.txt`,
then applies `mame-*.patch` files in name order. It recognizes an already
applied patch using a reverse applicability check; unexpected patch-context
changes fail the build rather than being silently overwritten.

## Preserve active DUART transfers when baud rates do not change

`mame-duart-preserve-active-serial.patch` changes the MC68681-family
channel clock-select update. The parent ACR write handler calls
`baud_updated()` on both channels even when only interrupt-control bits
change. The previous channel implementation called `set_rcv_rate()` and
`set_tra_rate()` unconditionally. Those serial-interface methods reset the
receive/transmit shift registers and disable their timers. They do not
reconcile the DUART's separate transmitter-ready status in this case.

Consequently an interrupt-control write could discard an active character
and leave the DUART reporting not ready indefinitely. In MNENG3 this
stalled port 1 after its initial CR, while ports 2, 3 and 8 could emit the
login banner. The correction updates each serial rate only when the numeric
rate actually changes, preserving active transfers during unchanged-rate
updates. This also avoids discarding a partial receive frame in that case.

Evidence: `analysis/mneng3-uart1-healthy-handoff-probe.log` (before),
`analysis/mneng3-uart2-channel-control.log`,
`analysis/mneng3-uart3-channel-control.log`, and
`analysis/mneng3-uart1-tx-rate-fix.log` (after). The corrected port-1 run
finishes 30 simulated seconds, receives all three probe CRs and emits the
DS90TL banner and Enter username prompt. The transcript records holding
register writes; it is not a decoded serial-wire capture. Broader MC68681
system compatibility and actual rate-change semantics are not established
by this regression alone.

The patch preserves the source file's original MAME BSD-3-Clause licensing.
It does not alter MNENG3.SYS or remove firmware checks.

## mame-duart-modem-byte-transport.patch

Adds a logical CTS input (ready by default), a transmit-byte callback at the
holding-to-shift-register boundary, and receive FIFO/enabled-state accessors.
MR2-controlled CTS gates between characters and holds THR/TxRDY until resume;
mode changes can release held data and transmitter reset discards it. The 90TL
board connects its DSR signal to this control and its PTY to the byte callback.
Existing drivers with no CTS connection retain an asserted default. The board
handles 2692-compatible DTR commands and automatic receive-DTR behavior locally.

The patch composes with the baud-preservation patch. See modem-lines.md and
tools/verify_modem*.py for real firmware and isolated register verification.

## mame-tap-interface-selection.patch

Extends the existing Linux TAP backend with optional `DS90_TAP_NAME`, keeping
the upstream name fallback when unset. Rejects failed device opens/attachments
instead of returning a dead network device. `DS90_TAP_PCAP` optionally captures
Ethernet frames at the host boundary, without FCS, and flushes each record;
packet metadata is also written to the full trace. No chip registers, descriptor
logic or network protocols are reimplemented here. See network.md for real
firmware ARP/ping/Telnet verification and the offline LANCE loopback fixture.
