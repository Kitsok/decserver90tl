#!/usr/bin/env python3
"""Cross-build a nanovax bundle without containers, sudo or host package changes.

Host tools are explicit prerequisites. Signed Debian 12 ARM64 development and
runtime packages are downloaded into private APT state and extracted as a sysroot.
"""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import pwd
import re
import shlex
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT/'.deps/aarch64'
OUTPUT = ROOT/'build/aarch64'
PACKAGES = ['libc6-dev', 'libgcc-12-dev', 'libstdc++-12-dev', 'libsdl2-dev',
            'libsdl2-ttf-dev', 'libfontconfig-dev', 'libegl-dev']
# Published at https://ftp-master.debian.org/keys.html.
KEYS = {
    'archive-key-12.asc': 'B8B80B5B623EAB6AD8775C45B7C5D7D6350947F8',
    'archive-key-12-security.asc': '05AB90340C0C5E797F44A8C8254CF3B5AEC0A8F0',
    'release-12.asc': '4D64FEC119C2029067D6E791F8D2585B8783D481',
}


def run(command, **kwargs):
    return subprocess.run([str(item) for item in command], check=True, **kwargs)


def capture(command, **kwargs):
    return subprocess.check_output([str(item) for item in command], text=True, **kwargs)


def tools():
    cc = os.environ.get('AARCH64_CC', 'aarch64-linux-gnu-gcc-12')
    cxx = os.environ.get('AARCH64_CXX', 'aarch64-linux-gnu-g++-12')
    needed = ['git', 'make', 'gcc', 'g++', 'pkg-config', 'apt-get', 'dpkg',
              'dpkg-deb', 'gpg', 'gpgv', 'aarch64-linux-gnu-ar',
              'aarch64-linux-gnu-readelf', cc, cxx]
    missing = [name for name in needed if not shutil.which(name)]
    if missing:
        raise SystemExit('Missing host tools: '+', '.join(missing)+'\nInstall explicitly on Debian/Ubuntu:\n'
                         '  sudo apt-get install build-essential git python3 pkg-config apt dpkg gnupg ca-certificates '
                         'gcc-12-aarch64-linux-gnu g++-12-aarch64-linux-gnu binutils-aarch64-linux-gnu')
    for compiler in (cc, cxx):
        if capture([compiler, '-dumpversion']).strip().split('.')[0] != '12':
            raise SystemExit(f'{compiler} must be GCC 12 for the Debian 12 target headers/runtime')
        if capture([compiler, '-dumpmachine']).strip() != 'aarch64-linux-gnu':
            raise SystemExit(f'{compiler} is not an aarch64-linux-gnu compiler')
    return cc, cxx


