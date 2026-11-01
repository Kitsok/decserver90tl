# Ethernet integration

The simulator reuses MAME's Am7990 controller and Linux TAP provider. Networking
is explicitly selected with `--tap NAME`; the default is offline. A named TAP
must already exist, be UP, and belong to a Linux bridge. The simulator does not
create interfaces, change bridge membership, or require root. The kernel checks
TAP ownership when MAME attaches; failures stop startup rather than simulating
a connected network.

## Prepare an isolated lab

The included helper creates a new bridge and persistent TAP, assigning the TAP
to your normal UID. It refuses to change any existing interface and rolls back
new interfaces if setup fails. The bridge has 192.0.2.1/24 and no external uplink,
NAT, forwarding, or default-route changes:

```sh
sudo ./network.sh setup "$(id -u)"
./run.sh --interactive --tap ds90tap
```

This leaves existing Wi-Fi and libvirt bridges alone. It is a lab network for
host-to-server testing. Linux TAP carries Ethernet frames, including non-IP
protocols such as LAT, without requiring an IP protocol implementation in the
emulator. To join another LAN, prepare a user-owned TAP on its existing bridge
and select that TAP instead. A Wi-Fi station interface generally cannot serve
as an ordinary transparent Ethernet bridge uplink; the lab setup does not try.

Optional helper arguments are `setup OWNER_UID BRIDGE TAP`. The helper never
runs the simulator with sudo. To remove the default lab, stop the simulator and
remove the two interfaces you created:

```sh
sudo ip link delete dev ds90tap
sudo ip link delete dev brds90
```

The helper creates a host TAP and bridge, not permanent host boot configuration.
These interfaces persist after simulator exit but disappear on host reboot unless
separately configured by your network manager. This is separate from guest
configuration storage.

## Run and observe

```sh
./run.sh --interactive --tap ds90tap
# Bounded experiment with an isolated configuration store:
python3 tools/run_mneng3.py --seconds 10 --tap ds90tap \
  --rom-alignment-assist --ram-wait-cycles 1 \
  --nvram-directory run/network-test-nvram --log-file run/network-test.log
```

The launcher prints the bridge/TAP selection and the driver confirms successful
attachment. Networked runs use paced emulation rather than the benchmark mode.
Text logs include packet direction, length, Ethernet addresses and type, plus
LANCE interrupt changes. Normal console verbosity hides individual packets.

Each networked run also writes a classic Ethernet PCAP beside its text log:
`run/interactive.pcap` for interactive mode, or a corresponding stage PCAP for
the default timed recipe. The Python runner accepts `--ethernet-pcap PATH` to
choose another path. Files are truncated when starting a run. Records are
flushed as packets pass the TAP boundary; timestamps are host wall time. Captures
exclude FCS, as conventional host captures do. The existing TAP backend adds
padding and FCS when delivering host frames into the controller.

Inspect captures without changing host interfaces:

```sh
tcpdump -n -e -r run/interactive.pcap
```

The synthetic station address remains `02:90:00:00:00:01`. The LANCE reads its
actual programmed station address, descriptors, buffer pointers and modes from
guest RAM; those are not hard-coded in the network transport.

MAME host configuration is kept in a fresh temporary directory for each runner
invocation so a saved MAME network menu setting cannot silently reconnect a
previous TAP on an offline run. Guest NVRAM continues to use the explicitly
selected persistent directory. Existing host `run/cfg` files are left alone.

## Implementation and verification

The tracked `mame-tap-interface-selection.patch` adds an explicit TAP name via
`DS90_TAP_NAME`, checks backend open/attach success, and records optional packet
captures selected by `DS90_TAP_PCAP`. Normal upstream TAP naming remains the
fallback for other consumers that do not set these variables. The board selects
provider interface 0 only when a TAP was explicitly requested, and the runner
selects the `taptun` provider. Offline mode explicitly selects provider `none`.

Preflight tests exercise rejection of physical/TUN interfaces, missing devices,
invalid names, a down TAP and missing bridge membership. Twelve unit tests pass.
The separate `tools/verify_ethernet_loopback.py` fixture holds the CPU in a RAM
loop and uses the CPU bus to exercise the real LANCE: initialization, CSR3=6,
24-bit DMA, byte order, descriptor ownership, receive/transmit interrupt causes
and acknowledgement all passed. Its 32-byte diagnostic loopback frame becomes
36 bytes including FCS, within the controller's diagnostic loopback length limit.
This component fixture does not use a host network or establish firmware behavior.

After the user prepared brds90/ds90tap, `tools/verify_ethernet.py` used an isolated
copy of the initialized NVRAM seed, logged in through the PTY, entered privileged
mode, and issued these commands:

```text
SET INTERNET SUBNET MASK 255.255.255.0
SET INTERNET ADDRESS 192.0.2.90
```

All three host pings succeeded (0% packet loss). The capture contains a station
ARP reply, three ICMP echo replies and a LAT multicast advertisement. TCP port 23
accepted a connection and returned Telnet option negotiation. Full Telnet login
and incoming LAT sessions were not exercised. The test stopped normally and
removed its private control socket; the original NVRAM seed was unchanged.
Results are recorded in [analysis/ethernet-host-verification.json](analysis/ethernet-host-verification.json)
and [analysis/ethernet-loopback-verification.json](analysis/ethernet-loopback-verification.json).

