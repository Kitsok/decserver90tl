"""Small, offline checks of cross-build isolation and ABI rejection."""
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('cross_build', Path(__file__).resolve().parents[1]/'tools/build_aarch64.py')
cross = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cross)


class CrossBuildTests(unittest.TestCase):
    def test_cxx_uses_only_explicit_target_headers_and_runtime_prefix(self):
        with patch.dict(os.environ, {'DS90_CROSS_SYSROOT': '/target', 'DS90_CROSS_CXX': 'cross-g++'}), patch.object(cross.os, 'execvp') as execute:
            cross.compiler('cxx', ['-c', 'test.cpp'])
        program, arguments = execute.call_args.args
        self.assertEqual(program, 'cross-g++')
        self.assertIn('--sysroot=/target', arguments)
        self.assertIn('-B/target/usr/lib/gcc/aarch64-linux-gnu/12/', arguments)
        self.assertIn('-nostdinc', arguments)
        self.assertIn('-nostdinc++', arguments)
        self.assertLess(arguments.index('/target/usr/include/c++/12'), arguments.index('/target/usr/include'))

    def test_pkgconfig_cannot_search_host_metadata(self):
        with patch.dict(os.environ, {'DS90_CROSS_SYSROOT': '/target', 'PKG_CONFIG_PATH': '/host/pkgconfig'}), patch.object(cross.os, 'execvpe') as execute:
            cross.compiler('pkg-config', ['--libs', 'sdl2'])
        _, _, env = execute.call_args.args
        self.assertEqual(env['PKG_CONFIG_PATH'], '')
        self.assertEqual(env['PKG_CONFIG_SYSROOT_DIR'], '/target')
        self.assertTrue(all(path.startswith('/target/') for path in env['PKG_CONFIG_LIBDIR'].split(':')))

    def test_bundle_rejects_host_elf_and_newer_glibc(self):
        for header, version, message in (
            ('Machine: Advanced Micro Devices X86-64', '', 'Non-AArch64'),
            ('Machine: AArch64', 'GLIBC_2.38', 'newer than nanovax'),
        ):
            with self.subTest(message=message), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                binary = root/'binary'
                binary.write_bytes(b'test fixture')
                def capture(command, **kwargs):
                    return header if '-h' in command else version
                with patch.object(cross, 'OUTPUT', root), patch.object(cross, 'capture', capture):
                    with self.assertRaisesRegex(SystemExit, message):
                        cross.bundle(binary, root/'sysroot')


if __name__ == '__main__':
    unittest.main()
