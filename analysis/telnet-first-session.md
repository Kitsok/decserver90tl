# First complete Telnet session attempt

The prepared brds90/ds90tap lab was used with a copied NVRAM store and
manual SET INTERNET SUBNET MASK 255.255.255.0 and SET INTERNET ADDRESS
192.0.2.90 commands. No DHCP server was started.

Two attempts using the installed inetutils Telnet client connected to
TCP port 23. Waiting passively produced no login prompt. Sending an initial
Return produced CR/LF followed by bytes 07 23 00 (BEL, #, NUL), then no
recognizable Local or password prompt within 20 seconds. The test failed;
privileged access, logout and reconnection remain unverified.

Reproduction:

    python3 tools/verify_telnet.py --nvram-seed run/nvram-local-repro-20261031

The tool uses a temporary copy of the seed. It saves the client transcript
in run/telnet-transcript.log and the simulator log in run/settings-telnet.log.
Future runs also save failure details in analysis/telnet-verification.json.
Requires pexpect and /usr/bin/telnet, already installed on the development
host. The TAP must be prepared and available to the current user.

The malformed response is an observation, not yet attributed to firmware,
network emulation, negotiation or configuration. TCP connection success alone
must not be reported as a working Telnet console.

## Follow-up: line endings and serial formatting

Packet inspection showed the first test sent a bare LF. The test now sets
pexpect's line separator to CR. A repeated live test still produced the same
07 23 00 response. An exploratory run sending a username after the malformed
prompt produced a second identical response, without reaching a Local prompt.
That blind username injection is not part of the normal regression.

Serial SHOW SERVER also contains a stray NUL near the screen heading and
after Service Groups. SHOW SERVER REMOTE CONSOLE prints its labels, but no
visible values for Remote Console or Inactivity Logout. These observations
suggest investigating common formatting/initialization alongside the Telnet
path; they do not yet establish a cause. The captured report records these
serial responses. Correcting line endings did not fix the guest behavior.
