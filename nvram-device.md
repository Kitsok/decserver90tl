# Likely physical settings-storage device

## Estimate

The leading candidate is a **32K×8 parallel EEPROM in the 28C256 family**.
This is an inference from firmware behavior and layout, not an identified part
marking. A pin-compatible battery-backed SRAM module, such as a Dallas DS1230,
remains a credible alternative. The current board photograph does not resolve
the relevant markings well enough to choose a manufacturer or exact part.

## Capacity evidence

A runtime inspection of the initialized 60-entry record table at 0x079ac16c
found its highest primary logical allocation ending at 0xe800. The recovered
accessors divide logical offsets by two and add physical base 0x100c00:

```text
0x100c00 + 0xe800 / 2 = 0x108000  (exclusive end)
```

That lands exactly on the end of a 32 KiB region starting at 0x100000. In other
words, the record allocation occupies 0x7400 physical bytes after a 0x0c00-byte
prefix, totaling 0x8000 bytes. This strongly suggests a 32 KiB storage design;
it does not prove that the installed chip cannot be larger, or that all table
entries are used by every supported configuration. The simulator's 64 KiB file
and mapping are an oversized approximation, not evidence of a 64 KiB chip.
The map/file size has not been changed, preserving compatibility with existing
backing files.

## Technology evidence

- Reads and writes address bytes directly in the 0x100c00-based region. These
  settings paths do not shift an I2C/SPI command stream or use an RTC register
  interface.
- Low-level writer 0x07940c00 reads 0xfffc14, asserts bit 2, writes one byte
  through A2, then clears bit 2. This is consistent with external write gating;
  the physical signal and its polarity at the memory IC are not traced.
- The pending-write engine compares target bytes, programs changed bytes and
  polls readback. Its asynchronous service interval is 0x2710 microseconds
  (10 ms), and the synchronous path additionally uses a DBRA delay initialized
  to **0x960** (2400, not decimal 960).
- No sector-erase or flash unlock sequence appears in this recovered settings
  writer. Firmware-image flash support elsewhere is a separate mechanism.

That behavior is characteristic of byte-programmable parallel EEPROM. For
comparison, the [AT28C256 datasheet](https://ww1.microchip.com/downloads/en/DeviceDoc/doc0006.pdf)
describes a 32,768×8 memory accessed like SRAM, with internally timed writes,
3/10 ms maximum write cycles depending on variant, and data polling. The code's
whole-byte equality polling is compatible with such a device, but does not
establish that it specifically uses the datasheet's I/O7 polling algorithm.

Battery-backed SRAM needs no EEPROM programming delay. Nevertheless, software
can conservatively use the same driver for it: the [DS1230 datasheet](https://www.analog.com/media/en/technical-documentation/data-sheets/DS1230AB-DS1230Y.pdf)
specifies 32,768×8 nonvolatile SRAM and explicitly describes its compatibility
with 28256 EEPROM pinouts. Thus timing alone cannot rule out that alternative.

A DS1287/DS12887-style RTC's internal RAM is too small for this layout. For
comparison the [DS12887](https://www.analog.com/en/products/ds12887.html) provides
114 bytes of general-purpose battery-backed RAM. This rules out that small
internal RAM as the sole configuration store, while leaving an RTC plus separate
larger memory possible. No RTC/calendar access pattern has been identified in
the settings path.

A legible top marking or tracing the candidate's address/data/write-enable pins
would distinguish EEPROM from a battery-backed replacement conclusively.
