"""Collector-level tests for the spec 0.4 max-step gate.

`spec/decision-records/0009-max-step-gates-graded-rows.md`: a unit whose largest saved
time step exceeds T/200 contributes no value to any graded row, so every row it feeds is
`not_demonstrated` rather than `pass`. One test class per collector; each shows a unit
that fails **only** the step rule (in bounds otherwise) turning its rows no-value, and the
same unit with a compliant step passing.

The step gate is read off synthetic rawfiles through the real `unit_base` / `grade_unit` /
`unit_record`; the peer units a row needs around it are hand-built dicts of the same shape,
so a row's verdict is judged by the collector's own `judge()`. No saved klt report is
committed, so none is used.

Run: python3 -m unittest discover sim/lib
"""
import importlib.util
import math
import os
import re
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SIM_ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import buckmeas as bm  # noqa: E402

F = 2.0e6                                      # Hz, inside the R7 band: STEP_MAX_S is this run's T/200
T = 1.0 / F
OK_DT = bm.STEP_MAX_S                              # exactly the rule
TOL_DT = bm.STEP_MAX_S * (1 + bm.STEP_TOL / 2.0)   # over the rule but inside its 0.1 % tolerance
BAD_DT = 2.0 * bm.STEP_MAX_S                       # twice the rule: a violation
VIN, VO, DUTY, RIPPLE = 5.0, 1.8, 0.36, 0.15       # RIPPLE p-p is inside the R8 band (0.119 - 0.270 A)
SS_CYCLES = 130      # R7 reads the fundamental over >= 100 settled cycles (buckmeas.MIN_FSW_CYCLES)

# every vector any of the three collectors asks for, including the averaged load-step bench's
ALL_VECTORS = ("time", "i(lind)", "v(out)", "v(sw_d)", "v(vsrc)", "i(vsrc)", "v(xtop.trip)",
               "v(vo)", "i(l1)")


