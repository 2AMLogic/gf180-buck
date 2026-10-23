"""Unit tests for buckmeas on synthetic waveforms with known answers.

Run: python3 -m unittest discover sim/lib
"""
import json
import math
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import buckmeas as bm  # noqa: E402

F = 2e6
T = 1.0 / F
DT = T / 100  # synthetic step, finer than the T/200 rule is not needed here


def grid(n_cycles, dt=DT):
    n = int(round(n_cycles * T / dt))
    return [i * dt for i in range(n + 1)]


def triangle(t, f=F, pp=0.2):
    ph = (t * f) % 1.0
    return pp * (2 * ph if ph < 0.5 else 2 * (1 - ph)) - pp / 2


class SettleTest(unittest.TestCase):
    def test_sine_plus_triangle_is_settled(self):
        t = grid(120)
        vout = [1.8 + 0.01 * math.sin(2 * math.pi * F * x) for x in t]
        il = [0.25 + triangle(x) for x in t]
        s = bm.settle(t, vout, il, F)
        self.assertTrue(s["settled"], s)
        self.assertLess(s["mean_vout_delta_rel"], 1e-6)
        # Whole run is steady, so the chain reaches back to the first window.
        self.assertAlmostEqual(s["settled_since_s"], 0.0, delta=T)
        self.assertEqual(len(s["measure_window_s"]), 2)

    def test_never_settling_ramp_is_not_settled(self):
        t = grid(120)
        vout = [1.8 * x / t[-1] for x in t]
        il = [0.25 * x / t[-1] for x in t]
        s = bm.settle(t, vout, il, F)
        self.assertFalse(s["settled"])
        self.assertGreater(s["mean_vout_delta_rel"], bm.MEAN_TOL)

    def test_current_peak_drift_alone_fails(self):
        t = grid(120)
        vout = [1.8] * len(t)
        il = [0.25 * (1 + 0.1 * x / t[-1]) for x in t]
        self.assertFalse(bm.settle(t, vout, il, F)["settled"])

    def test_shorter_than_two_windows_is_not_settled(self):
        t = grid(39)
        s = bm.settle(t, [1.8] * len(t), [0.25] * len(t), F)
        self.assertFalse(s["settled"])
        self.assertIsNone(s["mean_vout_delta_rel"])
        self.assertIn("shorter", s["reason"])


class FrequencyTest(unittest.TestCase):
    def square(self, n_cycles, vin=5.0, f=F):
        t = grid(n_cycles, T / 200)
        return t, [vin if (x * f) % 1.0 < 0.36 else 0.0 for x in t]

    def test_measures_fundamental(self):
        t, vsw = self.square(150)
        r = bm.switching_frequency(t, vsw, 5.0, 10 * T, 150 * T)
        self.assertTrue(r["available"])
        self.assertAlmostEqual(r["hz"], F, delta=F * 1e-3)
        self.assertGreaterEqual(r["cycles"], 100)

    def test_refuses_below_100_cycles(self):
        t, vsw = self.square(150)
        r = bm.switching_frequency(t, vsw, 5.0, 10 * T, 90 * T)
        self.assertFalse(r["available"])
        self.assertIsNone(r["hz"])

    def test_edge_ringing_is_not_counted(self):
        t, vsw = self.square(150)
        # Ring around the rail after each rising edge, crossing vin/2 downward
        # and upward again.
        ring = [v + (3.0 * math.exp(-((x * F) % 1.0 - 0.0) * 40) * math.sin(2 * math.pi * 50 * F * x)
                     if v > 4 else 0.0) for x, v in zip(t, vsw)]
        r = bm.switching_frequency(t, ring, 5.0, 10 * T, 150 * T)
        self.assertAlmostEqual(r["hz"], F, delta=F * 1e-2)


