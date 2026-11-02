"""Tests for sim/device-stress: verdict rules of collect.py, request/bench drift guards.

Run: python3 -m unittest discover sim/lib
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
DS = os.path.join(ROOT, "sim", "device-stress")
sys.path.insert(0, DS)
sys.path.insert(0, HERE)
import collect  # noqa: E402


def unit(uid, sw_min=0.0, term=5.0, settled=True, edge_ok=True, dead=(2e-9, 4e-9), overlap=0.0):
    p = {"sw_min_v": sw_min, "sw_max_v": 5.0, "terminal_max": {"abs_v": term}}
    d = {"min_s": dead[0], "max_s": dead[1], "overlap_s": overlap}
    return {"id": uid, "peaks": p, "settled": settled, "edge": {"ok": edge_ok}, "dead_time": d,
            "dead_time_saved_window": d}


def row(units, fn, expected):
    return collect.judge(units, "x", fn, expected, "t", {})


class VerdictTest(unittest.TestCase):
    def test_complete_clean_set_passes(self):
        n = collect.EXPECTED["grid"]
        r = row([unit("u%d" % i) for i in range(n)], collect.r2_margin, n)
        self.assertEqual(r["verdict"], "pass")
        self.assertTrue(r["corner_set_complete"])

    def test_clean_ctyp_subset_is_not_demonstrated(self):
        n = collect.EXPECTED["ctyp"]
        for fn in (collect.r2_margin, collect.r14_margin):
            r = row([unit("u%d" % i) for i in range(n)], fn, n)
            self.assertEqual(r["verdict"], "not_demonstrated")
            self.assertFalse(r["corner_set_complete"])

    def test_ctyp_subset_with_a_failure_still_fails(self):
        n = collect.EXPECTED["ctyp"]
        us = [unit("u%d" % i) for i in range(n - 1)] + [unit("bad", sw_min=-0.71)]
        self.assertEqual(row(us, collect.r2_margin, n)["verdict"], "fail")

    def test_134_of_135_clean_is_not_demonstrated(self):
        n = collect.EXPECTED["grid"] - 1
        self.assertEqual(row([unit("u%d" % i) for i in range(n)], collect.r2_margin, 135)["verdict"], "not_demonstrated")

    def test_135_with_one_no_value_unit_is_not_demonstrated(self):
        n = collect.EXPECTED["grid"]
        us = [unit("u%d" % i) for i in range(n - 1)] + [unit("x", settled=False)]
        self.assertEqual(row(us, collect.r2_margin, n)["verdict"], "not_demonstrated")

    def test_subset_cannot_pass_the_row(self):
        r = row([unit("a"), unit("b")], collect.r2_margin, 135)
        self.assertEqual(r["verdict"], "not_demonstrated")
        self.assertFalse(r["corner_set_complete"])

    def test_unsettled_run_yields_no_value(self):
        r = row([unit("a"), unit("b", settled=False)], collect.r2_margin, 2)
        self.assertEqual(r["verdict"], "not_demonstrated")
        self.assertEqual(r["no_value_units"], ["b"])

    def test_unresolved_edges_cannot_pass(self):
        r = row([unit("a", edge_ok=False)], collect.r2_margin, 1)
        self.assertEqual(r["verdict"], "not_demonstrated")

    def test_exceedance_fails_even_when_unsettled_and_unresolved(self):
        r = row([unit("a"), unit("b", sw_min=-0.71, settled=False, edge_ok=False)], collect.r2_margin, 2)
        self.assertEqual(r["verdict"], "fail")
        self.assertEqual(r["failing_units"], ["b"])
        self.assertEqual(r["binding"]["id"], "b")

    def test_six_volts_exactly_is_not_a_failure(self):
        self.assertGreaterEqual(collect.r2_margin(unit("a", term=6.0)), 0)
        self.assertLess(collect.r2_margin(unit("a", term=6.01)), 0)

    def test_dead_time_band_and_overlap(self):
        full = collect.EXPECTED["grid"]
        self.assertEqual(row([unit("u%d" % i, dead=(1e-9, 6e-9)) for i in range(full)], collect.r14_margin, full)["verdict"], "pass")
        self.assertEqual(row([unit("a", dead=(0.9e-9, 5e-9))], collect.r14_margin, 1)["verdict"], "fail")
        self.assertEqual(row([unit("a", dead=(2e-9, 6.1e-9))], collect.r14_margin, 1)["verdict"], "fail")
        self.assertEqual(row([unit("a", overlap=1e-12)], collect.r14_margin, 1)["verdict"], "fail")

    def test_missing_threshold_gives_no_value(self):
        u = unit("a")
        u["dead_time"] = None
        self.assertEqual(row([u], collect.r14_margin, 1)["verdict"], "not_demonstrated")

    def test_corner_id_parse(self):
        k = collect.parse_id("sf/5.500V/-40C/params:iload=0.05")
        self.assertEqual((k["process"], k["vin_v"], k["temp_c"], k["iload_a"]), ("sf", 5.5, -40.0, 0.05))


class DriftTest(unittest.TestCase):
    def test_bench_is_the_steady_state_bench(self):
        ss = open(os.path.join(ROOT, "sim", "steady-state", "bench.spice")).read().splitlines()
        ds = open(os.path.join(DS, "bench.spice")).read().splitlines()
        for line in ss:
            if line.startswith("* gf180-buck steady-state bench") or line.startswith(".include opamp_two_stage"):
                continue
            if line.startswith("* external P-T parts") or line.startswith("* Body for"):
                pass
            self.assertIn(line, ds, "steady-state bench line missing from device-stress bench: %r" % line)
        self.assertIn(".include ../steady-state/opamp_two_stage.spice", ds)

    def test_generated_requests_match_committed_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            # the generator imports sim/lib/genkit.py as ../lib/genkit.py: mirror that layout under tmp
            out = os.path.join(tmp, "device-stress")
            os.makedirs(out)
            shutil.copy(os.path.join(DS, "gen_requests.py"), out)
            shutil.copytree(os.path.join(ROOT, "sim", "lib"), os.path.join(tmp, "lib"))
            subprocess.run([sys.executable, "-I", os.path.join(out, "gen_requests.py")], check=True)
            for f in ("request_grid.json", "request_ctyp.json", "matrix_grid.json", "matrix_ctyp.json"):
                self.assertEqual(json.load(open(os.path.join(out, f))), json.load(open(os.path.join(DS, f))), f)

    def test_request_states_the_100ps_step_and_c_full(self):
        req = json.load(open(os.path.join(DS, "request_grid.json")))
        self.assertTrue(req["analysis"]["args"].startswith("100p "))
        self.assertEqual(req["analysis"]["args"].split()[-1], "100p")        # tmax
        c = req["corners"]
        self.assertEqual(len(c["process"]) * len(c["temperature_c"]) * len(c["supply_v"]["vsrc"]), 45)
        self.assertEqual(c["params"]["iload"], [0.0, 0.05, 0.5])


if __name__ == "__main__":
    unittest.main()
