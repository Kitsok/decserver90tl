#!/usr/bin/env python3
"""Focused check of Courier's backend against an unused serialsim pair."""
import array
import fcntl
import os
import select
import termios
import time
import tty

from courier_emu.serialsim import SerialSimConsole

a = os.open('/dev/ttyPipeA0', os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
tty.setraw(a)
settings = termios.tcgetattr(a)
settings[2] |= termios.CLOCAL | termios.CREAD
settings[4] = settings[5] = termios.B115200
termios.tcsetattr(a, termios.TCSANOW, settings)
backend = None
try:
    b = os.open('/dev/ttyPipeB0', os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
    backend = SerialSimConsole(b)
    time.sleep(.05)
    status = array.array('I', [0])
    fcntl.ioctl(a, termios.TIOCMGET, status, True)
    assert status[0] & termios.TIOCM_DSR, 'Endpoint did not assert peer DSR'
    payload = bytes(range(256))
    os.write(a, payload)
    received = b''
    deadline = time.monotonic() + 2
    while received != payload and time.monotonic() < deadline:
        received += backend.poll()
        time.sleep(.005)
    assert received == payload, received
    for byte in payload:
        backend.write(byte)
    received = b''
    deadline = time.monotonic() + 2
    while received != payload and time.monotonic() < deadline:
        backend.poll(0)
        if select.select([a], [], [], .01)[0]:
            received += os.read(a, 4096)
    assert received == payload, received
    for state in (False, True):
        fcntl.ioctl(a, termios.TIOCMBIS if state else termios.TIOCMBIC,
                    array.array('I', [termios.TIOCM_DTR]))
        time.sleep(.05)
        backend.poll(0)
        assert backend.dtr == state
    backend.close()
    backend = None
    time.sleep(.05)
    fcntl.ioctl(a, termios.TIOCMGET, status, True)
    assert not status[0] & termios.TIOCM_DSR, 'Endpoint left peer DSR asserted'
    print('PASS: Courier serialsim binary data, DTR changes, DSR ready/close')
finally:
    if backend is not None:
        backend.close()
    os.close(a)
