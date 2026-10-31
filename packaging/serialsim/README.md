# Nanovax serialsim deployment

Installed on nanovax from upstream revision
60c0f40d884d92b80442857ed1b659f60294d9fb as DKMS package
serialsim/0.0.0+git60c0f40. Source and deployment files live under
/home/kostik/work/serialsim; DKMS keeps a root-owned source snapshot in
/usr/src and build state in /var/lib/dkms.

The running 6.1.63 module was built and installed by DKMS. The module loads
through /etc/modules-load.d/serialsim.conf, with seven pipe pairs selected in
/etc/modprobe.d/serialsim.conf. Devices ttyPipeA0/B0 through ttyPipeA6/B6
are root:dialout, mode 0660, via /etc/udev/rules.d/70-serialsim.rules.
DECserver port 1 remains available for a management PTY.

DKMS AUTOINSTALL and the installed kernel/header post-install hooks rebuild
the module during Debian kernel upgrades. Matching kernel headers/build files
must be available, and upstream may need updates for future kernel APIs. For a
manually installed custom kernel that bypasses Debian's hooks, run:

    sudo dkms autoinstall -k NEW_KERNEL_RELEASE

Do this with the new kernel's matching build tree installed before rebooting.
After an upgrade check `dkms status -m serialsim` and `modinfo -k NEW_KERNEL_RELEASE
serialsim`. This setup does not guarantee compatibility with arbitrary future
kernel APIs. No reboot was performed during installation.

`check_pair.py` passed once as the ordinary user: bidirectional bytes, observing
remote DTR and setting remote DSR. It restores null-modem mode and closes both
TTYs afterwards. Use it only while the first pair is unused.

`install.sh` refuses to overwrite existing deployment files. It is for an initial
installation, not repeated upgrades. The native build required no source changes.
