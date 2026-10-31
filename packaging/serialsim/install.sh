#!/bin/sh
# Run as root on nanovax after copying this directory under ~/work/serialsim.
set -eu

source_dir=/home/kostik/work/serialsim
version=0.0.0+git60c0f40
revision=60c0f40d884d92b80442857ed1b659f60294d9fb
templates=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
target=/usr/src/serialsim-$version

test "$(id -u)" -eq 0
test "$(git -c safe.directory="$source_dir" -C "$source_dir" rev-parse HEAD)" = "$revision"
git -c safe.directory="$source_dir" -C "$source_dir" diff --quiet
command -v dkms >/dev/null
test -r "/lib/modules/$(uname -r)/build/Module.symvers"
for path in "$target" /etc/modprobe.d/serialsim.conf /etc/modules-load.d/serialsim.conf /etc/udev/rules.d/70-serialsim.rules; do
    if test -e "$path"; then
        printf 'Refusing to overwrite existing installation file: %s\n' "$path" >&2
        exit 1
    fi
done

# DKMS builds from its root-owned source snapshot on every kernel upgrade.
install -d -m 0755 "$target/include/linux"
install -m 0644 "$source_dir/serialsim.c" "$source_dir/Makefile" "$templates/dkms.conf" "$target/"
install -m 0644 "$source_dir/include/linux/serialsim.h" "$target/include/linux/"
dkms add -m serialsim -v "$version"
dkms install -m serialsim -v "$version" -k "$(uname -r)" -j 1

install -m 0644 "$templates/serialsim.conf" /etc/modprobe.d/serialsim.conf
install -m 0644 "$templates/modules-load.conf" /etc/modules-load.d/serialsim.conf
install -m 0644 "$templates/70-serialsim.rules" /etc/udev/rules.d/70-serialsim.rules
udevadm control --reload-rules
modprobe serialsim
udevadm settle
dkms status -m serialsim
ls -l /dev/ttyPipeA[0-6] /dev/ttyPipeB[0-6]
