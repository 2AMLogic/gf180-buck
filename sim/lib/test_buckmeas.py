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


class LoadStepPairTest(unittest.TestCase):
    TAU = 3e-6
    N_UP, N_DN, N_END = 60, 210, 360  # cycles: up step, step back, end of run

    def wave(self, drift=0.0):
        t = grid(self.N_END)
        t_up, t_dn = self.N_UP * T, self.N_DN * T

        def v(x):
            r = 1.8 + 0.002 * math.sin(2 * math.pi * F * x) + drift * x
            if x >= t_dn:
                r += 0.04 * math.exp(-(x - t_dn) / self.TAU)
            elif x >= t_up:
                r -= 0.05 * math.exp(-(x - t_up) / self.TAU)
            return r
        return t, [v(x) for x in t], [0.25 + triangle(x) for x in t], t_up, t_dn

    def test_known_deviation_and_recovery_both_edges(self):
        t, vout, il, t_up, t_dn = self.wave()
        r = bm.load_step_pair(t, vout, il, F, t_up, t_dn, 0.018)
        up, back = r["up"], r["back"]
        self.assertTrue(up["available"] and back["available"], r)
        self.assertAlmostEqual(up["deviation_v"], 0.05, delta=2e-3)
        self.assertAlmostEqual(up["undershoot_v"], up["deviation_v"], places=9)
        self.assertAlmostEqual(back["overshoot_v"], back["deviation_v"], places=9)
        self.assertAlmostEqual(back["deviation_v"], 0.04, delta=2e-3)
        # last exit from +-18 mV: the 2 mV ripple peak keeps Vout out until the decay is under band - ripple,
        # i.e. tau * ln(dev / (band - ripple))
        self.assertAlmostEqual(up["recovery_time_s"], self.TAU * math.log(0.05 / 0.016), delta=0.15e-6)
        self.assertAlmostEqual(back["recovery_time_s"], self.TAU * math.log(0.04 / 0.016), delta=0.15e-6)
        self.assertTrue(up["run_long_enough"] and back["run_long_enough"])
        self.assertAlmostEqual(up["v_ref_v"], 1.8, delta=1e-3)

    def test_up_step_graded_before_second_edge_cuts_in(self):
        t, vout, il, t_up, t_dn = self.wave()
        up = bm.load_step_pair(t, vout, il, F, t_up, t_dn, 0.018)["up"]
        self.assertLess(up["t_end_s"], t_dn + 1e-12)  # the step back is not part of the up step's window

    def test_unsettled_before_step_reports_no_value(self):
        t, vout, il, t_up, t_dn = self.wave(drift=2000.0)  # 1.8 V drifting 0.1 % per ~0.5 us: not settled
        r = bm.load_step_pair(t, vout, il, F, t_up, t_dn, 0.018)
        self.assertFalse(r["up"]["available"])
        self.assertNotIn("deviation_v", r["up"])
        self.assertIn("not settled", r["up"]["reason"])


class CrossingsTest(unittest.TestCase):
    T = [0.0, 1.0, 2.0, 3.0, 4.0]
    Y = [0.0, 2.0, 0.0, 2.0, 0.0]

    def test_rising_and_falling_interpolated(self):
        self.assertEqual(bm.crossings(self.T, self.Y, 1.0), [0.5, 2.5])
        self.assertEqual(bm.crossings(self.T, self.Y, 1.0, rising=False), [1.5, 3.5])

    def test_t_from_filters_on_the_segment_end(self):
        self.assertEqual(bm.crossings(self.T, self.Y, 1.0, t_from=1.0), [0.5, 2.5])
        self.assertEqual(bm.crossings(self.T, self.Y, 1.0, t_from=2.0), [2.5])

    def test_level_hit_exactly_counts_once_rising(self):
        self.assertEqual(bm.crossings([0.0, 1.0, 2.0], [0.0, 1.0, 2.0], 1.0), [1.0])

    def test_flat_segment_never_divides_by_zero(self):
        self.assertEqual(bm.crossings([0.0, 1.0], [1.0, 1.0], 1.0), [])
        self.assertEqual(bm.crossings([0.0, 1.0], [1.0, 1.0], 1.0, rising=False), [])


class CrosscheckTest(unittest.TestCase):
    def test_within_and_outside_30_percent(self):
        self.assertEqual(bm.crosscheck(0.060, 0.050)["verdict"], "pass")     # +20 %
        self.assertEqual(bm.crosscheck(0.0655, 0.050)["verdict"], "fail")    # +31 %
        self.assertAlmostEqual(bm.crosscheck(0.035, 0.050)["rel_err"], -0.3)  # edge: -30 % passes
        self.assertEqual(bm.crosscheck(0.035, 0.050)["verdict"], "pass")

    def test_zero_prediction_and_missing_values(self):
        self.assertEqual(bm.crosscheck(0.0, 0.0)["verdict"], "pass")
        self.assertEqual(bm.crosscheck(1e-6, 0.0)["verdict"], "fail")
        self.assertEqual(bm.crosscheck(None, 0.05)["verdict"], "no_value")
        self.assertEqual(bm.crosscheck(0.05, None)["verdict"], "no_value")


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

    def test_analyze_columns_matches_analyze(self):
        t = grid(130, T / 200)
        vout = [1.8 + 0.002 * math.sin(2 * math.pi * F * x) for x in t]
        il = [0.25 + triangle(x, pp=0.17) for x in t]
        vsw = [5.0 if (x * F) % 1.0 < 0.36 else 0.0 for x in t]
        pin = [0.5] * len(t)
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "w.dat")
            with open(path, "w") as fh:
                for row in zip(t, vout, il, vsw, pin):
                    fh.write(" ".join(repr(x) for x in row) + "\n")
            kw = dict(f_sw=F, vin=5.0, tier_params={"i_load": 0.25}, step_max=T / 200)
            via_file = bm.analyze(path, **kw)
        self.assertEqual(bm.analyze_columns(t, vout, il, vsw, pin, **kw), via_file)

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


