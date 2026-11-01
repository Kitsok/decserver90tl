# Nanovax network and MOP-console milestone

Verified 2026-11-01. The cross-built standalone runtime runs on nanovax,
attached through user-owned TAP ds90tap to the existing DEC bridge decbr.
No build was run by the agent on nanovax. The bundle was checksum-verified;
runtime state remained under /dev/shm rather than flash-backed /tmp.

## Runtime

Directory:

```text
/dev/shm/ds90-performance.zVE9qR/decserver90tl
```

Command, run as kostik:

```sh
./run.sh --interactive --tap ds90tap run/validated-server
```

Tracing and capture are disabled. All eight PTYs were created; port 1 was
/dev/pts/2 in this instance. PTY numbers change on subsequent starts. The
simulator was left running after the successful console test.

Identity verified through SHOW SERVER:

```text
Network Access SW V2.4 BL50 for DS90TL
Address: 02-90-00-00-00-01
Name: LAT_029000000001
Console Port: 1
```

The SHOW SERVER software-name field displays MNENG1; this is not the loaded
image's identity. The launcher verifies and loads the unchanged MNENG3.SYS
image. No attempt was made to change that inherited display field.

## Manual IP and reachability

Applied through the port-1 console after privileged login:

```text
CHANGE INTERNET SUBNET MASK 255.255.255.0
CHANGE INTERNET ADDRESS 172.20.21.5
```

SHOW INTERNET subsequently reported Enabled, address 172.20.21.5 and mask
255.255.255.0. DHCP client remains enabled in the factory settings; no DHCP
server was started. The address was supplied manually, not leased.

Nanovax learned 172.20.21.5 at MAC 02:90:00:00:00:01 on decbr, and one ping
returned in 3.943 ms. From the notebook, two packets returned in 5.893 and
6.543 ms with no loss. The user independently confirmed connectivity.
An earlier notebook ping failed while setup was incomplete; successful
responses were verified after configuration, not inferred from SHOW output.

## MOP console from OpenVMS SIMVAX

Connected from the notebook using Telnet to simvax.decnet.alban
(172.20.21.1), running OpenVMS VAX V7.3. Authentication details are omitted.
NCP SHOW KNOWN CIRCUITS identified QNA-0 as on. The connection command was:

```text
$ MCR NCP CONNECT VIA QNA-0 PHYSICAL ADDRESS 02-90-00-00-00-01
Console connected (press CTRL/D when finished)
```

After the remote-console login, the simulator presented its banner, accepted
the username SIMULATOR and reached Local>. SHOW SERVER verified the synthetic
MAC above, and SHOW INTERNET verified 172.20.21.5/24 over this MOP session.
Commands were issued one at a time; pasting two together lost characters in
the second command, which was then reissued successfully.

Ctrl+D disconnected the MOP console back to VMS. The VMS Telnet session was
logged out. No LAT node settings were changed on simvax.

## Why MOP rather than LAT

The local DECserver 90TL Owner's Manual, section 3-23, describes its logical
remote console as MOP or Telnet. Existing physical-device findings in the
parent workspace's decserver90tl-serial-connections.md already distinguish
this from exported LAT serial-port services. The user selected MOP after
this distinction was checked. A LAT node name does not imply an exported
LAT management-console service. SHOW SERVICES LOCAL listed no services in
this configuration; no inbound or outbound LAT data session was tested here.

## Persistence and limits

CHANGE updated the firmware's operational and permanent configuration in
the selected emulated store. That store is currently in RAM and will be lost
on reboot unless exported. TAP setup is also not yet installed for boot.
This milestone proves MOP management and ARP/ICMP reachability on the real
DEC network. It does not establish seven-modem capacity or live target LAT,
Telnet, serialsim or telephone-call behavior with this optimized build.
