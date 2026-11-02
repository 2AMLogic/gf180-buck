"""Unit tests for stressmeas on synthetic waveforms with known answers.

Run: python3 -m unittest discover sim/lib
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import stressmeas as sm  # noqa: E402

VIN = 5.0
PER = 500e-9
DT = 50e-12   # 50 ps synthetic step: inside the 100 ps edge window rule


def ramp(t, t0, dur, a, b):
    if t <= t0:
        return a
    if t >= t0 + dur:
        return b
    return a + (b - a) * (t - t0) / dur


def wave(td_ls_hs=3e-9, td_hs_ls=3e-9, n=4, dt=DT, edge=1e-9, sw_peak=None, sw_trough=None):
    """HS on for 180 ns of each 500 ns period. gh is the PMOS gate (low = on), gl the NMOS gate (high = on).
    Dead times are set at the 0.5*level thresholds' crossings by construction of the ramps."""
    t = [k * dt for k in range(int(n * PER / dt) + 1)]
    gh, gl, sw = [], [], []
    for x in t:
        p = x % PER
        base = x - p
        # HS: gate falls VIN -> 0 (turns on) at t_hs_on, rises at t_hs_off; LS gate high otherwise.
        t_ls_off = base + 20e-9
        t_hs_on = t_ls_off + td_ls_hs
        t_hs_off = base + 200e-9
        t_ls_on = t_hs_off + td_hs_ls
        hs_g = VIN
        if t_hs_on <= x < t_hs_off + 0:
            hs_g = 0.0
        ghv = ramp(x, t_hs_on, edge, VIN, 0.0) if x < t_hs_off else ramp(x, t_hs_off, edge, 0.0, VIN)
        glv = (ramp(x, t_ls_off, edge, 3.3, 0.0) if x < t_ls_on - 1e-12 and x >= t_ls_off else
               (ramp(x, t_ls_on, edge, 0.0, 3.3) if x >= t_ls_on else 3.3))
        if x >= base + 200e-9 + td_hs_ls + edge or x < t_ls_off:
            glv = 3.3
        gh.append(ghv)
        gl.append(glv)
        sw.append(VIN if ghv < 2.5 else 0.0)
    if sw_peak is not None:
        sw[len(sw) // 2] = sw_peak
    if sw_trough is not None:
        sw[len(sw) // 3] = sw_trough
    return t, sw, gh, gl


class StressTest(unittest.TestCase):
    def test_peaks_and_limits(self):
        t, sw, gh, gl = wave(sw_peak=6.3, sw_trough=-0.9)
        vin, gnd = [VIN] * len(t), [0.0] * len(t)
        p = sm.stress_peaks(t, vin, sw, gnd, gh, gl)
        self.assertAlmostEqual(p["sw_min_v"], -0.9)
        self.assertAlmostEqual(p["sw_max_v"], 6.3)
        sw_ok, term_ok = sm.r2_verdict(p)
        self.assertFalse(sw_ok)
        self.assertFalse(term_ok)       # SW at 6.3 V is 6.3 V across the LS drain-source

    def test_inside_limits(self):
        t, sw, gh, gl = wave()
        p = sm.stress_peaks(t, [VIN] * len(t), sw, [0.0] * len(t), gh, gl)
        self.assertEqual(sm.r2_verdict(p), (True, True))
        self.assertLessEqual(p["terminal_max"]["abs_v"], 6.0)

    def test_ground_bounce_counts_against_the_die_ground(self):
        t, sw, gh, gl = wave()
        gnd = [0.3] * len(t)             # die ground 0.3 V above the pin; SW sits at 0 V on the pin
        p = sm.stress_peaks(t, [VIN] * len(t), sw, gnd, gh, gl)
        self.assertAlmostEqual(p["sw_min_vs_gnd_v"], -0.3)
        self.assertAlmostEqual(p["sw_min_v"], -0.3)

    def test_boundary_is_not_relaxed(self):
        self.assertEqual(sm.r2_verdict({"sw_min_v": -0.7, "sw_max_v": 6.0, "terminal_max": {"abs_v": 6.0}}), (True, True))
        self.assertEqual(sm.r2_verdict({"sw_min_v": -0.7001, "sw_max_v": 6.0001, "terminal_max": {"abs_v": 6.0}}), (False, False))


class DeadTimeTest(unittest.TestCase):
    def run_dt(self, ls_hs, hs_ls, vthn=0.686, vthp=0.889):
        t, sw, gh, gl = wave(ls_hs, hs_ls)
        return sm.dead_time(t, [VIN] * len(t), [0.0] * len(t), gh, gl, vthn, vthp, PER, 4 * PER)

    def test_known_dead_times(self):
        r = self.run_dt(3e-9, 4e-9)
        self.assertEqual(r["overlap_s"], 0.0)
        self.assertGreaterEqual(min(r["n_pairs"]), 2)
        # the thresholds are crossed part-way up the 1 ns edges, so the measured value is the commanded
        # delay plus the difference of the two threshold-crossing offsets (within one edge)
        self.assertAlmostEqual(r["min_s"], 3e-9, delta=1e-9)
        self.assertAlmostEqual(r["max_s"], 4e-9, delta=1e-9)

    def test_overlap_is_reported(self):
        r = self.run_dt(-3e-9, 3e-9)     # HS turns on 3 ns before LS has turned off
        self.assertGreater(r["overlap_s"], 1e-9)

    def test_threshold_moves_the_answer(self):
        lo = self.run_dt(3e-9, 3e-9, vthn=0.3, vthp=0.3)
        hi = self.run_dt(3e-9, 3e-9, vthn=2.0, vthp=2.0)
        self.assertNotEqual(round(lo["min_s"], 12), round(hi["min_s"], 12))


class EdgeResolutionTest(unittest.TestCase):
    def test_fine_step_passes_and_coarse_fails(self):
        t, sw, gh, gl = wave(dt=50e-12)
        ok = sm.edge_resolution(t, sw, VIN, gh, gl)
        self.assertTrue(ok["ok"])
        self.assertLessEqual(ok["max_step_s"], 100e-12 + 1e-15)
        t2, sw2, gh2, gl2 = wave(dt=250e-12)
        bad = sm.edge_resolution(t2, sw2, VIN, gh2, gl2)
        self.assertFalse(bad["ok"])
        self.assertGreater(bad["max_step_s"], 100e-12)

    def test_no_edge_is_not_resolved(self):
        t = [k * 50e-12 for k in range(1000)]
        flat = [0.0] * len(t)
        r = sm.edge_resolution(t, flat, VIN, [VIN] * len(t), flat)
        self.assertFalse(r["ok"])
        self.assertIsNone(r["max_step_s"])


if __name__ == "__main__":
    unittest.main()
