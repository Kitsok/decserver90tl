"""Stream complete simulator logs while presenting concise console progress."""
import queue
import re
import subprocess
import threading
import time


class ConsoleOutput:
    def __init__(self, seconds, verbose=False, emit=None):
        self.seconds = seconds
        self.verbose = verbose
        self.emit = emit or (lambda line: print(line, flush=True))
        self.started = self.last_notice = time.monotonic()
        self.next_progress = 0
        self.guest_ms = 0
        self.serial = {}
        self.ansi = {}

    def say(self, line):
        self.emit(f'[{time.monotonic() - self.started:6.1f}s] {line}')
        self.last_notice = time.monotonic()

    def flush_serial(self, port):
        text = self.serial.pop(port, '')
        if text.strip():
            self.say(f'UART {port}: {text}')

    def handle(self, line):
        line = line.rstrip('\r\n')
        if self.verbose:
            self.say(line)
            return
        progress = re.match(r'DS90 PROGRESS ms=(\d+) pc=([0-9a-fA-F]+)', line)
        if progress:
            self.guest_ms = int(progress[1])
            if self.guest_ms >= self.next_progress:
                self.say(f'Emulated {self.guest_ms / 1000:.1f}/{self.seconds}s')
                self.next_progress = (self.guest_ms // 5000 + 1) * 5000
            return
        tx = re.match(r'DS90 UART-TX port=(\d+) byte=([0-9a-fA-F]{2})', line)
        if tx:
            port, byte = int(tx[1]), int(tx[2], 16)
            if port in self.ansi:
                if self.ansi[port] == 'escape' and byte == ord('['):
                    self.ansi[port] = 'csi'
                elif self.ansi[port] == 'escape' or 0x40 <= byte <= 0x7e:
                    del self.ansi[port]
                return
            if byte == 27:
                self.ansi[port] = 'escape'
                return
            if byte in (17, 19):  # flow control, retained in the raw log
                return
            if byte == 8:
                self.serial[port] = self.serial.get(port, '')[:-1]
                return
            if byte in (10, 13):
                self.flush_serial(port)
            else:
                char = chr(byte) if 32 <= byte < 127 else f'<{byte:02X}>'
                self.serial[port] = self.serial.get(port, '') + char
                if byte == ord('>') or len(self.serial[port]) >= 160:
                    self.flush_serial(port)
            return
        if line.startswith('DS90 FIFO-INJECT'):
            match = re.search(r'port=(\d+) byte=([0-9a-fA-F]{2})', line)
            if match:
                byte = int(match[2], 16)
                char = '<CR>' if byte == 13 else repr(chr(byte)) if 32 <= byte < 127 else f'0x{byte:02x}'
                self.say(f'Diagnostic input: UART {match[1]} {char}')
            return
        if line.startswith(('DS90 SERIAL ', 'DS90 NETWORK ')):
            self.say(line.removeprefix('DS90 '))
        elif line.startswith('DS90 BOOT '):
            self.say('Firmware started (MNENG3, 4 MiB RAM)')
        elif line.startswith(('DS90 unsupported', 'DS90 unresolved', 'DS90 firmware fatal',
                            'DS90 inherited exception')):
            self.say(line)
        elif line and not line.startswith('DS90 '):
            self.say(line)

    def heartbeat(self):
        if time.monotonic() - self.last_notice >= 5:
            self.say(f'Still running; last emulated progress {self.guest_ms / 1000:.1f}/{self.seconds}s')

    def finish(self):
        for port in list(self.serial):
            self.flush_serial(port)


def stream_process(command, cwd, env, log_path, console, timeout=120):
    """Return child status; flush every raw line to disk before console filtering."""
    lines = queue.Queue()
    started = time.monotonic()
    with log_path.open('w') as log:
        process = subprocess.Popen(command, cwd=cwd, env=env, stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT, text=True, errors='replace', bufsize=1)

        def read_lines():
            try:
                for line in process.stdout:
                    lines.put(line)
            finally:
                lines.put(None)

        reader = threading.Thread(target=read_lines, daemon=True)
        reader.start()
        eof = False
        try:
            while not eof or process.poll() is None:
                if timeout is not None and time.monotonic() - started >= timeout:
                    raise subprocess.TimeoutExpired(command, timeout)
                console.heartbeat()
                try:
                    line = lines.get(timeout=0.25)
                except queue.Empty:
                    continue
                if line is None:
                    eof = True
                    continue
                log.write(line)
                log.flush()
                console.handle(line)
            console.finish()
            return process.wait()
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
            reader.join(timeout=1)
            process.stdout.close()
