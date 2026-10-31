#!/usr/bin/env python3
"""One short byte and modem-ioctl check of the unused first serialsim pair."""
import array
import fcntl
import os
import select
import termios
import time
import tty

fds = []
try:
    for path in ('/dev/ttyPipeA0', '/dev/ttyPipeB0'):
        fd = os.open(path, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
        fds.append(fd)
        tty.setraw(fd)
        attrs = termios.tcgetattr(fd)
        attrs[2] |= termios.CLOCAL | termios.CREAD
        attrs[4] = attrs[5] = termios.B115200
        termios.tcsetattr(fd, termios.TCSANOW, attrs)
    a, b = fds
    for src, dst, data in ((a, b, b'DS90_TO_COURIER'), (b, a, b'COURIER_TO_DS90')):
        os.write(src, data)
        received = b''
        end = time.monotonic() + 2
        while len(received) < len(data) and time.monotonic() < end:
            if select.select([dst], [], [], .1)[0]:
                received += os.read(dst, 128)
        assert received == data, (data, received)
    # Disable automatic null-modem inputs on A: Courier will drive A's DSR.
    fcntl.ioctl(b, 0x54e4, 0)
    for state in (False, True):
        fcntl.ioctl(a, termios.TIOCMBIS if state else termios.TIOCMBIC,
                    array.array('I', [termios.TIOCM_DTR]))
        time.sleep(.03)
        value = array.array('I', [0])
        fcntl.ioctl(b, 0x800454e9, value, True)
        assert bool(value[0] & termios.TIOCM_DTR) == state
        fcntl.ioctl(b, 0x54e5, (termios.TIOCM_DSR << 16) | (termios.TIOCM_DSR if state else 0))
        fcntl.ioctl(a, termios.TIOCMGET, value, True)
        assert bool(value[0] & termios.TIOCM_DSR) == state
    print('PASS: bidirectional bytes, remote DTR observation, remote DSR control')
finally:
    if len(fds) == 2:
        fcntl.ioctl(fds[1], 0x54e4, 1)
    for fd in fds:
        os.close(fd)
