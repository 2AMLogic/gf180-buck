"""Unit tests for rawgrade on synthetic ngspice ASCII rawfiles with known answers.

Run: python3 -m unittest discover sim/lib
"""
import math
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rawgrade as rg  # noqa: E402

F = 1.9e6  # deliberately not the 2 MHz buckmeas default: the clock must come from V(sw)
T = 1.0 / F
VIN, ILOAD, VO = 5.0, 0.25, 1.8
DUTY = 0.36
I_SRC = 0.1  # A drawn from the board-side source -> Pin = 0.5 W -> eta = 0.9


def write_raw(path, n_cycles, vout_fn=None, per_cycle=100, t0=0.0, names=None, skip_cycle=None):
    names = names or ["time", "i(lind)", "v(out)", "v(sw_d)", "v(vsrc)", "i(vsrc)"]
    dt = T / per_cycle
    rows = []
    for k in range(int(n_cycles * per_cycle) + 1):
        t = t0 + k * dt
        ph = (t * F) % 1.0
        vsw = VIN if ph < DUTY else 0.0
        if skip_cycle is not None and int((t - t0) * F + 1e-9) == skip_cycle:
            vsw = 0.0
        il = ILOAD + 0.1 * (2 * ph if ph < 0.5 else 2 * (1 - ph)) - 0.05
        vo = vout_fn(t) if vout_fn else VO + 0.005 * math.sin(2 * math.pi * F * t)
        vals = {"time": t, "i(lind)": il, "v(out)": vo, "v(sw_d)": vsw, "v(vsrc)": VIN, "i(vsrc)": -I_SRC}
        rows.append([vals.get(n, 0.0) for n in names])
    with open(path, "w") as fh:
        fh.write("Title: synthetic\nPlotname: Transient Analysis\nFlags: real\n")
        fh.write("No. Variables: %d\nNo. Points: %d\nVariables:\n" % (len(names), len(rows)))
        for i, n in enumerate(names):
            fh.write("\t%d\t%s\t%s\n" % (i, n, "time" if n == "time" else "voltage"))
        fh.write("Values:\n")
        for k, row in enumerate(rows):
            fh.write(" %d\t%.15e\n" % (k, row[0]))
            for x in row[1:]:
                fh.write("\t%.15e\n" % x)


class RawGradeTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "waveform.raw")

    def tearDown(self):
        self.tmp.cleanup()

    def test_settled_run_known_values(self):
        write_raw(self.path, 130)
        r = rg.grade(self.path, VIN, ILOAD, step_max=T / 100 * 1.001)
        self.assertTrue(r["graded"])
        self.assertAlmostEqual(r["clock"]["f_hz"] / F, 1.0, delta=2e-3)
        self.assertTrue(r["settle"]["settled"])
        self.assertAlmostEqual(r["R4_vout_mean"]["mean_v"], VO, delta=2e-3)
        self.assertAlmostEqual(r["R9_R10_efficiency"]["eta"], VO * ILOAD / (VIN * I_SRC), delta=5e-3)
        self.assertTrue(r["R7_f_sw"]["available"])
        self.assertAlmostEqual(r["R7_f_sw"]["hz"] / F, 1.0, delta=2e-3)
        self.assertAlmostEqual(r["R8_il_pp"]["pp_a"], 0.1, delta=5e-3)

    def test_pwm_regularity_flags_a_skipped_pulse(self):
        write_raw(self.path, 60)
        r = rg.grade(self.path, VIN, ILOAD, step_max=T / 100 * 1.001)
        reg = r["pwm_regularity"]
        self.assertAlmostEqual(reg["max_over_median"], 1.0, delta=0.02)
        self.assertAlmostEqual(reg["il_min_a"], ILOAD - 0.05, delta=2e-3)
        write_raw(self.path, 60, skip_cycle=30)  # one pulse missing: the longest gap is ~2 periods
        r = rg.grade(self.path, VIN, ILOAD, step_max=T / 100 * 1.001)
        self.assertGreater(r["pwm_regularity"]["max_over_median"], 1.8)

    def test_drifting_run_reports_no_value(self):
        # Vout ramps 1.0 -> 2.0 V over the run: consecutive windows differ by far more than 0.1 %
        t_end = 130 * T
        write_raw(self.path, 130, vout_fn=lambda t: 1.0 + t / t_end)
        r = rg.grade(self.path, VIN, ILOAD, step_max=T / 100 * 1.001)
        self.assertTrue(r["graded"])
        self.assertFalse(r["settle"]["settled"])
        self.assertFalse(r["R4_vout_mean"]["available"])
        self.assertFalse(r["R7_f_sw"]["available"])
        self.assertFalse(r["R9_R10_efficiency"]["available"])

    def test_clock_phase_offset_does_not_matter(self):
        write_raw(self.path, 130, t0=0.37 * T)
        r = rg.grade(self.path, VIN, ILOAD, step_max=T / 100 * 1.001)
        self.assertTrue(r["settle"]["settled"])
        self.assertAlmostEqual(r["R9_R10_efficiency"]["eta"], 0.9, delta=5e-3)

    def test_too_few_cycles_is_not_graded(self):
        write_raw(self.path, 30)
        r = rg.grade(self.path, VIN, ILOAD, step_max=T / 100 * 1.001)
        self.assertFalse(r["graded"])

    def test_missing_vector_raises(self):
        write_raw(self.path, 5, names=["time", "i(lind)", "v(out)"])
        with self.assertRaises(ValueError):
            rg.read_ascii_raw(self.path)


if __name__ == "__main__":
    unittest.main()