def load_collector(bench):
    """Import sim/<bench>/collect.py by path -- the bench directories carry hyphens."""
    path = os.path.join(SIM_ROOT, bench, "collect.py")
    spec = importlib.util.spec_from_file_location("collect_" + bench.replace("-", "_"), path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def write_raw(path, n_cycles, dt, iload=0.25, names=ALL_VECTORS, i_src=None):
    """A clean, settled synthetic switched run at F, sampled every `dt`.

    `dt` is the whole point: it is the only thing that differs between a unit that passes
    every row and one that fails only the spec 0.4 step rule. Efficiency is fixed at 0.90
    (above the R9 floor) by drawing `iload * 0.4` from the board-side source.
    """
    i_src = iload * 0.4 if i_src is None else i_src
    rows = []
    for k in range(int(round(n_cycles * T / dt)) + 1):
        t = k * dt
        ph = (t * F) % 1.0
        tri = 2.0 * ph if ph < 0.5 else 2.0 * (1.0 - ph)   # 0 -> 1 -> 0 over the cycle
        il = iload + RIPPLE * (tri - 0.5)
        vout = VO + 0.005 * math.sin(2.0 * math.pi * F * t)
        vals = {"time": t, "v(sw_d)": VIN if ph < DUTY else 0.0,
                "i(lind)": il, "i(l1)": il, "v(out)": vout, "v(vo)": vout,
                "v(vsrc)": VIN, "i(vsrc)": -i_src, "v(xtop.trip)": 0.0}
        rows.append([vals.get(n, 0.0) for n in names])
    return _write_rawfile(path, names, rows)


def write_cl_raw(path, dt, *, f=F, vin=VIN, t0=600e-6, span=20e-6, trip_at=None,
                 il0=0.5, il1=0.5, vout=VO):
    """One current-limit bench window: saved from `t0`, switching at `f`, I(L) ramping il0 -> il1.

    TRIP asserts once at `trip_at` (never, when that is None), so the same writer makes both the
    ramp case (a trip whose I(L) is inside the R16 window) and the min case (no trip at all).
    """
    names = ("time", "v(out)", "i(lind)", "v(sw_d)", "v(xtop.trip)")
    n = int(round(span / dt))
    rows = []
    for k in range(n + 1):
        t = t0 + k * dt
        ph = ((t - t0) * f) % 1.0
        tri = 2.0 * ph if ph < 0.5 else 2.0 * (1.0 - ph)
        il = il0 + (il1 - il0) * (k / n) + RIPPLE * (tri - 0.5)
        rows.append([t, vout, il, vin if ph < DUTY else 0.0,
                     3.3 if trip_at is not None and t >= trip_at else 0.0])
    return _write_rawfile(path, names, rows)


def _write_rawfile(path, names, rows):
    out = ["Title: synthetic\nPlotname: Transient Analysis\nFlags: real\n",
           "No. Variables: %d\nNo. Points: %d\nVariables:\n" % (len(names), len(rows))]
    out += ["\t%d\t%s\t%s\n" % (i, n, "time" if n == "time" else "voltage") for i, n in enumerate(names)]
    out.append("Values:\n")
    for k, row in enumerate(rows):
        out.append(" %d\t%.15e\n" % (k, row[0]))
        out += ["\t%.15e\n" % x for x in row[1:]]
    with open(path, "w") as fh:
        fh.write("".join(out))
    return path


def corner(cid, raw):
    return {"corner_id": cid, "status": "pass", "diagnostics": [], "artifacts": {"raw": raw}}


class StepReasonTest(unittest.TestCase):
    """The reason every collector records is one wording, read from the one threshold."""

    def test_reason_names_the_observed_and_the_allowed_step(self):
        r = bm.step_reason(BAD_DT)
        self.assertIn("5e-09", r)
        self.assertIn("2.5e-09", r)
        self.assertIn("0.4", r)

    def test_the_tolerance_edge_is_compliant(self):
        """The collectors call `step_check` with its default threshold, so they inherit the
        0.1 % tolerance exactly: a largest step of `STEP_MAX_S * (1 + STEP_TOL)` still passes.
        Asserted on the helper because a sampled time column cannot land on that edge to the
        last bit; the collector tests use TOL_DT, which is over STEP_MAX_S and inside the band."""
        self.assertTrue(bm.step_check([0.0, bm.STEP_MAX_S * (1 + bm.STEP_TOL)])[1])
        self.assertGreater(TOL_DT, bm.STEP_MAX_S)
        self.assertTrue(bm.step_check([0.0, TOL_DT])[1])
        self.assertFalse(bm.step_check([0.0, BAD_DT])[1])

    def test_no_collector_carries_its_own_copy_of_the_threshold(self):
        for bench in ("current-limit", "load-step", "steady-state", "soft-start"):
            with open(os.path.join(SIM_ROOT, bench, "collect.py")) as fh:
                src = fh.read()
            with self.subTest(bench=bench):
                self.assertNotIn("2.5e-9", src)
                self.assertNotIn("STEP_TOL", src)
                # the only mention of the threshold is a reference to the one definition
                self.assertEqual(re.findall(r"(?<!buckmeas\.)\bSTEP_MAX_S\b", src), [])


class CurrentLimitStepGateTest(unittest.TestCase):
    """R16 trip window and R16 min bound (sim/current-limit/collect.py).

    Both the passing and the gated unit are graded by the real `ramp_unit` / `min_unit` off a
    synthetic bench window, so the only difference between a `pass` row and a `not_demonstrated`
    one is the sample step.
    """

    RAMP_CID = "typical/5.0V/27C/params:i_end=3.0,t_ramp=300e-06"
    MIN_CID = "typical/5.5V/27C/params:iload=0.5,lfac=0.8"
    T_R0 = 600e-6

    @classmethod
    def setUpClass(cls):
        cls.mod = load_collector("current-limit")
        cls.tmp = tempfile.TemporaryDirectory()
        d = cls.tmp.name
        cls.raw = {}
        for label, dt in (("ok", OK_DT), ("tol", TOL_DT), ("bad", BAD_DT)):
            # ramp: I(L) climbs 0.5 -> 2.0 A and TRIP asserts halfway, so the trip current
            # (~1.25 A) sits inside the 0.70 - 2.1 A R16 window
            cls.raw[("ramp", label)] = write_cl_raw(
                os.path.join(d, "ramp-%s.raw" % label), dt,
                trip_at=cls.T_R0 + 10e-6, il0=0.5, il1=2.0)
            # min: 500 mA held, no trip, peak I(L) 0.575 A under the 0.70 A bound, and the
            # free-running clock at 1.6 MHz so the f-min condition is exercised
            cls.raw[("min", label)] = write_cl_raw(
                os.path.join(d, "min-%s.raw" % label), dt,
                f=1.6e6, vin=5.5, trip_at=None, il0=0.5, il1=0.5)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def ramp(self, label):
        return self.mod.ramp_unit(corner(self.RAMP_CID, self.raw[("ramp", label)]))

    def mn(self, label):
        return self.mod.min_unit(corner(self.MIN_CID, self.raw[("min", label)]))

    def test_a_compliant_run_is_still_graded(self):
        for label in ("ok", "tol"):
            u, d = self.mod.unit_base(corner(self.RAMP_CID, self.raw[("ramp", label)]))
            with self.subTest(step=label):
                self.assertTrue(u["graded"])
                self.assertTrue(u["step_ok"])
                self.assertIsNotNone(d, "grading must continue for a compliant run")
                self.assertNotIn("reason", u)

    def test_a_step_violation_is_a_no_value_unit_that_keeps_its_evidence(self):
        u, d = self.mod.unit_base(corner(self.RAMP_CID, self.raw[("ramp", "bad")]))
        self.assertIsNone(d, "no waveform is handed on, so no trip is measured")
        self.assertFalse(u["graded"])
        self.assertFalse(u["step_ok"])
        self.assertAlmostEqual(u["step_max_s"], BAD_DT, delta=1e-14)
        self.assertIn("window_s", u)
        self.assertEqual(u["reason"], bm.step_reason(u["step_max_s"]))

    def test_the_gated_unit_carries_no_trip_value(self):
        for name, u in (("ramp", self.ramp("bad")), ("min", self.mn("bad"))):
            with self.subTest(unit=name):
                self.assertIsNone(u.get("trip_il_a"))
                self.assertNotIn("n_trip_assertions", u)
                self.assertFalse(u["step_ok"])
                self.assertAlmostEqual(u["step_max_s"], BAD_DT, delta=1e-14)

    def test_both_r16_rows_pass_with_a_compliant_grid(self):
        for label in ("ok", "tol"):
            rows = self.mod.judge([self.ramp(label)], [self.mn(label)])
            with self.subTest(step=label):
                self.assertEqual(rows["R16_trip_window"]["verdict"], "pass", rows["R16_trip_window"])
                self.assertEqual(rows["R16_min_bound_no_trip"]["verdict"], "pass",
                                 rows["R16_min_bound_no_trip"])

    def test_the_compliant_unit_really_is_in_bounds_on_every_other_count(self):
        """So a `not_demonstrated` below can only be the step rule, nothing else."""
        r, m = self.ramp("ok"), self.mn("ok")
        self.assertTrue(self.mod.TRIP_BOUNDS[0] <= r["trip_il_a"] <= self.mod.TRIP_BOUNDS[1])
        self.assertTrue(r["in_regulation_at_load_start"])
        self.assertEqual(m["n_trip_assertions"], 0)
        self.assertLess(m["peak_il_a"], self.mod.TRIP_BOUNDS[0])
        self.assertTrue(m["f_min_condition"])

    def test_one_step_violating_unit_makes_both_r16_rows_not_demonstrated(self):
        rows = self.mod.judge([self.ramp("ok"), self.ramp("bad")],
                              [self.mn("ok"), self.mn("bad")])
        trip, mb = rows["R16_trip_window"], rows["R16_min_bound_no_trip"]
        self.assertEqual(trip["verdict"], "not_demonstrated")
        self.assertEqual(trip["n_valued"], 1)
        self.assertEqual(trip["n_no_trip_or_no_value"], 1)
        self.assertEqual(trip["n_out_of_bounds"], 0, "it fails only the step rule")
        self.assertEqual(mb["verdict"], "not_demonstrated")
        self.assertEqual(mb["n_no_waveform"], 1)
        self.assertEqual(mb["n_tripped_or_peak_over_min"], 0)

    def test_a_grid_of_nothing_but_violations_is_never_a_pass(self):
        rows = self.mod.judge([self.ramp("bad")], [self.mn("bad")])
        for name, row in rows.items():
            with self.subTest(row=name):
                self.assertEqual(row["verdict"], "not_demonstrated")


class LoadStepStepGateTest(unittest.TestCase):
    """R12, R13(b) and R13(c) (sim/load-step/collect.py)."""

    CID = "typical/5.0V/27C/params:lfac=1.0,ceff=4.7e-06,esr=0.01"

    @classmethod
    def setUpClass(cls):
        cls.mod = load_collector("load-step")
        cls.tm = cls.mod.bench_timing()
        cls.tmp = tempfile.TemporaryDirectory()
        d = cls.tmp.name
        # grade_unit locks the clock before the step gate, so the run needs >= 41 crossings
        cls.ok = write_raw(os.path.join(d, "ok.raw"), 45, OK_DT)
        cls.tol = write_raw(os.path.join(d, "tol.raw"), 45, TOL_DT)
        cls.bad = write_raw(os.path.join(d, "bad.raw"), 45, BAD_DT)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def gated(self, bench="tol"):
        return self.mod.grade_unit(corner(self.CID, self.bad), bench, self.tm)

    @staticmethod
    def edge_value(dev=0.05, rec=10e-6):
        return {"settled": True, "available": True, "recovered": True, "run_long_enough": True,
                "deviation_v": dev, "recovery_time_s": rec}

    @classmethod
    def unit_pass(cls, uid, lfac=1.0, dev=0.05, rec=10e-6):
        """A hand-built unit inside the R12 bounds on both edges."""
        return {"id": uid, "graded": True, "vin_v": 5.0, "lfac": lfac, "ceff_f": 4.7e-6,
                "esr_ohm": 0.01, "run": {"step_ok": True},
                "up": cls.edge_value(dev, rec), "back": cls.edge_value(dev, rec)}

    def test_a_compliant_run_is_still_graded(self):
        for label, raw in (("exactly the limit", self.ok), ("inside the tolerance", self.tol)):
            u = self.mod.grade_unit(corner(self.CID, raw), "tol", self.tm)
            with self.subTest(step=label):
                self.assertTrue(u["run"]["step_ok"])
                self.assertTrue(u["graded"])
                self.assertIn("up", u, "grading must continue for a compliant run")

    def test_a_step_violation_yields_no_value_for_either_edge(self):
        u = self.gated()
        self.assertFalse(u["graded"])
        self.assertFalse(u["run"]["step_ok"])
        self.assertAlmostEqual(u["run"]["step_max_observed_s"], BAD_DT, delta=1e-14)
        self.assertEqual(u["reason"], bm.step_reason(u["run"]["step_max_observed_s"]))
        self.assertNotIn("up", u)
        self.assertNotIn("back", u)

    def test_r12_passes_without_the_violating_unit(self):
        self.assertEqual(self.mod.judge_r12([self.unit_pass("a")])["verdict"], "pass")

    def test_one_step_violating_unit_makes_r12_not_demonstrated(self):
        g = self.gated()
        row = self.mod.judge_r12([self.unit_pass("a"), g])
        self.assertEqual(row["verdict"], "not_demonstrated")
        self.assertEqual(row["n_steps_no_value"], 2)        # both edges of the gated unit
        self.assertEqual(row["n_steps_failing"], 0)         # it fails only the step rule
        for name in ("up", "back"):
            self.assertIn("%s [%s]" % (g["id"], name), row["no_value_steps"])

    def test_r13b_marks_the_violating_unit_s_tolerance_corner_no_value(self):
        g = self.gated()
        table = self.mod.r13b_table([self.unit_pass("a"), g])
        key = self.mod.tol_key(g)
        self.assertEqual(table[key]["no_value"], 2)
        self.assertEqual(table[key]["fail"], 0)
        self.assertEqual(table[key]["verdict"], "not_demonstrated")

    def test_r13c_passes_without_the_violating_unit(self):
        row = self.mod.r13c([self.unit_pass("sw")], [self.unit_pass("avg")])
        self.assertEqual(row["verdict"], "pass")
        self.assertEqual(row["n_withheld_step_violation"], 0)

    def test_r13c_counts_a_withheld_unit_instead_of_shrinking_silently(self):
        """The finding this row needs its own criterion for: `r13c` only sees graded units, so
        without an explicit count a step violation would leave the row `pass` on a smaller set."""
        g = self.gated()
        row = self.mod.r13c([self.unit_pass("sw"), g], [self.unit_pass("avg")])
        self.assertEqual(row["n_withheld_step_violation"], 1)
        self.assertEqual(row["withheld_step_violation_units"], [g["id"]])
        self.assertEqual(row["n_units"], 1, "the table itself still holds only graded units")
        self.assertEqual(row["n_pass"], 1)
        self.assertEqual(row["verdict"], "not_demonstrated")

    def test_r13c_counts_a_withheld_averaged_unit_too(self):
        g = self.gated("avg")
        row = self.mod.r13c([self.unit_pass("sw")], [self.unit_pass("avg"), g])
        self.assertEqual(row["n_withheld_step_violation"], 1)
        self.assertEqual(row["verdict"], "not_demonstrated")

    def test_a_grid_of_nothing_but_violations_is_never_a_pass(self):
        g = self.gated()
        self.assertEqual(self.mod.judge_r12([g])["verdict"], "not_demonstrated")
        self.assertEqual(self.mod.r13b_table([g])[self.mod.tol_key(g)]["verdict"], "not_demonstrated")
        self.assertEqual(self.mod.r13c([g], [g])["verdict"], "not_demonstrated")


class SteadyStateStepGateTest(unittest.TestCase):
    """R4, R6, R7, R8, R9, R10 and R11 (sim/steady-state/collect.py).

    Every one of the seven rows reads a field set only inside the graded/settled branch, so
    every one of them is gated. R7 is the easy one to miss.
    """

    LOADS = (0.0, 0.05, 0.25, 0.5)
    # the row -> the unit whose value it reads, as (bench, iload)
    GATED_ROWS = {"R4": ("grid", 0.5), "R6": ("grid", 0.0), "R7": ("grid", 0.5),
                  "R8": ("r8", 0.25), "R9": ("grid", 0.25), "R10": ("grid", 0.5),
                  "R11": ("grid", 0.5)}

    @classmethod
    def setUpClass(cls):
        cls.mod = load_collector("steady-state")
        cls.tmp = tempfile.TemporaryDirectory()
        d = cls.tmp.name
        # a settled tail (2 x 20 whole cycles), a 41-crossing clock and R7's >= 100 settled cycles
        want = [("ok", il) for il in cls.LOADS] + [("tol", 0.25)]
        want += [("bad", il) for il in cls.LOADS]
        dts = {"ok": OK_DT, "tol": TOL_DT, "bad": BAD_DT}
        cls.raws = {(lab, il): write_raw(os.path.join(d, "%s-%g.raw" % (lab, il)),
                                        SS_CYCLES, dts[lab], iload=il) for lab, il in want}

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def unit(self, bench, iload, label="ok"):
        cid = "typical/5.0V/27C/params:iload=%g" % iload
        if bench == "r8":
            cid = "typical/5.0V/27C/params:iload=%g,lfac=1.0" % iload
        return self.mod.unit_record(corner(cid, self.raws[(label, iload)]), bench)

    def grid(self, gate=None, label="bad"):
        """The C-typ grid over all four loads, optionally with one unit's run step-violating."""
        return [self.unit("grid", il, label if gate == ("grid", il) else "ok") for il in self.LOADS]

    def r8(self, gate=None, label="bad"):
        return [self.unit("r8", 0.25, label if gate == ("r8", 0.25) else "ok")]

    def test_a_compliant_run_is_still_graded_and_settled(self):
        for label in ("ok", "tol"):
            u = self.unit("grid", 0.25, label)
            with self.subTest(step=label):
                self.assertTrue(u["graded"], u.get("reason"))
                self.assertTrue(u["step_max_ok"])
                self.assertTrue(u["settled"], u.get("reason"))
                self.assertIsNotNone(u.get("vout_v"))
                self.assertIsNotNone(u.get("f_sw_hz"))

    def test_a_step_violation_is_a_no_value_unit_that_keeps_its_evidence(self):
        u = self.unit("grid", 0.25, "bad")
        self.assertFalse(u["graded"])
        self.assertFalse(u["settled"])
        self.assertFalse(u["step_max_ok"], "the flag is recorded ahead of the no-value return")
        self.assertAlmostEqual(u["step_max_s"], BAD_DT, delta=1e-14)
        self.assertEqual(u["reason"], bm.step_reason(u["step_max_s"]))
        for field in ("vout_v", "f_sw_hz", "il_pp_a", "ripple_v", "eta", "pwm"):
            self.assertIsNone(u.get(field), field)

    def test_every_row_passes_with_a_compliant_grid(self):
        rows = self.mod.judge(self.grid(), self.r8())
        expected = {"R4": "pass", "R6": "pass", "R7": "pass", "R8": "pass",
                    "R9": "pass", "R10": "reported", "R11": "pass"}
        for name, verdict in expected.items():
            with self.subTest(row=name):
                self.assertEqual(rows[name]["verdict"], verdict, rows[name])

    def test_each_gated_row_goes_no_value_on_its_own_step_violation(self):
        """All seven rows, one at a time: the violating unit is in bounds on every other count."""
        for name, target in self.GATED_ROWS.items():
            rows = self.mod.judge(self.grid(gate=target), self.r8(gate=target))
            with self.subTest(row=name, gated=target):
                self.assertEqual(rows[name]["verdict"], "not_demonstrated", rows[name])
                self.assertEqual(rows[name].get("n_out_of_bounds", 0), 0,
                                 "the unit fails only the step rule, so nothing is out of bounds")

    def test_an_unsettled_clock_observation_is_not_borrowed_from_a_gated_unit(self):
        """A gated unit records no clock, so it cannot leak into R7's diagnostic block."""
        rows = self.mod.judge(self.grid(gate=("grid", 0.5)), self.r8())
        self.assertNotIn("unsettled_clock_observation_hz", rows["R7"])

    def test_a_grid_of_nothing_but_violations_is_never_a_pass(self):
        grid = [self.unit("grid", il, "bad") for il in self.LOADS]
        rows = self.mod.judge(grid, [self.unit("r8", 0.25, "bad")])
        for name, row in rows.items():
            with self.subTest(row=name):
                self.assertEqual(row["verdict"], "not_demonstrated", row)


if __name__ == "__main__":
    unittest.main()
