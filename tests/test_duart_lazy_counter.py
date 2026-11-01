"""Independent event-by-event versus lazy counter specification.

This checks timer arithmetic/observations without compiling MAME. Native
firmware and serial validation are still required after rebuilding.
"""
import copy
import unittest


SECOND = 10**18


class Counter:
    def __init__(self, rate=3686400, preset=2):
        self.rate, self.preset = rate, preset
        self.half, self.ready, self.output = 0, False, False
        self.irq_mask, self.pin, self.serial = False, False, False
        self.events = []
        self.next = self.period()

    def period(self):
        return max(self.preset, 1) * (SECOND // self.rate)

    def advance(self, now):
        while self.next is not None and self.next <= now:
            self.half ^= 1
            if self.pin:
                self.output = not self.output
                self.events.append(('pin', self.next, self.output))
            if self.serial:
                self.events.append(('serial', self.next, self.half))
            if not self.half:
                if self.irq_mask and not self.ready:
                    self.events.append(('irq', self.next, True))
                self.ready = True
            self.next += self.period()

    def change(self, now, name, value):
        self.advance(now)  # synchronize with old register values first
        if name == 'clear':
            self.ready = False
        elif name == 'start':
            self.half = 0
            self.next = now + self.period()
        elif name == 'stop':
            self.next = None
        else:
            setattr(self, name, value)

    def observe(self, now):
        self.advance(now)
        count = None if self.next is None else ((self.next-now)*self.rate // SECOND) & 0xffff
        return self.half, self.ready, count, self.next, self.output, tuple(self.events)


class LazyCounter(Counter):
    def advance(self, now):
        if self.irq_mask or self.pin or self.serial:
            return super().advance(now)
        if self.next is None or self.next > now:
            return
        # One old pending edge, followed by reloads with the current preset.
        while self.next <= now:
            reloads = min(2**32-1, (now-self.next) // self.period())
            self.ready |= reloads != 0 or self.half != 0
            self.half ^= (reloads+1) & 1
            self.next += self.period() * (reloads+1)


class LazyCounterTests(unittest.TestCase):
    def test_edges_and_latch_clears(self):
        for rate in (3686400, 230400):
            for preset in (0, 1, 2, 17, 65535):
                a, b = Counter(rate, preset), LazyCounter(rate, preset)
                p = a.period()
                for now in (0, p-1, p, p+1, 2*p-1, 2*p, 19*p, 20*p+1):
                    self.assertEqual(a.observe(now), b.observe(now))
                    a.change(now, 'clear', None)
                    b.change(now, 'clear', None)
                    self.assertEqual(a.observe(now), b.observe(now))

    def test_mid_period_preset_and_clock_change_keeps_pending_deadline(self):
        a, b = Counter(), LazyCounter()
        p = a.period()
        for now, name, value in ((p//2, 'preset', 17), (p, 'preset', 0),
                                 (11*p, 'rate', 230400), (20*p, 'preset', 9),
                                 (22*p, 'start', None), (23*p, 'stop', None),
                                 (25*p, 'start', None)):
            a.change(now, name, value)
            b.change(now, name, value)
            self.assertEqual(a.observe(now), b.observe(now))
        self.assertEqual(a.observe(1000*p), b.observe(1000*p))

    def test_consumers_resume_with_preserved_phase(self):
        for consumer in ('pin', 'serial', 'irq_mask'):
            a, b = Counter(), LazyCounter()
            p = a.period()
            for tick, name, value in ((11, consumer, True), (17, 'clear', None),
                                      (21, consumer, False), (39, 'clear', None),
                                      (42, consumer, True), (47, consumer, False)):
                now = tick*p + p//3
                a.change(now, name, value)
                b.change(now, name, value)
                self.assertEqual(a.observe(now), b.observe(now))
            self.assertEqual(a.observe(101*p), b.observe(101*p))

    def test_saved_lazy_state_and_long_elapsed_interval(self):
        a, b = Counter(preset=17), LazyCounter(preset=17)
        p = a.period()
        self.assertEqual(a.observe(37*p+1), b.observe(37*p+1))
        restored = copy.deepcopy(b)
        self.assertEqual(a.observe(1000*p), restored.observe(1000*p))
        # C++ coalesces u32-sized chunks; each chunk's phase/latch result
        # must also compose correctly across the wrap boundary.
        edges = 2**32 + 19
        b = LazyCounter()
        next_before = b.next
        b.advance(next_before + (edges-1)*b.period())
        self.assertEqual(b.half, edges & 1)
        self.assertTrue(b.ready)
        self.assertEqual(b.next, next_before + edges*b.period())


if __name__ == '__main__':
    unittest.main()
