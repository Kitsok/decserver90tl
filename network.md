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