class RippleTest(unittest.TestCase):
    def test_lowpass_gain_and_attenuation(self):
        t = [i * 0.2e-9 for i in range(5001)]  # 1 us, 25 samples per 200 MHz period
        slow = bm.lowpass(t, [math.sin(2 * math.pi * 5e6 * x) for x in t], 20e6)
        # |H| = 1/sqrt(1+(5/20)^2) = 0.970 at 5 MHz
        self.assertAlmostEqual(max(slow[len(t) // 2:]), 0.970, delta=0.01)
        fast = bm.lowpass(t, [math.sin(2 * math.pi * 200e6 * x) for x in t], 20e6)
        # |H| = 1/sqrt(1+(f/fc)^2) = 0.0995 at 200 MHz
        self.assertAlmostEqual(max(fast[len(t) // 2:]), 0.0995, delta=0.01)


class EfficiencyTest(unittest.TestCase):
    def test_partial_last_cycle_is_excluded(self):
        # 60 whole cycles plus a 0.4-cycle tail where Pin is 100x larger.
        n = 60.4
        t = grid(n)
        vout = [1.8] * len(t)
        cut = 60 * T
        pin = [0.5 if x <= cut + 1e-12 else 50.0 for x in t]
        e = bm.efficiency(t, vout, pin, 0.25, F)
        self.assertAlmostEqual(e["t_end_s"], 60 * T, delta=1e-12)
        self.assertAlmostEqual(e["eta"], 0.45 / 0.5, delta=1e-3)
        self.assertEqual(e["cycles"], 20.0)

    def test_window_before_data_raises(self):
        t = grid(10)
        with self.assertRaises(ValueError):
            bm.efficiency(t, [1.8] * len(t), [0.5] * len(t), 0.25, F)


class LoadStepTest(unittest.TestCase):
    def step_wave(self, tau, depth, n_after=300, sign=-1):
        t = grid(100 + n_after)
        ts = 100 * T
        v = [1.8 if x < ts else 1.8 + sign * depth * math.exp(-(x - ts) / tau) for x in t]
        return t, v, ts

    def test_known_recovery_time_and_deviation(self):
        tau, depth, band = 20 * T, 0.09, 0.018
        t, v, ts = self.step_wave(tau, depth)
        r = bm.load_step(t, v, ts, 1.8, band, F)
        self.assertTrue(r["recovered"])
        self.assertAlmostEqual(r["deviation_v"], depth, delta=1e-3)
        self.assertAlmostEqual(r["undershoot_v"], depth, delta=1e-3)
        self.assertEqual(r["overshoot_v"], 0.0)
        expected = tau * math.log(depth / band)
        self.assertAlmostEqual(r["recovery_time_s"], expected, delta=2 * DT)
        self.assertTrue(r["run_long_enough"])

    def test_deviation_is_larger_of_under_and_overshoot(self):
        t, v, ts = self.step_wave(20 * T, 0.05, sign=+1)
        r = bm.load_step(t, v, ts, 1.8, 0.018, F)
        self.assertAlmostEqual(r["deviation_v"], r["overshoot_v"])
        self.assertGreater(r["overshoot_v"], r["undershoot_v"])

    def test_never_recovering_reports_none(self):
        t, v, ts = self.step_wave(1e3 * T, 0.09)
        r = bm.load_step(t, v, ts, 1.8, 0.018, F)
        self.assertFalse(r["recovered"])
        self.assertIsNone(r["recovery_time_s"])

    def test_late_recovery_needs_20_cycles_in_band(self):
        # Recovers 10 cycles before the run ends: not enough in-band time.
        tau, depth, band = 20 * T, 0.09, 0.018
        t_rec = tau * math.log(depth / band)
        n_after = int(t_rec / T) + 10
        t, v, ts = self.step_wave(tau, depth, n_after=n_after)
        r = bm.load_step(t, v, ts, 1.8, band, F)
        self.assertFalse(r["recovered"])


class IdealVoutTest(unittest.TestCase):
    def test_formula(self):
        v = bm.ideal_vout(5.0, 0.36, 0.25, dcr=0.1, r_wire=0.1, wires=2, ron_hs=0.01, ron_ls=0.01)
        r = 0.1 + 0.05 + 0.36 * 0.06 + 0.64 * 0.06
        self.assertAlmostEqual(v, 1.8 - 0.25 * r)


class WrdataTest(unittest.TestCase):
    def write(self, text):
        fh = tempfile.NamedTemporaryFile("w", suffix=".dat", delete=False)
        self.addCleanup(os.unlink, fh.name)
        fh.write(text)
        fh.close()
        return fh.name

    def test_singlescale_and_paired_layouts(self):
        single = self.write("0 1 2 3 4\n1 5 6 7 8\n")
        paired = self.write("0 1 0 2 0 3 0 4\n1 5 1 6 1 7 1 8\n")
        a, b = bm.read_wrdata(single), bm.read_wrdata(paired)
        self.assertEqual(a, b)
        self.assertEqual(a["pin"], [4.0, 8.0])

    def test_header_skipped_and_bad_width_rejected(self):
        ok = self.write("time v(out) il vsw pin\n0 1 2 3 4\n")
        self.assertEqual(bm.read_wrdata(ok)["t"], [0.0])
        with self.assertRaises(ValueError):
            bm.read_wrdata(self.write("0 1 2\n"))


class AnalyzeTest(unittest.TestCase):
    def test_end_to_end_on_synthetic_run(self):
        n = 260.4  # 0.4-cycle partial tail
        t = grid(n, T / 200)
        vin, i_load = 5.0, 0.25
        vout = [1.8 + 0.002 * math.sin(2 * math.pi * F * x) for x in t]
        il = [i_load + triangle(x, pp=0.17) for x in t]
        vsw = [vin if (x * F) % 1.0 < 0.36 else 0.0 for x in t]
        pin = [0.5] * len(t)
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "w.dat")
            with open(path, "w") as fh:
                for row in zip(t, vout, il, vsw, pin):
                    fh.write(" ".join(repr(x) for x in row) + "\n")
            params = {"i_load": i_load}
            res = bm.analyze(path, f_sw=F, vin=vin, tier_params=params, step_max=T / 200)
        json.dumps(res)  # serialisable
        self.assertTrue(res["settle"]["settled"])
        self.assertTrue(res["run"]["step_ok"])
        self.assertAlmostEqual(res["R4_vout_mean"]["mean_v"], 1.8, delta=1e-4)
        self.assertAlmostEqual(res["R8_il_pp"]["pp_a"], 0.17, delta=2e-3)
        self.assertTrue(res["R7_f_sw"]["available"])
        self.assertAlmostEqual(res["R9_R10_efficiency"]["eta"], 0.9, delta=1e-3)
        for key in ("R4_vout_mean", "R8_il_pp", "R9_R10_efficiency", "R11_ripple"):
            self.assertEqual(res[key]["cycles"], 20.0)

    def test_short_run_reports_not_settled_and_no_values(self):
        t = grid(30, T / 200)
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "w.dat")
            with open(path, "w") as fh:
                for x in t:
                    fh.write(f"{x!r} 1.8 0.25 0 0.5\n")
            res = bm.analyze(path, f_sw=F, vin=5.0, tier_params={"i_load": 0.25}, step_max=T / 200)
        self.assertFalse(res["settle"]["settled"])
        for key in ("R4_vout_mean", "R7_f_sw", "R8_il_pp", "R9_R10_efficiency", "R11_ripple"):
            self.assertFalse(res[key]["available"])
            self.assertNotIn("mean_v", res[key])


if __name__ == "__main__":
    unittest.main()
