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
