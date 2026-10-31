#!/usr/bin/env python3
"""Build only the 90TL machine against the pinned local MAME checkout.

Fetch dependency first: git clone https://github.com/mamedev/mame .deps/mame
Then git -C .deps/mame checkout --detach <mame-revision.txt>.
Requires system development packages: pkg-config, libsdl2-dev,
libsdl2-ttf-dev, libfontconfig-dev and libegl-dev, plus GCC/Make/Python 3.
"""
import argparse
import fcntl
import os
from pathlib import Path
import shutil
import signal
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('-j', '--jobs', type=int, default=2)
    args = parser.parse_args()
    if args.jobs < 1:
        parser.error('--jobs must be positive')
    subprocess.run(['pkg-config', '--exists', 'sdl2', 'SDL2_ttf', 'fontconfig', 'egl'], check=True)
    source = ROOT / '.deps/mame'
    lock = (ROOT/'.deps/mame-build.lock').open('a+')
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        raise SystemExit('A MAME build is already running; wait for it to finish.')
    expected = (ROOT/'mame-revision.txt').read_text().strip()
    actual = subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip()
    if actual != expected:
        raise SystemExit(f'MAME revision mismatch: expected {expected}, found {actual}')
    for patch in sorted((ROOT/'patches').glob('mame-*.patch')):
        reverse = subprocess.run(['git', '-C', str(source), 'apply', '--reverse', '--check', str(patch)],
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if reverse.returncode:
            subprocess.run(['git', '-C', str(source), 'apply', '--check', str(patch)], check=True)
            subprocess.run(['git', '-C', str(source), 'apply', str(patch)], check=True)
    destination = source / 'src/mame/dec/decserver90tl.cpp'
    destination.parent.mkdir(exist_ok=True)
    driver = ROOT/'src/mame/decserver90tl.cpp'
    if not destination.exists() or destination.read_bytes() != driver.read_bytes():
        shutil.copyfile(driver, destination)
    listing = source / 'src/mame/mame.lst'
    text = subprocess.check_output(['git', '-C', str(source), 'show', 'HEAD:src/mame/mame.lst'], text=True)
    text += '\n@source:dec/decserver90tl.cpp\nds90tl\n'
    if listing.read_text() != text:
        listing.write_text(text)
    # MAME's M680X0 group also builds generated 68000/68008 engines and
    # unrelated MCU models. CPU32 uses the Musashi engine plus common code.
    # Restrict the build file list without changing CPU implementation code.
    cpu_script = source/'scripts/src/cpu.lua'
    cpu_lua = subprocess.check_output(['git', '-C', str(source), 'show', 'HEAD:scripts/src/cpu.lua'], text=True)
    first = cpu_lua.index('if CPUS["M680X0"] then\n')
    last = cpu_lua.index('\nend', first) + len('\nend')
    names = ['m68kcpu.cpp', 'm68kcpu.h', 'm68kops.cpp', 'm68kops.h',
             'm68kfpu.cpp', 'm68kmmu.h', 'm68kmusashi.h', 'm68kcommon.h',
             'm68kcommon.cpp', 'fscpu32.h', 'fscpu32.cpp']
    selection = 'if CPUS["M680X0"] then\n\tfiles {\n'
    selection += ''.join(f'\t\tMAME_DIR .. "src/devices/cpu/m68000/{name}",\n' for name in names)
    selection += '\t}\nend'
    cpu_lua = cpu_lua[:first] + selection + cpu_lua[last:]
    if cpu_script.read_text() != cpu_lua:
        cpu_script.write_text(cpu_lua)
    env = os.environ.copy()
    flags = ['SUBTARGET=ds90tl', 'SOURCES=src/mame/dec/decserver90tl.cpp',
             'OSD=sdl', 'NO_X11=1', 'NO_OPENGL=1', 'USE_QTDEBUG=0',
             'NO_USE_XINPUT=1', 'NO_USE_MIDI=1', 'NO_USE_PORTAUDIO=1',
             'NO_USE_PULSEAUDIO=1', 'NO_USE_PIPEWIRE=1', 'USE_PCAP=0',
             'USE_TAPTUN=1', 'NOWERROR=1', 'OPTIMIZE=1', 'SYMBOLS=0',
             'USE_SYSTEM_LIB_EXPAT=0', 'USE_SYSTEM_LIB_ZLIB=0']
    child = subprocess.Popen(['make', f'-j{args.jobs}', *flags], cwd=source, env=env,
                             start_new_session=True, pass_fds=(lock.fileno(),))
    try:
        status = child.wait()
    except BaseException:
        os.killpg(child.pid, signal.SIGTERM)
        try:
            child.wait(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(child.pid, signal.SIGKILL)
            child.wait()
        raise
    if status:
        raise SystemExit(status)
    output = ROOT/'build'
    output.mkdir(exist_ok=True)
    # A source-filtered MAME build names the executable after SUBTARGET.
    binary = source/'ds90tl'
    # Replace the inode so an existing simulator can keep running its build.
    with tempfile.NamedTemporaryFile(dir=output, prefix='.mame-ds90tl-', delete=False) as staging:
        staged = Path(staging.name)
    try:
        shutil.copy2(binary, staged)
        os.replace(staged, output/'mame-ds90tl')
    finally:
        staged.unlink(missing_ok=True)
    print(output/'mame-ds90tl')


if __name__ == '__main__':
    main()