def _ramp_run(v_end=1.8, ramp_s=200e-6, t_en=20e-6, t_stop=400e-6, dip=None, bump=0.0):
    t = grid(int(t_stop / T))
    v = []
    for x in t:
        r = min(max((x - t_en) / ramp_s, 0.0), 1.0) * v_end
        if dip and dip[0] <= x < dip[1]:
            r -= 0.05
        if bump and x > t_en + ramp_s:
            r += bump * math.exp(-(x - t_en - ramp_s) / 20e-6) * math.sin(math.pi * (x - t_en - ramp_s) / 40e-6)
        v.append(r + 0.004 * math.sin(2 * math.pi * F * x))
    edges = [i * T for i in range(len(t) // 100 + 1)]
    return t, v, [0.3] * len(t), edges


class SoftStartTest(unittest.TestCase):
    def meas(self, **kw):
        t, v, il, edges = _ramp_run(**kw)
        return bm.soft_start(t, v, il, edges, t_en=20e-6, v_target=1.8, v_reg_max=1.872)

    def test_linear_ramp_t90_and_monotonic(self):
        r = self.meas()
        self.assertTrue(r["available"], r)
        self.assertAlmostEqual(r["t_90_s"], 0.9 * 200e-6, delta=1e-6)
        self.assertTrue(r["monotonic"], r)
        self.assertEqual(r["overshoot_v"], 0.0)
        self.assertAlmostEqual(r["peak_il_a"], 0.3)

    def test_dip_during_rise_is_not_monotonic(self):
        r = self.meas(dip=(80e-6, 100e-6))
        self.assertFalse(r["monotonic"])
        self.assertGreater(r["max_drawdown_v"], 0.04)

    def test_overshoot_above_r4_max(self):
        r = self.meas(bump=0.3)
        self.assertGreater(r["overshoot_v"], 0.02)
        self.assertLess(r["overshoot_v"], 0.2)

    def test_never_reaching_90_percent_has_no_time(self):
        r = self.meas(v_end=1.5)
        self.assertFalse(r["available"])
        self.assertNotIn("t_90_s", r)


class StepCheckTest(unittest.TestCase):
    """The §0.4 max-step rule, which every collector grades through this one helper."""

    def test_constant_is_the_spec_2p5ns(self):
        self.assertAlmostEqual(bm.STEP_MAX_S, 2.5e-9, places=15)
        self.assertEqual(bm.STEP_MAX_S, 1.0 / (bm.STEP_DIVISOR * bm.F_SW_SPEC_HZ))

    def test_uniform_run_reports_its_step(self):
        t = [k * 2e-9 for k in range(11)]
        max_dt, ok = bm.step_check(t)
        self.assertAlmostEqual(max_dt, 2e-9)
        self.assertTrue(ok)

    def test_tolerance_edge_passes_at_exactly_0p1_percent_over(self):
        # §0.4 is met to STEP_TOL, so a run at exactly step_max*(1+STEP_TOL) still passes ...
        dt = bm.STEP_MAX_S * (1 + bm.STEP_TOL)
        self.assertTrue(bm.step_check([0.0, dt])[1])
        # ... and anything above it does not
        self.assertFalse(bm.step_check([0.0, dt * (1 + 1e-9)])[1])

    def test_largest_step_governs(self):
        t = [0.0, 1e-9, 2e-9, 2e-9 + 4e-9, 2e-9 + 5e-9]  # one 4 ns step among 1 ns ones
        max_dt, ok = bm.step_check(t)
        self.assertAlmostEqual(max_dt, 4e-9)
        self.assertFalse(ok)

    def test_explicit_step_max_overrides_the_default(self):
        t = [0.0, 4e-9]
        self.assertFalse(bm.step_check(t)[1])
        self.assertTrue(bm.step_check(t, 5e-9)[1])


class TripEventTest(unittest.TestCase):
    def test_trip_reports_current_at_assertion(self):
        t = grid(50)
        il = [x / t[-1] * 2.0 for x in t]            # 0 -> 2 A
        trip = [3.3 if i >= 1.2 else 0.0 for i in il]  # asserts at ~1.2 A
        r = bm.trip_event(t, trip, il, 1.65)
        self.assertTrue(r["engaged"])
        self.assertAlmostEqual(r["trip_il_a"], 1.2, delta=0.02)

    def test_no_assertion_is_no_trip_not_a_pass(self):
        t = grid(50)
        il = [0.5] * len(t)
        r = bm.trip_event(t, [0.0] * len(t), il, 1.65)
        self.assertFalse(r["engaged"])
        self.assertIsNone(r["trip_il_a"])
        self.assertEqual(r["n_assertions"], 0)

    def test_assertions_before_t_from_are_ignored(self):
        t = grid(50)
        trip = [3.3 if 10 * T <= x < 12 * T else 0.0 for x in t]
        r = bm.trip_event(t, trip, [0.4] * len(t), 1.65, t_from=20 * T)
        self.assertFalse(r["engaged"])


if __name__ == "__main__":
    unittest.main()
