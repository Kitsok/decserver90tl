# Container-free build for nanovax

Run `./buildaarch64.sh` on a Linux build machine. This is a genuine cross-build:
host tools execute locally and an AArch64 GCC 12 compiler builds the target.
There is no Docker, Podman, chroot, QEMU, SSH, sudo, or host package installation
inside the script. Nothing is built on nanovax. Use a checkout path without
whitespace and Python 3.9 or newer.

## Host prerequisites

Install these explicitly on the build machine (Debian/Ubuntu package names):

```sh
sudo apt-get install build-essential git python3 pkg-config apt dpkg gnupg \
  ca-certificates gcc-12-aarch64-linux-gnu g++-12-aarch64-linux-gnu \
  binutils-aarch64-linux-gnu
```

GCC 12 is deliberate: nanovax is Debian 12 with glibc 2.36. Set AARCH64_CC and
AARCH64_CXX to alternate paths for GCC 12 AArch64 cross-compilers if necessary.
Newer compiler runtimes from the host are not a substitute for the target
development packages. Host-native GCC/G++ also build MAME's build-time tools.

```sh
./buildaarch64.sh --check       # diagnose host prerequisites; no downloads
./buildaarch64.sh -j 2          # prepare dependencies, build, package
./buildaarch64.sh --offline    # reuse prepared sysroot and pinned source
```

The first build needs HTTPS access to Debian and GitHub. Debian signing keys
are checked against pinned Bookworm fingerprints published by the
[Debian FTP team](https://ftp-master.debian.org/keys.html). APT authenticates
repository metadata and package hashes. Its configuration, status database,
lists, package cache and logs are all under .deps/aarch64/apt. Download-only
mode is used; dpkg-deb extracts files without running package scripts. Host
architecture settings, APT repositories and installed packages are untouched.

## Build isolation

The default uses the standalone headless frontend, excluding MAME's standard
frontend, Lua and SQLite. Shared core services and SDL remain; see [BUILD.md](BUILD.md).
Pass `./buildaarch64.sh --full-frontend` if Lua diagnostics are needed.
The selected mode is recorded in `BUILD-TARGET.json` in the runtime bundle.
Changing modes regenerates the cross-build projects and replaces the same
output executable and archive after a successful build.

- .deps/aarch64/sysroot contains Debian 12 ARM64 development/runtime packages.
- .deps/aarch64/mame is a separate checkout of mame-revision.txt, patched with
  the same driver/device changes as the native build.
- .deps/aarch64/bin contains generated compiler and pkg-config wrappers.
- build/aarch64/bin/mame-ds90tl is the resulting AArch64 ELF executable.

The wrappers force target headers, GCC 12 startup/runtime files, library paths
and pkg-config metadata from the sysroot. Target code uses -mcpu=cortex-a53.
MAME's bundled dependencies are cross-built; precompiled headers, unrelated
machine layouts and target symbol stripping by the host tool are disabled.
Native build objects and build/mame-ds90tl are not reused or replaced.

The prepared sysroot is cached unchanged. Its nanovax-sysroot.json records
package versions/hashes. To refresh Debian packages, move the cached sysroot
aside and rerun online. The script refuses to overwrite an unrecognized tree.
Do not copy compiled .deps trees between architectures or compiler versions.

## Deployable output

The result is `build/aarch64/decserver90tl-nanovax.tar.gz`. It contains:

- the AArch64 executable and its recursive ELF shared-library dependencies,
  including the matching Debian 12 loader and glibc;
- a launcher that selects those bundled libraries;
- unchanged MNENG3 firmware, runtime Python helpers and shell launchers;
- configuration/network documentation, package metadata, copyrights and hashes.

Each ELF is checked for AArch64 architecture and glibc versions no newer than
2.36 before the archive is published. No ARM binary is executed during the
build. Runtime functionality still needs testing on nanovax; these checks do
not establish emulator speed or a complete modem connection.

Copy the archive to a new directory under /home/kostik/work on nanovax and
extract it there. Avoid extracting over an existing source checkout or saved
configuration. Then, from the extracted decserver90tl directory:

```sh
sha256sum -c SHA256SUMS
./run.sh --interactive --serialsim 2=/dev/ttyPipeA0
```

Nanovax's existing Python 3 is used; no Python interpreter is bundled. Serialsim,
TAP provisioning and Courier are separate runtime components. The serialsim
driver is already installed on nanovax through DKMS; this cross-build does not
replace it, compile Courier, or modify host networking. Saved NVRAM and run logs
are never included in the archive. Add --tap only after preparing the desired
bridge/TAP on nanovax.
