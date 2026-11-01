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
import re
from pathlib import Path
import shutil
import signal
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('-j', '--jobs', type=int, default=2)
    parser.add_argument('--skip-machine-layouts', action='store_true',
                        help='Skip unrelated src/mame/layout generation; keep core renderer layouts')
    parser.add_argument('--source-directory', type=Path, default=ROOT/'.deps/mame')
    parser.add_argument('--output-directory', type=Path, default=ROOT/'build')
    parser.add_argument('--make-arg', action='append', default=[], help='Additional Make assignment')
    parser.add_argument('--full-frontend', action='store_true', help='Keep the standard MAME/Lua frontend for diagnostics')
    args = parser.parse_args()
    if args.jobs < 1:
        parser.error('--jobs must be positive')
    subprocess.run([os.environ.get('PKG_CONFIG', 'pkg-config'), '--exists', 'sdl2', 'SDL2_ttf', 'fontconfig', 'egl'], check=True)
    source = args.source_directory.resolve()
    lock = (source.parent/'mame-build.lock').open('a+')
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        raise SystemExit('A MAME build is already running; wait for it to finish.')
    expected = (ROOT/'mame-revision.txt').read_text().strip()
    actual = subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip()
    if actual != expected:
        raise SystemExit(f'MAME revision mismatch: expected {expected}, found {actual}')
    # This follow-up edits code introduced by the TAP patch. Peel it off
    # before checking base patches, then reapply it in sorted order below.
    trace_patch = ROOT/'patches/mame-tap-trace-control.patch'
    if subprocess.run(['git', '-C', str(source), 'apply', '--reverse', '--check', str(trace_patch)],
                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0:
        subprocess.run(['git', '-C', str(source), 'apply', '--reverse', str(trace_patch)], check=True)
    for patch in sorted((ROOT/'patches').glob('mame-*.patch')):
        reverse = subprocess.run(['git', '-C', str(source), 'apply', '--reverse', '--check', str(patch)],
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if reverse.returncode:
            subprocess.run(['git', '-C', str(source), 'apply', '--check', str(patch)], check=True)
            subprocess.run(['git', '-C', str(source), 'apply', str(patch)], check=True)
    destination = source / 'src/mame/dec/decserver90tl.cpp'
    destination.parent.mkdir(exist_ok=True)
    for name in ('decserver90tl.cpp', 'decserver90tl_nvram.h', 'decserver90tl_trace.h'):
        driver = ROOT/'src/mame'/name
        destination = source/'src/mame/dec'/name
        if not destination.exists() or destination.read_bytes() != driver.read_bytes():
            shutil.copyfile(driver, destination)
    standalone_changed = False
    if not args.full_frontend:
        for name, relative in (
            ('ds90tl.cpp', 'src/ds90tl/ds90tl.cpp'),
            ('ds90tl.lua', 'scripts/target/ds90tl/ds90tl.lua'),
        ):
            original = ROOT/'src/standalone'/name
            destination = source/relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            if not destination.exists() or destination.read_bytes() != original.read_bytes():
                shutil.copyfile(original, destination)
                standalone_changed = True
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
    flags = ['SUBTARGET=ds90tl',
             'OSD=sdl', 'NO_X11=1', 'NO_OPENGL=1', 'USE_QTDEBUG=0',
             'NO_USE_XINPUT=1', 'NO_USE_MIDI=1', 'NO_USE_PORTAUDIO=1',
             'NO_USE_PULSEAUDIO=1', 'NO_USE_PIPEWIRE=1', 'USE_PCAP=0',
             'USE_TAPTUN=1', 'NOWERROR=1', 'OPTIMIZE=1', 'SYMBOLS=0', 'PRECOMPILE=0',
             'USE_SYSTEM_LIB_EXPAT=0', 'USE_SYSTEM_LIB_ZLIB=0']
    if args.full_frontend:
        flags += ['TARGET=mame', 'SOURCES=src/mame/dec/decserver90tl.cpp']
    else:
        flags.append('TARGET=ds90tl')
    if args.skip_machine_layouts:
        # Command-line Make assignments override the top-level wildcard.
        # CPU/renderer core layouts are separate generated-project tasks.
        flags.append('LAYOUTS=')
    flags.extend(args.make_arg)
    project_name = 'mameds90tl' if args.full_frontend else 'ds90tl'
    project = source/f'build/projects/sdl/{project_name}/gmake-linux/precompile.make'
    if standalone_changed or (project.exists() and re.search(r'^\s*PCH\s*=', project.read_text(), re.MULTILINE)):
        # Make does not track option changes as file dependencies. Regenerate
        # old projects once so PRECOMPILE=0 removes their forced PCH includes.
        flags.append('REGENIE=1')
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
    output = args.output_directory.resolve()
    output.mkdir(parents=True, exist_ok=True)
    # Distinct upstream outputs avoid reusing the other mode's newer binary.
    binary = source/('ds90tl' if args.full_frontend else 'ds90tl-standalone')
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
