# First DECserver-to-Courier AT exchange on nanovax

Verified 2026-11-01 using the user's native Courier build at
/home/kostik/work/courier-emu (cefbe4a). Its existing Python 3.11 AArch64
supervisor extension and C5x library were staged into RAM; no compilation
was run by the agent. Configuration/native-library preflight passed with
COURIER_EMU_NO_BUILD=1.

## Running endpoints

DECserver runtime:

```text
/dev/shm/ds90-lat-modem.W3F8wp/decserver90tl
```

It runs with the working 172.20.21.5/24 configuration copied after graceful
shutdown of the previous instance:

```sh
./run.sh --interactive --tap ds90tap --serialsim 2=/dev/ttyPipeA0 run/validated-server
```

Port 1 remains a management PTY; port 2 uses serialsim A0. Other ports retain
PTYs. All runtime settings and logs stay under /dev/shm.

Courier runtime:

```text
/dev/shm/courier-serialsim.eeuo7jm0
```

It runs the analog403 profile with serialsim B0, RAM-backed settings,
compilation disabled and audio monitoring off. The temporary test.ini uses
loopback SIP/RTP binding, port 5074/RTP 4014, and no SIP registration. It is
an AT-test setup, not verified incoming-call provisioning. The original
Courier checkout/configuration was not changed.

## DECserver configuration and observed exchange

Configured only simulated port 2: autobaud disabled, 9600 baud, 8 data bits,
no parity, flow control disabled, permanent Remote access applied by logout.
TCP listener 2002 maps to port 2 with connections enabled. SHOW readbacks
confirmed the settings after application. These are saved in the emulated
RAM-backed configuration, not persistent host installation files.

From the notebook:

```text
telnet -8 172.20.21.5 2002
Connected to 172.20.21.5.
AT
OK
```

The AT response arrived before the test client exited. Port-2 sideband
inspection showed DTR=1, DSR=1, RX/TX enabled and no queued host output.
Courier DSR remains the documented endpoint-ready approximation, not a
decoded firmware ASIC output. Signal transitions and carrier handling were
not exercised in this test.

The user requested that both emulators stay running for their own call.
The Telnet test client was disconnected; no test call or SIP registration
was made. Both emulators were left running. Incoming-call readiness is not
established while registration is disabled; the setup also remains volatile
across reboot. The earlier outgoing LAT refusal is recorded separately in
lat-first-session-2026-11-01.md and remains unresolved.
