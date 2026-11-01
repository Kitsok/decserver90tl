"""Offline differential model of the pinned Musashi DBRA/prefetch path.

These checks validate the batching arithmetic and firmware signature, not the
compiled CPU adapter. Firmware A/B validation remains required on the target.
"""
from pathlib import Path
import unittest


PC = 0x07940c2c


def interpret(counter, budget, wait, batch=False):
    # Begin at the steady-state fetch boundary left by a taken DBRA.
    pc, prefetch = PC, PC + 4
    original_high = counter & 0xffff0000
    if batch:
        low = counter & 0xffff
        if 0 < low <= 0x960 and budget > 1:
            count = min(low, (budget - 1) // (4 + 3 * wait))
            counter = original_high | (low - count)
            budget -= count * (4 + 3 * wait)
    while budget > 0 and pc == PC:
        # m68ki_read_imm_16: opcode cache miss, then prefetch displacement.
        budget -= wait
        pc += 2
        prefetch = pc
        budget -= wait
        low = ((counter & 0xffff) - 1) & 0xffff
        counter = original_high | low
        if low != 0xffff:
            # OPER_I_16 hits prefetched displacement and prefetches PC+4.
            pc += 2
            prefetch = pc
            budget -= wait
            pc -= 2
            pc -= 2  # branch displacement -2
        else:
            pc += 2
            budget -= 4  # CPU32 expired-counter adjustment
        budget -= 4  # CPU32 DBRA cycle-table entry
    return counter, budget, pc, prefetch


class ProgrammingDelayTests(unittest.TestCase):
    def test_batch_matches_interpreter_at_slice_or_loop_exit(self):
        for wait in (0, 1, 2, 16):
            for low in (0, 1, 2, 3, 9, 0x95f, 0x960, 0x961, 0xffff):
                for high in (0, 0xa5a50000):
                    for budget in (*range(1, 65), 127, 1000, 1792, 50000):
                        counter = high | low
                        self.assertEqual(interpret(counter, budget, wait),
                                         interpret(counter, budget, wait, batch=True),
                                         (counter, budget, wait))

    def test_original_firmware_contains_only_the_expected_delay(self):
        root = Path(__file__).resolve().parents[1]
        image = (root/'firmware/MNENG3.SYS').read_bytes()
        offset = PC - 0x07805000
        self.assertEqual(image[offset-6:offset+8], bytes.fromhex(
            '283c00000960'  # move.l #$960,d4
            '51ccfffe'      # dbra d4,PC
            '4cdf0010'))    # movem.l (a7)+,d4


if __name__ == '__main__':
    unittest.main()
