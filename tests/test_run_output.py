import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from run_output import ConsoleOutput, stream_process


class RunOutputTests(unittest.TestCase):
    def test_default_console_filters_trace_and_throttles_progress(self):
        output = []
        console = ConsoleOutput(60, emit=output.append)
        console.handle('DS90 WRITE-INTERNAL address=fffa00 data=60cf\n')
        for ms in (100, 200, 4900, 5000):
            console.handle(f'DS90 PROGRESS ms={ms} pc=07871448 sp=079dbfc0\n')
        self.assertEqual(sum('Emulated' in line for line in output), 2)
        self.assertFalse(any('WRITE-INTERNAL' in line for line in output))

    def test_checkpoint_notice_visible_with_default_console(self):
        output = []
        console = ConsoleOutput('unlimited', emit=output.append)
        console.handle('DS90 STORAGE checkpoint saved path=/tmp/configram bytes=65536')
        self.assertEqual(len(output), 1)
        self.assertIn('STORAGE checkpoint saved', output[0])

    def test_serial_paths_visible_with_default_console(self):
        output = []
        console = ConsoleOutput('unlimited', emit=output.append)
        for port in range(1, 9):
            console.handle(f'DS90 SERIAL port={port} path=/dev/pts/{port + 10}')
        self.assertEqual(len(output), 8)
        self.assertTrue(output[-1].endswith('SERIAL port=8 path=/dev/pts/18'))

    def test_serial_prompt_is_readable_without_terminal_control_codes(self):
        output = []
        console = ConsoleOutput(60, emit=output.append)
        for byte in b'\x11\x1b[H\x1b[JHello\r\nLocal> ':
            console.handle(f'DS90 UART-TX port=1 byte={byte:02x} char=.\n')
        console.finish()
        self.assertEqual(len(output), 2)
        self.assertTrue(output[0].endswith('UART 1: Hello'))
        self.assertTrue(output[1].endswith('UART 1: Local>'))

    def test_verbose_console_retains_register_trace(self):
        output = []
        console = ConsoleOutput(1, verbose=True, emit=output.append)
        console.handle('DS90 WRITE-INTERNAL address=fffa00 data=60cf\n')
        self.assertIn('WRITE-INTERNAL', output[0])

    def test_actual_firmware_transcript_keeps_prompt_and_parameter_warnings(self):
        output = []
        console = ConsoleOutput(50, emit=output.append)
        fixture = Path(__file__).resolve().parents[1] / 'analysis/mneng3-local-repro-login-50s.log'
        for line in fixture.read_text().splitlines():
            console.handle(line)
        console.finish()
        self.assertTrue(any(line.endswith('UART 1: Local>') for line in output))
        self.assertTrue(any('Local -602-' in line for line in output))
        self.assertTrue(any('Local -603-' in line for line in output))
        self.assertFalse(any('WRITE-INTERNAL' in line or 'UART-TX' in line for line in output))

    def test_console_and_log_are_live_before_child_can_exit(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            log = root / 'trace.log'
            marker = root / 'seen'
            output = []

            def emit(line):
                output.append(line)
                if 'Firmware started' in line:
                    self.assertIn('WRITE-INTERNAL', log.read_text())
                    marker.touch()

            code = '''import pathlib, sys, time
print('DS90 WRITE-INTERNAL address=fffa00 data=60cf', flush=True)
print('DS90 BOOT image=MNENG3', flush=True)
deadline = time.monotonic() + 3
while not pathlib.Path('seen').exists() and time.monotonic() < deadline:
    time.sleep(0.01)
sys.exit(0 if pathlib.Path('seen').exists() else 4)
'''
            status = stream_process([sys.executable, '-c', code], root, os.environ.copy(),
                                    log, ConsoleOutput(1, emit=emit), timeout=5)
            self.assertEqual(status, 0)
            self.assertIn('WRITE-INTERNAL', log.read_text())
            self.assertFalse(any('WRITE-INTERNAL' in line for line in output))

    def test_timeout_stops_the_child(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = []
            code = "import os,time; print('pid=' + str(os.getpid()), flush=True); time.sleep(10)"
            with self.assertRaises(subprocess.TimeoutExpired):
                stream_process([sys.executable, '-c', code], root, os.environ.copy(),
                               root / 'trace.log', ConsoleOutput(1, emit=output.append), timeout=0.3)
            pid = int(next(line.split('pid=')[1] for line in output if 'pid=' in line))
            with self.assertRaises(ProcessLookupError):
                os.kill(pid, 0)


if __name__ == '__main__':
    unittest.main()
