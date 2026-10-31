import sys
import tempfile
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from tap_network import validate_tap


class TapPreflightTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.net = self.root / 'net'
        self.interface = self.net / 'ds90tap'
        self.interface.mkdir(parents=True)
        (self.interface / 'flags').write_text('0x1003')
        (self.interface / 'tun_flags').write_text('0x1002')
        bridge = self.net / 'brds90'
        (bridge / 'bridge').mkdir(parents=True)
        (self.interface / 'master').symlink_to(bridge, target_is_directory=True)
        self.tun = self.root / 'tun'
        self.tun.touch()

    def check(self, name='ds90tap'):
        return validate_tap(name, self.net, self.tun)

    def test_accepts_up_bridged_tap(self):
        self.assertEqual(self.check(), 'brds90')

    def test_refuses_physical_or_tun_interface(self):
        (self.interface / 'tun_flags').unlink()
        with self.assertRaisesRegex(ValueError, 'not a TAP'):
            self.check()
        (self.interface / 'tun_flags').write_text('0x1001')
        with self.assertRaisesRegex(ValueError, 'not a TAP'):
            self.check()

    def test_refuses_down_or_unbridged_tap(self):
        (self.interface / 'flags').write_text('0x1002')
        with self.assertRaisesRegex(ValueError, 'down'):
            self.check()
        (self.interface / 'flags').write_text('0x1003')
        (self.interface / 'master').unlink()
        with self.assertRaisesRegex(ValueError, 'Linux bridge'):
            self.check()

    def test_refuses_missing_tap_or_tun_device(self):
        with self.assertRaisesRegex(ValueError, 'does not exist'):
            self.check('absent')
        self.tun.unlink()
        with self.assertRaisesRegex(ValueError, 'missing or inaccessible'):
            self.check()

    def test_rejects_invalid_names_before_reading_sysfs(self):
        for name in ('../ds90tap', '.', '..', 'a' * 16, 'tap%u', 'tap name', ''):
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.check(name)


if __name__ == '__main__':
    unittest.main()