def prepare_sysroot(offline):
    destination = WORK/'sysroot'
    if (destination/'nanovax-sysroot.json').exists():
        manifest = json.loads((destination/'nanovax-sysroot.json').read_text())
        if manifest.get('requested_packages') != PACKAGES:
            raise SystemExit('Cached sysroot package selection differs; move it aside before regenerating')
        return destination
    if offline:
        raise SystemExit('Prepared Debian 12 sysroot is missing; first run needs network access')
    if destination.exists():
        raise SystemExit(f'Refusing to overwrite incomplete or unrelated sysroot: {destination}')
    apt = WORK/'apt'
    for name in ('etc/parts', 'lists/partial', 'archives/partial', 'log', 'gnupg'):
        (apt/name).mkdir(parents=True, exist_ok=True)
    (apt/'gnupg').chmod(0o700)
    key_env = os.environ.copy()
    key_env['GNUPGHOME'] = str(apt/'gnupg')
    for name, fingerprint in KEYS.items():
        path = apt/name
        with urllib.request.urlopen('https://ftp-master.debian.org/keys/'+name, timeout=60) as response:
            path.write_bytes(response.read())
        listing = capture(['gpg', '--batch', '--with-colons', '--show-keys', path], env=key_env)
        primary = next(line.split(':')[9] for line in listing.splitlines() if line.startswith('fpr:'))
        if primary != fingerprint:
            raise SystemExit(f'Unexpected Debian signing-key fingerprint: {primary}')
        run(['gpg', '--batch', '--import', path], env=key_env)
    keyring = apt/'bookworm.gpg'
    run(['gpg', '--batch', '--yes', '--output', keyring, '--export', *KEYS.values()], env=key_env)
    sources = apt/'etc/sources.list'
    sources.write_text(''.join(f'deb [arch=arm64 signed-by={keyring}] {url} {suite} main\n'
        for url, suite in [('https://deb.debian.org/debian', 'bookworm'),
                           ('https://deb.debian.org/debian', 'bookworm-updates'),
                           ('https://security.debian.org/debian-security', 'bookworm-security')]))
    (apt/'status').touch()
    # All APT state/config/log/cache paths are private. No dpkg installation is
    # performed, and no host APT configuration or post-invoke hooks are read.
    config = {
        'Dir::Etc': apt/'etc', 'Dir::Etc::main': '/dev/null', 'Dir::Etc::parts': apt/'etc/parts',
        'Dir::Etc::sourcelist': sources, 'Dir::Etc::sourceparts': apt/'etc/parts',
        'Dir::Etc::preferences': '/dev/null', 'Dir::Etc::preferencesparts': apt/'etc/parts',
        'Dir::State': apt, 'Dir::State::status': apt/'status', 'Dir::State::lists': apt/'lists',
        'Dir::Cache': apt, 'Dir::Cache::archives': apt/'archives',
        'Dir::Cache::pkgcache': apt/'pkgcache.bin', 'Dir::Cache::srcpkgcache': apt/'srcpkgcache.bin',
        'Dir::Log': apt/'log', 'APT::Architecture': 'arm64',
        'APT::Sandbox::User': pwd.getpwuid(os.getuid()).pw_name,
        'Acquire::Languages': 'none', 'APT::Get::AllowUnauthenticated': 'false',
        'Acquire::AllowInsecureRepositories': 'false',
    }
    conf = apt/'apt.conf'
    conf.write_text(''.join(f'{key} "{value}";\n' for key, value in config.items())+
                    'APT::Architectures { "arm64"; };\n')
    env = os.environ.copy()
    env['APT_CONFIG'] = str(conf)
    run(['apt-get', 'update'], env=env)
    run(['apt-get', '--download-only', '--no-install-recommends', '-y', 'install',
         *(name+':arm64' for name in PACKAGES)], env=env)
    selected = {}
    for path in sorted((apt/'archives').glob('*.deb')):
        name, version, architecture = capture(['dpkg-deb', '-f', path, 'Package', 'Version', 'Architecture']).splitlines()
        # Multi-field output has "Field: value" prefixes.
        name, version, architecture = (value.split(': ', 1)[-1] for value in (name, version, architecture))
        if architecture not in ('arm64', 'all'):
            raise SystemExit(f'Unexpected package architecture: {path}')
        previous = selected.get(name)
        if previous is None or subprocess.run(['dpkg', '--compare-versions', version, 'gt', previous[0]]).returncode == 0:
            selected[name] = (version, path)
    if not selected:
        raise SystemExit('No target packages downloaded')
    with tempfile.TemporaryDirectory(prefix='sysroot-', dir=WORK) as temporary:
        stage = Path(temporary)/'root'
        stage.mkdir()
        for version, path in selected.values():
            run(['dpkg-deb', '--extract', path, stage])
        # Absolute package symlinks must resolve inside the sysroot, never on
        # the build host (notably linker/runtime library symlinks).
        for path in stage.rglob('*'):
            if path.is_symlink() and os.readlink(path).startswith('/'):
                target = stage/os.readlink(path).lstrip('/')
                path.unlink()
                path.symlink_to(os.path.relpath(target, path.parent))
        (stage/'nanovax-sysroot.json').write_text(json.dumps({
            'distribution': 'Debian 12 bookworm', 'architecture': 'arm64',
            'requested_packages': PACKAGES,
            'packages': {name: {'version': version, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
                         for name, (version, path) in selected.items()},
        }, indent=2)+'\n')
        stage.rename(destination)
    return destination


def compiler(mode, arguments):
    root = Path(os.environ['DS90_CROSS_SYSROOT'])
    if mode == 'pkg-config':
        env = os.environ.copy()
        env['PKG_CONFIG_LIBDIR'] = f'{root}/usr/lib/aarch64-linux-gnu/pkgconfig:{root}/usr/share/pkgconfig'
        env['PKG_CONFIG_SYSROOT_DIR'] = str(root)
        env['PKG_CONFIG_PATH'] = ''
        return os.execvpe('pkg-config', ['pkg-config', *arguments], env)
    cxx = mode == 'cxx'
    program = os.environ['DS90_CROSS_CXX' if cxx else 'DS90_CROSS_CC']
    flags = [f'--sysroot={root}', f'-B{root}/usr/lib/gcc/aarch64-linux-gnu/12/',
             '-mcpu=cortex-a53', '-nostdinc', f'-L{root}/usr/lib/aarch64-linux-gnu',
             f'-L{root}/lib/aarch64-linux-gnu',
             f'-Wl,-rpath-link,{root}/usr/lib/aarch64-linux-gnu:{root}/lib/aarch64-linux-gnu']
    if cxx:
        flags += ['-nostdinc++']
        for directory in ('usr/include/c++/12', 'usr/include/aarch64-linux-gnu/c++/12', 'usr/include/c++/12/backward'):
            flags += ['-isystem', str(root/directory)]
    for directory in ('usr/lib/gcc/aarch64-linux-gnu/12/include',
                      'usr/lib/gcc/aarch64-linux-gnu/12/include-fixed',
                      'usr/include/aarch64-linux-gnu', 'usr/include'):
        flags += ['-isystem', str(root/directory)]
    os.execvp(program, [program, *flags, *arguments])


def prepare_mame(offline):
    source = WORK/'mame'
    revision = (ROOT/'mame-revision.txt').read_text().strip()
    if not (source/'.git').exists():
        if source.exists() and any(source.iterdir()):
            raise SystemExit(f'Refusing to overwrite non-repository {source}')
        source.mkdir(exist_ok=True)
        run(['git', '-C', source, 'init', '--quiet'])
    if subprocess.run(['git', '-C', source, 'rev-parse', '--verify', 'HEAD'],
                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode:
        if offline:
            raise SystemExit('Pinned cross-build MAME checkout is missing; first run needs network access')
        run(['git', '-C', source, 'fetch', '--depth', '1', 'https://github.com/mamedev/mame.git', revision])
        run(['git', '-C', source, 'checkout', '--detach', revision])
    if capture(['git', '-C', source, 'rev-parse', 'HEAD']).strip() != revision:
        raise SystemExit('Cross-build MAME revision differs; existing checkout left unchanged')
    return source


def bundle(binary, sysroot, full_frontend=False):
    readelf = 'aarch64-linux-gnu-readelf'
    search = [sysroot/'lib/aarch64-linux-gnu', sysroot/'usr/lib/aarch64-linux-gnu',
              sysroot/'lib', sysroot/'usr/lib']
    with tempfile.TemporaryDirectory(prefix='nanovax-bundle-', dir=OUTPUT) as temporary:
        stage = Path(temporary)/'decserver90tl'
        libs = stage/'build/lib'
        libs.mkdir(parents=True)
        shutil.copy2(binary, stage/'build/mame-ds90tl.bin')
        pending = [binary]
        visited = set()
        library_names = set()
        interpreter = None
        while pending:
            path = pending.pop()
            if path.resolve() in visited:
                continue
            visited.add(path.resolve())
            header = capture([readelf, '-h', path])
            if not re.search(r'Machine:\s+AArch64', header):
                raise SystemExit(f'Non-AArch64 ELF in target dependency closure: {path}')
            versions = capture([readelf, '--version-info', path])
            if any(tuple(map(int, value.split('.'))) > (2, 36)
                   for value in re.findall(r'GLIBC_(\d+(?:\.\d+)+)', versions)):
                raise SystemExit(f'Target requires glibc newer than nanovax 2.36: {path}')
            needed = re.findall(r'\(NEEDED\).*?\[(.*?)\]', capture([readelf, '-d', path]))
            if path == binary:
                match = re.search(r'Requesting program interpreter:\s*(.*?)\]', capture([readelf, '-l', path]))
                if not match:
                    raise SystemExit('Target executable has no dynamic loader')
                interpreter = Path(match[1]).name
                needed.append(interpreter)
            for name in needed:
                if name in library_names:
                    continue
                original = next((directory/name for directory in search if (directory/name).is_file()), None)
                if original is None or not original.resolve().is_relative_to(sysroot):
                    raise SystemExit(f'Missing target runtime dependency: {name}')
                shutil.copy2(original, libs/name, follow_symlinks=True)
                library_names.add(name)
                pending.append(original)
        launcher = stage/'build/mame-ds90tl'
        launcher.write_text('#!/bin/sh\nset -eu\nhere=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)\n'
                            f'exec "$here/lib/{interpreter}" --library-path "$here/lib" "$here/mame-ds90tl.bin" "$@"\n')
        launcher.chmod(0o755)
        for relative in ('run.sh', 'network.sh', 'README.md', 'BUILD.md', 'AARCH64-BUILD.md', 'serialsim.md',
                         'modem-lines.md', 'network.md', 'settings-storage.md',
                         'firmware/MNENG3.SYS', 'tools/run_mneng3.py', 'tools/run_output.py',
                         'tools/tap_network.py', 'tools/build_mame.py', 'tools/serial_control.py'):
            destination = stage/relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT/relative, destination)
        shutil.copy2(sysroot/'nanovax-sysroot.json', stage/'BUILD-PACKAGES.json')
        for copyright_file in (sysroot/'usr/share/doc').glob('*/copyright'):
            if copyright_file.is_file() and copyright_file.resolve().is_relative_to(sysroot):
                destination = stage/'licenses'/copyright_file.parent.name/'copyright'
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(copyright_file, destination, follow_symlinks=True)
        for name in ('COPYING', 'LICENSE.md', 'LICENSE'):
            original = WORK/'mame'/name
            if original.is_file():
                destination = stage/'licenses'/('MAME-'+name)
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(original, destination)
        common_licenses = sysroot/'usr/share/common-licenses'
        if not common_licenses.is_dir():
            common_licenses = Path('/usr/share/common-licenses')
        if common_licenses.is_dir():
            shutil.copytree(common_licenses, stage/'licenses/common-licenses', symlinks=True)
        (stage/'BUILD-TARGET.json').write_text(json.dumps({
            'architecture': 'aarch64', 'cpu': 'cortex-a53', 'distribution': 'Debian 12',
            'frontend': 'full' if full_frontend else 'standalone',
            'maximum_glibc': '2.36', 'mame_revision': (ROOT/'mame-revision.txt').read_text().strip(),
            'compiler': capture([os.environ['DS90_CROSS_CXX'], '--version']).splitlines()[0],
            'driver_sha256': hashlib.sha256((ROOT/'src/mame/decserver90tl.cpp').read_bytes()).hexdigest(),
            'runtime_libraries': sorted(library_names),
        }, indent=2)+'\n')
        hashes = [f'{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.relative_to(stage)}'
                  for path in sorted(stage.rglob('*')) if path.is_file()]
        (stage/'SHA256SUMS').write_text('\n'.join(hashes)+'\n')
        archive = OUTPUT/'decserver90tl-nanovax.tar.gz'
        staged_archive = Path(temporary)/archive.name
        with tarfile.open(staged_archive, 'w:gz') as tar:
            tar.add(stage, arcname='decserver90tl')
        os.replace(staged_archive, archive)
        print(f'Bundle: {archive}\nExtract on nanovax and run decserver90tl/run.sh --interactive', flush=True)


def main():
    if len(sys.argv) > 2 and sys.argv[1] == '--tool':
        compiler(sys.argv[2], sys.argv[3:])
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('-j', '--jobs', type=int, default=2)
    parser.add_argument('--check', action='store_true', help='Check host tools only, with no downloads or build')
    parser.add_argument('--offline', action='store_true', help='Require the cached sysroot and pinned MAME checkout')
    parser.add_argument('--full-frontend', action='store_true', help='Include the standard MAME/Lua frontend for diagnostics')
    args = parser.parse_args()
    if args.jobs < 1:
        parser.error('--jobs must be positive')
    if sys.platform != 'linux' or any(character.isspace() for character in str(ROOT)):
        parser.error('Use a Linux build machine and a repository path without whitespace')
    cc, cxx = tools()
    firmware = ROOT/'firmware/MNENG3.SYS'
    if hashlib.sha256(firmware.read_bytes()).hexdigest() != 'a3764087d79df64eb7124056824652cf23b558fcae2029f887e4a37a3db49ad3':
        raise SystemExit('Unexpected MNENG3 firmware hash')
    if args.check:
        print('AArch64 GCC 12 toolchain and host prerequisites: OK. Target dependencies are prepared on first build.')
        return
    WORK.mkdir(parents=True, exist_ok=True)
    with (WORK/'cross-build.lock').open('a+') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise SystemExit('Another AArch64 build is running')
        sysroot = prepare_sysroot(args.offline)
        for relative in ('usr/lib/gcc/aarch64-linux-gnu/12/libstdc++.a',
                         'usr/lib/gcc/aarch64-linux-gnu/12/libgcc.a',
                         'usr/lib/gcc/aarch64-linux-gnu/12/crtbeginS.o',
                         'usr/lib/gcc/aarch64-linux-gnu/12/include/stddef.h',
                         'usr/include/c++/12/vector',
                         'usr/include/aarch64-linux-gnu/c++/12/bits/c++config.h'):
            if not (sysroot/relative).is_file():
                raise SystemExit(f'Incomplete Debian 12 development sysroot: missing {relative}')
        source = prepare_mame(args.offline)
        wrappers = WORK/'bin'
        wrappers.mkdir(exist_ok=True)
        for name in ('cc', 'cxx', 'pkg-config'):
            path = wrappers/name
            path.write_text('#!/bin/sh\nexec '+shlex.quote(sys.executable)+' '+
                            shlex.quote(str(Path(__file__).resolve()))+' --tool '+name+' "$@"\n')
            path.chmod(0o755)
        env = os.environ.copy()
        for name in ('CFLAGS', 'CXXFLAGS', 'CPPFLAGS', 'LDFLAGS', 'ARCHOPTS',
                     'CPATH', 'C_INCLUDE_PATH', 'CPLUS_INCLUDE_PATH', 'LIBRARY_PATH',
                     'COMPILER_PATH', 'GCC_EXEC_PREFIX', 'MAKEFLAGS', 'MFLAGS',
                     'PKG_CONFIG_PATH', 'PKG_CONFIG_LIBDIR', 'PKG_CONFIG_SYSROOT_DIR'):
            env.pop(name, None)
        env.update(CC='gcc', CXX='g++', AR='ar', LD='g++')
        env.update(DS90_CROSS_SYSROOT=str(sysroot), DS90_CROSS_CC=cc, DS90_CROSS_CXX=cxx,
                   PKG_CONFIG=str(wrappers/'pkg-config'))
        # Reuse the common pinned/patch-aware build preparation but not native
        # objects. Host GCC still builds GENie; only generated targets cross-build.
        flags = ['CROSS_BUILD=1', 'TARGETOS=linux', 'PLATFORM=arm64', 'ARCHITECTURE=',
                 f'OVERRIDE_CC={wrappers}/cc', f'OVERRIDE_CXX={wrappers}/cxx',
                 f'OVERRIDE_LD={wrappers}/cxx', 'OVERRIDE_AR=aarch64-linux-gnu-ar',
                 'STRIP_SYMBOLS=0', 'NOASM=1']
        signature = json.dumps({
            'root': str(ROOT), 'flags': flags,
            'full_frontend': args.full_frontend,
            'compiler': capture([cxx, '--version']),
            'wrapper_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'sysroot_sha256': hashlib.sha256((sysroot/'nanovax-sysroot.json').read_bytes()).hexdigest(),
        }, sort_keys=True)
        stamp = WORK/'build-configuration.json'
        if not stamp.exists() or stamp.read_text() != signature:
            flags.append('REGENIE=1')
        run([sys.executable, ROOT/'tools/build_mame.py', '--jobs', args.jobs,
             '--skip-machine-layouts', '--source-directory', source,
             '--output-directory', OUTPUT/'bin',
             *(['--full-frontend'] if args.full_frontend else []),
             *('--make-arg='+flag for flag in flags)], env=env)
        stamp.write_text(signature)
        os.environ['DS90_CROSS_CXX'] = cxx
        bundle(OUTPUT/'bin/mame-ds90tl', sysroot, args.full_frontend)


if __name__ == '__main__':
    try:
        main()
    except subprocess.CalledProcessError as error:
        raise SystemExit(error.returncode)