To configure your own running instance after login, enter `SET PRIVILEGED` and
its password (factory default `SYSTEM`), then the two IP commands above. From the
host, use `ping -I brds90 192.0.2.90` or connect to TCP port 23. The test's IP
configuration belonged to its disposable store; it did not configure yours.

Reproduce the checks after preparing the lab:

```sh
python3 tools/verify_ethernet_loopback.py
python3 tools/verify_ethernet.py --nvram-seed run/my-decserver \
  --report analysis/ethernet-host-verification.json
```

The host test expects factory privileged credentials and configures the lab
address only in a copied store. It uses a private control socket, reserves the
lowest recycled PTY against reconnecting terminal clients, records packets in
`run/ethernet-verification.pcap`, and leaves host interfaces unchanged. Select
another prepared TAP/bridge with its `--tap` and `--bridge` options. The default
subnet is fixed to the isolated 192.0.2.0/24 lab; avoid running multiple instances
with the same guest IP or synthetic MAC on a shared bridge.

## Telnet console login

After assigning the manual IP, run `telnet 192.0.2.90`. Press Return to get
the beep and `#` login-password prompt, then enter the factory login password
`ACCESS`. This differs from `SYSTEM`, used after `SET PRIVILEGED` at Local>.
`CHANGE SERVER LOGIN PASSWORD "new-password"` changes the login password in
both operational and permanent settings; use it through a privileged session.

The complete console regression uses the installed `/usr/bin/telnet` and
Python pexpect, a copied store, and manually assigned 192.0.2.90/24:

```sh
python3 tools/verify_telnet.py --nvram-seed run/my-decserver
python3 tools/verify_telnet.py --nvram-seed run/my-decserver --change-login-password
```

The default test expects the seed's login password to be ACCESS. The optional
flag first sets a known test password in the copy. Both check two sessions,
SHOW commands, privileged access, an operational identification change,
logout and reconnection. Transcripts and packets are saved under run/;
analysis/telnet-verification.json records the latest result. No DHCP server
is started. Incoming LAT sessions remain deferred to nanovax.

## Nanovax MOP-console and IP milestone (2026-11-01)

The optimized AArch64 runtime was verified on nanovax's real DEC network,
using ds90tap on decbr. Manual address 172.20.21.5/24 responds to ping from
nanovax and the notebook. Its synthetic MAC is 02:90:00:00:00:01.

OpenVMS SIMVAX reached the simulator's own Local> management console with:

```text
MCR NCP CONNECT VIA QNA-0 PHYSICAL ADDRESS 02-90-00-00-00-01
```

The logical management console is MOP or Telnet; LAT services expose serial
ports. No LAT node settings were changed on simvax, and a LAT data session
remains untested. The simulator was left running from /dev/shm with a RAM-only
configuration store; this test deployment is not persistent across reboot.
See [milestone details](analysis/nanovax-mop-console-2026-11-01.md) for setup,
observed identity, connection sequence, reachability results and limitations.

## Serial Telnet listener regression

`tools/verify_telnet_ports.py --nvram-seed run/my-decserver` configures a copied
store via the TCP 23 management console, assigning serial ports 1–8 to listeners
2001–2008. This firmware rejects SET/CHANGE PORT ACCESS with error 729; the test
uses DEFINE PORT n ACCESS REMOTE followed by LOGOUT PORT n. Other initial serial
settings use CHANGE: fixed 9600 baud, eight data bits, no parity, no flow control.

The test exchanges distinct markers in both directions, checks port isolation,
DSR and XON/XOFF pause/resume, and disconnect/reconnect. It uses the existing
isolated TAP and manual IP, leaves the source store unchanged, and records
analysis/telnet-ports-verification.json plus run/telnet-ports-transcript.log.
The first individual-port run passed all checks on ports 1–6, then received a
connection refusal from listener 2007. Listener 2008 remains untested in that
run. All eight configuration sequences had returned without CLI errors. The
cause of listener 2007's refusal was subsequently traced to the handoff below.

Follow-up narrowed the failure: SHOW PORT 7 reports operational Access Local,
XON flow control and autobaud enabled, while LIST PORT 7 shows saved Access
Remote, no flow control and autobaud disabled. Both listener 2007 and 2008
report enabled with the expected serial mappings. The guest sends TCP RST/ACK
for the refused connection. Re-enabling/remapping listeners and waiting for
configuration writes did not resolve it. The same SHOW/LIST mismatch remains
after a normal restart with saved IP and listener settings. This points to a
port-configuration activation/restoration problem rather than a listener limit.

The diagnostic now saves IP/listener settings, drains pending writes, restarts,
and then tests requested ports. `--ports 7,8` configures and checks only those
ports, avoiding a repeated full sweep. Low PTYs are reserved across both boots
to keep reconnecting user terminals from consuming test data.

The downloaded image has stale record-validity flags 0x00004040 at header
0x07805016. Firmware ORs genuine checksum failures into that inherited value;
it never clears the stale port-7 bit. The model now clears only its low sixteen
per-port bits before validation, allowing firmware to compute actual failures.
With this handoff correction, the focused two-boot run passed serial ports 7
and 8 on TCP ports 2007 and 2008, including both transfer directions, isolation,
DSR and XON/XOFF pause/resume, and reconnection. Its source store is unchanged.
The latest report records those passes; ports 1–6 passed in commit 630bcdc's
report. All eight physical ports thus have individual coverage across the runs;
eight simultaneous serial sessions have not been established. See
firmware-organization.md for the validation and default-selection addresses.
