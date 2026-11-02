"""Unit tests for recordkit / genkit, the shared collector and request-generator plumbing.

Run: python3 -I -m unittest discover sim/lib
"""
import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import genkit  # noqa: E402
import recordkit  # noqa: E402

CID = "ss/5.5V/-40C/params:iload=0.05,lfac=0.8"


class ParseTest(unittest.TestCase):
    def test_corner(self):
        key, params = recordkit.parse_corner(CID)
        self.assertEqual(key, {"process": "ss", "vin_v": 5.5, "temp_c": -40.0})
        self.assertEqual(params, {"iload": 0.05, "lfac": 0.8})

    def test_id_lfac_only_when_present(self):
        self.assertEqual(recordkit.parse_id(CID)["lfac"], 0.8)
        g = "typical/5.0V/27C/params:iload=0.5"
        self.assertNotIn("lfac", recordkit.parse_id(g))
        self.assertEqual(recordkit.parse_id(g, lfac_default=1.0)["lfac"], 1.0)
        self.assertEqual(recordkit.parse_id(g)["iload_a"], 0.5)

    def test_bad_id(self):
        with self.assertRaises(ValueError):
            recordkit.parse_corner("nonsense")


class WriteTest(unittest.TestCase):
    def test_append_only(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "records", "r.json")
            with redirect_stdout(io.StringIO()):
                self.assertEqual(recordkit.write_record(p, {"a": 1}), 0)
            first = open(p).read()
            err = io.StringIO()
            with redirect_stderr(err):
                self.assertEqual(recordkit.write_record(p, {"a": 2}), 1)
            self.assertIn("append-only", err.getvalue())
            self.assertEqual(open(p).read(), first)
            self.assertEqual(json.loads(first), {"a": 1})

    def test_dry_writes_nothing(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "r.json")
            with redirect_stdout(io.StringIO()):
                self.assertEqual(recordkit.write_record(p, {}, dry=True), 0)
            self.assertFalse(os.path.exists(p))


class EnvTest(unittest.TestCase):
    REP = {"status": "pass", "environment": {"remote": {"provider": "p", "job_id": "j", "state": "done", "jobs": [1]}}}

    def test_remote_subset(self):
        self.assertEqual(recordkit.remote_subset(self.REP, ("provider", "state", "instance_type")),
                         {"provider": "p", "state": "done", "instance_type": None})
        self.assertEqual(recordkit.remote_subset({}), {k: None for k in recordkit.REMOTE_FIELDS})

    def test_report_env(self):
        e = recordkit.report_env(self.REP, "/x/rep.json", jobs=True)
        self.assertEqual((e["report"], e["status"], e["jobs"]), ("rep.json", "pass", [1]))
        self.assertNotIn("jobs", recordkit.report_env(self.REP, "rep.json"))

    def test_files_sha256_pins_shared_module(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "bench.spice"), "w") as fh:
                fh.write("x")
            h = recordkit.files_sha256(d, ("bench.spice",), lib_files=("rawgrade.py",))
            self.assertEqual(list(h), ["bench.spice", "sim/lib/rawgrade.py", "sim/lib/recordkit.py"])
            self.assertEqual(h["sim/lib/recordkit.py"], recordkit.sha256(recordkit.__file__))


class GenkitTest(unittest.TestCase):
    def test_process_bundles(self):
        by = {p["name"]: p["sections"] for p in genkit.PROCESS}
        self.assertEqual(by["ff"], ["ff", "mimcap_ff", "cap_mim", "res_ff"])
        self.assertEqual(by["fs"], ["fs", "mimcap_typical", "cap_mim", "res_typical"])  # MOS-only skew

    def test_request_and_matrix(self):
        c = {"process": genkit.PROCESS[:1], "supply_v": {"vsrc": [5.0]}, "temperature_c": [27], "params": {"iload": [0.1]}}
        r = genkit.request(c, "1n 1u", [genkit.vout_last(9)], {"o": 1})
        self.assertEqual(list(r), ["netlist", "engine", "models", "analysis", "corners", "measurements", "batch", "options"])
        self.assertEqual(r["measurements"][0]["spice"], ".meas tran vout_last FIND v(out) AT=9u")
        self.assertEqual(r["batch"], {"max_units_per_job": 1, "max_concurrent_jobs": 12})
        self.assertEqual(list(genkit.request(c, "t", [], {}, [{"x": 1}]))[-1], "exclude")
        self.assertEqual(genkit.matrix(c), c)
        self.assertEqual(genkit.matrix(c, [1])["exclude"], [1])


if __name__ == "__main__":
    unittest.main()
