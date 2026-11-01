# First outgoing LAT session attempt on nanovax

The user supplied a rebuilt bundle on 2026-11-01. Checksums passed after
extraction to /dev/shm/ds90-lat-modem.W3F8wp/decserver90tl. Its executable
SHA-256 was identical to the already running optimized AArch64 binary:

```text
c6c9825503f7e5c3f7c86e8cd324e480b8f77c3ee6c4878901a10ead40b89960
```

The existing instance and manually configured 172.20.21.5/24 settings were
retained for the LAT test. No VMS LAT configuration was changed.

## Observations

Logged into the emulator's port-8 PTY as LATTEST. Port readback confirmed
Local access, LAT as the default protocol, 9600 baud, group 0 authorized and
current, and a four-session limit. Service/node discovery works: SHOW
SERVICES listed CONTROL, DECAGENT, DECBROUTER90, MODEM, MV2000-1, MV2000-2,
MV3100-40, MV3100-80, NANOVAX and SIMVAX. These are remote services on the
real DEC network, not simulator-exported local services.

SHOW NODE SIMVAX STATUS identified MAC AA-00-04-00-01-04, LAT V5.3, group 0,
1500-byte data-link frames and an available SIMVAX service.

Both commands failed locally:

```text
Local> CONNECT SIMVAX
Local -722- Server disabled

Local> CONNECT LAT SIMVAX
Local -722- Server disabled
```

SHOW SERVER COUNTERS still showed zero LAT messages received/transmitted,
with Ethernet frame counters increasing and no LANCE send/receive failures.
This points to refusal before circuit establishment; the exact gate has not
been identified. No OpenVMS login was reached through LAT.

Privileged HELP SET SERVER listed no obvious general LAT enable/disable
switch. Read-only debugger checks and RAM snapshots were stored under the
running release's run directory in /dev/shm. Candidate constant-table
watchpoints only found background checksum reads, not the refusal site.
Capturing the UART error output found the guest already back in its idle
loop; it did not expose the original connection call stack. No guest memory
was modified, and the debugger detached after each bounded check.

## Remaining work

Identify the connection refusal in the firmware and determine whether an
initialization/handoff field or supported configuration is missing. Discovery
alone is not proof of working LAT sessions. Keep this failure separate from
the already verified MOP management console and ARP/ICMP connectivity.

The user subsequently confirmed a native Courier build at
/home/kostik/work/courier-emu on nanovax. Its existing libraries and firmware
were staged under /dev/shm/courier-serialsim.eeuo7jm0; configuration and native
library checks passed with compilation disabled. The serialsim modem test is
being prepared independently of the unresolved LAT session gate.
