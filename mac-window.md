# MAC window and nearby accesses

MNENG3 scan, 2026-10-31. Linked addresses use the existing inferred
file-offset bias 0x07805000. Explicit absolute-long memory operands were
checked in the physical range 0x1fff00..0x2000ff, including 24-bit aliases.
Raw constant matches were filtered using decoded operand addressing modes;
immediate values and coincidental data are not counted as MMIO references.
This does not prove absence of register-indirect or table-derived accesses.

## Confirmed MNENG3 instructions

| Linked instruction | Access | Interpretation |
|---|---|---|
| 0x079409e8 | LEA 0x200000,A1 | The following loop copies six consecutive bytes to A2: the candidate MAC reader. |
| 0x0794470c | TST.B 0x200000 | Startup probe after disabling SIM periodic interrupts and changing TPU priority. Then installs a level-6 autovector entry at VBR+0x78. |
| 0x07944a48 | TST.B 0x200000 | Interrupt-path read, followed by updates of internal software counters. Acknowledge/clear side effect is plausible but unproven. |
| 0x07904388 | ANDI.W #0xfdff,0x200000 | Clears word bit 9, but skipped when board ID is 0x10 or 0x11. |
| 0x079043a6 | ORI.W #0x0200,0x200000 | Sets word bit 9, with the same board-ID guard. |

Board initialization at 0x079406ee assigns board ID 0x10 to RAM field
0x079ac14c, or 0x11 when the profile byte at 0x078051e4 is at least four.
Consequently the word writes are shared-image behavior that the presently
recovered 90TL initialization skips. Do not add a writable MAC latch solely
to satisfy those instructions.

No explicit absolute-long operands target 0x200006..0x2000ff in this scan.
The identity reader reaches 0x200001..0x200005 by incrementing A1, rather
than by separate absolute references. No clock/calendar register sequence
was identified in these routines. This provides no positive evidence for
a DS1287-style RTC at this window.

MNENG1 provides the same six-byte reader at 0x0788d0d4 and base-address TST.B
instructions at 0x07890338 and 0x07890676. MNENG2 has base TST.B references
at 0x0780d682 and 0x0780d758. These addresses describe each file using the
same inferred linked-address bias; they do not establish identical complete
memory maps across images.

## Model implications

The simulator currently supplies synthetic MAC 02:90:00:00:00:01 and no
read side effects. Interrupt-path evidence means that this read-only identity
approximation is incomplete. A shared decode could expose ROM data while
also acknowledging a board timer/interrupt source. The relevant interrupt
source must be identified before implementing acknowledgement semantics.

Keep this window separate from the configuration store accessed relative
to 0x100c00. Missing factory configuration in that store remains a viable
explanation for the current record-bounds failure. Both FF and zero initial
patterns fail, but neither represents a reconstructed valid factory image.
