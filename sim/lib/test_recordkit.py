"""Unit tests for recordkit / genkit, the shared collector and request-generator plumbing.

Run: python3 -I -m unittest discover sim/lib
"""
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import genkit  # noqa: E402
import recordkit  # noqa: E402

CID = "ss/5.5V/-40C/params:iload=0.05,lfac=0.8"
KLT = shutil.which("klt")



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

    def test_runner_provenance_is_carried(self):
        """The four provenance fields by name: the runner's klt, not the grading host's, is what a
        batch-fleet record needs, and an older report (or a local run) degrades to None."""
        provenance = {"runner_klt_version": "0.9.0", "client_klt_version": "0.9.0",
                      "runner_compatibility": "match", "region": "us-east-1"}
        rep = {"environment": {"remote": dict(provenance, job_id="j")}}
        sub = recordkit.remote_subset(rep)
        for k, v in provenance.items():
            self.assertEqual(sub[k], v, k)
        e = recordkit.report_env(dict(rep, status="pass"), "/x/rep.json")
        for k, v in provenance.items():
            self.assertEqual(e["remote"][k], v, k)
        empty = recordkit.remote_subset({})
        for k in provenance:
            self.assertIsNone(empty[k], k)

    def test_files_sha256_pins_shared_module(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "bench.spice"), "w") as fh:
                fh.write("x")
            h = recordkit.files_sha256(d, ("bench.spice",), lib_files=("rawgrade.py",))
            self.assertEqual(list(h), ["bench.spice", "sim/lib/rawgrade.py", "sim/lib/recordkit.py"])
            self.assertEqual(h["sim/lib/recordkit.py"], recordkit.sha256(recordkit.__file__))


class WaveformOrReasonTest(unittest.TestCase):
    """The one no-waveform guard: which klt corners carry a value, and what the others record."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.raw = os.path.join(self.tmp.name, "waveform.raw")
        with open(self.raw, "w") as fh:
            fh.write("x")

    def tearDown(self):
        self.tmp.cleanup()

    def corner(self, status="pass", raw="?", diagnostics=None):
        c = {"corner_id": CID, "status": status,
             "artifacts": {"raw": self.raw if raw == "?" else raw}}
        if diagnostics is not None:
            c["diagnostics"] = diagnostics
        return c

    def test_pass_and_fail_with_a_raw_on_disk_grade(self):
        for status in ("pass", "fail"):
            raw, reason = recordkit.waveform_or_reason(self.corner(status=status))
            self.assertEqual(raw, self.raw)
            self.assertIsNone(reason)

    def test_other_statuses_carry_no_value(self):
        for status in ("timeout", "error", "skipped", None):
            raw, reason = recordkit.waveform_or_reason(self.corner(status=status))
            self.assertIsNone(raw)
            self.assertEqual(reason, "no waveform: klt status %s []" % status)

    def test_pass_but_the_raw_file_is_missing(self):
        raw, reason = recordkit.waveform_or_reason(
            self.corner(raw=os.path.join(self.tmp.name, "gone.raw")))
        self.assertIsNone(raw)
        self.assertEqual(reason, "no waveform: klt status pass []")

    def test_pass_but_no_raw_named_at_all(self):
        for corner in ({"status": "pass"},                    # no artifacts key
                       {"status": "pass", "artifacts": {}},   # artifacts, no raw
                       self.corner(raw="")):                  # raw named as an empty string
            raw, reason = recordkit.waveform_or_reason(corner)
            self.assertIsNone(raw)
            self.assertEqual(reason, "no waveform: klt status pass []")

    def test_reason_carries_the_first_diagnostic_code_and_message(self):
        _, reason = recordkit.waveform_or_reason(self.corner(
            status="timeout",
            diagnostics=[{"code": "sim_timeout", "message": "ngspice exceeded the 900 s wall clock"},
                         {"code": "ignored", "message": "second diagnostic is not recorded"}]))
        self.assertEqual(
            reason,
            "no waveform: klt status timeout "
            "[('sim_timeout', 'ngspice exceeded the 900 s wall clock')]")

    def test_long_message_is_truncated_to_its_tail(self):
        msg = "A" * 50 + "B" * 120
        _, reason = recordkit.waveform_or_reason(
            self.corner(status="error", diagnostics=[{"code": "spice_error", "message": msg}]))
        self.assertIn("B" * recordkit.DIAG_MSG_TAIL, reason)
        self.assertNotIn("A", reason)

    def test_diagnostic_without_a_message(self):
        _, reason = recordkit.waveform_or_reason(
            self.corner(status="error", diagnostics=[{"code": "spice_error"}]))
        self.assertEqual(reason, "no waveform: klt status error [('spice_error', '')]")


class CornerMatrixCheckTest(unittest.TestCase):
    """corner_matrix_check: the parsed verdict on exit 0 AND exit 3, and a klt refusal as an
    error block instead of an exception. klt is mocked so the suite runs before CI installs
    it; CornerMatrixCheckKltTest runs the real binary where it exists."""

    VERDICT = {"matrix": "/x/matrix_grid.json", "mode": "report", "source": "/y/rep.json",
               "complete": True, "matrix_size": 3, "observed_count": 3,
               "missing": [], "extra": [], "duplicate": [],
               "not_simulated": [], "non_finite": [], "out_of_bounds": []}

    def run_check(self, returncode, stdout="", stderr=""):
        result = subprocess.CompletedProcess(["klt"], returncode, stdout=stdout, stderr=stderr)
        with mock.patch.object(recordkit.subprocess, "run", return_value=result):
            return recordkit.corner_matrix_check("/x/matrix_grid.json", "/y/rep.json")

    def test_complete_verdict_is_parsed_on_exit_0(self):
        e = self.run_check(0, json.dumps(self.VERDICT))
        self.assertNotIn("error", e)
        self.assertEqual((e["matrix"], e["report"]), ("matrix_grid.json", "rep.json"))
        for k in ("matrix_size", "observed_count", "missing", "extra", "duplicate",
                  "not_simulated", "non_finite", "out_of_bounds"):
            self.assertEqual(e[k], self.VERDICT[k], k)

    def test_incomplete_verdict_is_parsed_on_exit_3(self):
        """klt exits 3 when the grid is not covered: a verdict, not a refusal -- the exit
        status is klt's own complete flag folded with the per-corner verdicts, never a gate."""
        v = dict(self.VERDICT, complete=False, missing=["typical/5.000V/27C/params:iload=0.1"])
        e = self.run_check(3, json.dumps(v))
        self.assertNotIn("error", e)
        self.assertEqual(e["missing"], ["typical/5.000V/27C/params:iload=0.1"])

    def test_refusal_envelope_comes_back_as_an_error_block(self):
        env = {"error": {"command": "corner-matrix",
                         "message": "report has no corners[] array: /y/rep.json"}}
        e = self.run_check(1, stderr=json.dumps(env))
        self.assertEqual((e["matrix"], e["report"]), ("matrix_grid.json", "rep.json"))
        self.assertEqual(e["error"], "report has no corners[] array: /y/rep.json")

    def test_plain_text_refusal_is_kept_verbatim(self):
        e = self.run_check(1, stderr="klt corner-matrix: unknown matrix key(s)")
        self.assertEqual(e["error"], "klt corner-matrix: unknown matrix key(s)")

    def test_no_output_at_all_names_the_exit(self):
        self.assertIn("7", self.run_check(7)["error"])

    def test_exit_0_without_a_verdict_is_an_error_not_a_crash(self):
        self.assertIn("error", self.run_check(0, stdout="not json"))
        self.assertIn("error", self.run_check(1, stderr="[1, 2]"))


@unittest.skipUnless(KLT, "klt not on PATH (CI runs this suite before installing it)")
class CornerMatrixCheckKltTest(unittest.TestCase):
    """The real binary against a committed matrix and a synthetic report fixture. No committed
    klt sim report exists -- records/ are this repo's own format -- so the report side is
    always a fixture, here and in the collectors' real runs."""

    R8_IDS = ("typical/4.500V/27C/params:iload=0.25,lfac=1.2",
              "typical/5.000V/27C/params:iload=0.25,lfac=1",
              "typical/5.500V/27C/params:iload=0.25,lfac=0.8")   # matrix_r8.json, whole expansion

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.matrix = os.path.join(recordkit.ROOT, "sim", "steady-state", "matrix_r8.json")
        self.report = os.path.join(self.tmp.name, "report.json")

    def tearDown(self):
        self.tmp.cleanup()

    def write_report(self, corners):
        with open(self.report, "w") as fh:
            json.dump({"corners": corners}, fh)

    @staticmethod
    def corner(cid, status="pass"):
        return {"corner_id": cid, "status": status, "measurements": [{"name": "vout", "value": 1.8}]}

    def test_full_coverage_of_a_committed_matrix(self):
        self.write_report([self.corner(c) for c in self.R8_IDS])
        e = recordkit.corner_matrix_check(self.matrix, self.report)
        self.assertNotIn("error", e)
        self.assertEqual((e["matrix"], e["matrix_size"], e["observed_count"]),
                         ("matrix_r8.json", 3, 3))
        for k in ("missing", "extra", "duplicate", "not_simulated", "non_finite", "out_of_bounds"):
            self.assertEqual(e[k], [], k)

    def test_a_report_missing_one_corner_fails_coverage(self):
        self.write_report([self.corner(c) for c in self.R8_IDS[1:]])
        e = recordkit.corner_matrix_check(self.matrix, self.report)
        self.assertEqual(e["missing"], [self.R8_IDS[0]])
        self.assertEqual(recordkit.coverage_failures([e]),
                         ["matrix_r8.json: coverage incomplete: 1 missing"])

    def test_a_failing_corner_is_out_of_bounds_and_not_a_coverage_failure(self):
        """The case that must never gate: klt status fail is a simulated corner whose
        measurement left its limits; this repo's rows legitimately record it."""
        self.write_report([self.corner(self.R8_IDS[0], status="fail")] +
                          [self.corner(c) for c in self.R8_IDS[1:]])
        e = recordkit.corner_matrix_check(self.matrix, self.report)
        self.assertEqual(e["out_of_bounds"], [self.R8_IDS[0]])
        self.assertEqual(recordkit.coverage_failures([e]), [])

    def test_a_committed_record_without_corners_is_a_refusal(self):
        path = os.path.join(recordkit.ROOT, "sim", "steady-state", "records",
                            "20261102T014053Z-4a850294020b.json")
        e = recordkit.corner_matrix_check(self.matrix, path)
        self.assertIn("error", e)
        self.assertIn("no corners[] array", e["error"])
        self.assertIn("refused", recordkit.coverage_failures([e])[0])


class CoverageFailuresTest(unittest.TestCase):
    """The gate: missing / extra / duplicate only; refusals; per-corner verdicts never."""

    def test_counts_are_named(self):
        e = {"matrix": "m.json", "missing": ["a"], "extra": [], "duplicate": ["b", "c"]}
        self.assertEqual(recordkit.coverage_failures([e]),
                         ["m.json: coverage incomplete: 1 missing, 2 duplicate"])

    def test_an_error_entry_names_the_refusal(self):
        e = {"matrix": "m.json", "error": "report has no corners[] array"}
        self.assertEqual(recordkit.coverage_failures([e]),
                         ["m.json: corner-matrix refused the report (report has no corners[] array)"])

    def test_exact_coverage_with_per_corner_verdicts_is_not_a_failure(self):
        e = {"matrix": "m.json", "missing": [], "extra": [], "duplicate": [],
             "not_simulated": ["x"], "non_finite": ["y"], "out_of_bounds": ["z"]}
        self.assertEqual(recordkit.coverage_failures([e]), [])

    def test_coverage_exit_prints_one_line_per_failure_and_returns_1(self):
        entries = [{"matrix": "m.json", "missing": ["a"], "extra": [], "duplicate": []},
                   {"matrix": "n.json", "error": "boom"}]
        err = io.StringIO()
        with redirect_stderr(err):
            rc = recordkit.coverage_exit(entries, tool="collect.py")
        self.assertEqual(rc, 1)
        self.assertEqual(err.getvalue().count("\n"), 2)
        self.assertIn("collect.py: m.json: coverage incomplete: 1 missing", err.getvalue())
        self.assertIn("collect.py: n.json: corner-matrix refused the report (boom)", err.getvalue())
        with redirect_stderr(io.StringIO()):
            self.assertEqual(recordkit.coverage_exit([]), 0)


def load_collector(bench):
    """Import sim/<bench>/collect.py by path -- the bench directories carry hyphens
    (same loader as test_collect_step_gate.py)."""
    import importlib.util
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", bench, "collect.py")
    spec = importlib.util.spec_from_file_location("collect_" + bench.replace("-", "_"), path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class CollectorCornerMatrixTest(unittest.TestCase):
    """Each collector runs the check once per report it was handed, pairs report to matrix
    from the flags it already takes, carries the verdict in the record's
    environment.corner_matrix, and gates its exit on coverage only -- after writing the
    record. klt is faked; the report fixtures are synthetic (no committed report exists)."""

    ENTRY = {"matrix_size": 1, "observed_count": 1, "missing": [], "extra": [], "duplicate": [],
             "not_simulated": [], "non_finite": [], "out_of_bounds": []}

    def collect(self, bench, argv, entries):
        """Run collector main() with the verdict faked: `entries` are returned per report
        call in order (the last repeats). Returns (rc, records write_record got, check calls
        as (matrix basename, report basename) in order)."""
        mod = load_collector(bench)
        calls, written = [], []

        def fake_check(matrix, report):
            e = dict(entries[min(len(calls), len(entries) - 1)])
            e.update(matrix=os.path.basename(matrix), report=os.path.basename(report))
            calls.append((os.path.basename(matrix), os.path.basename(report)))
            return e

        def fake_write(path, rec, dry=False, tool="collect.py"):
            written.append(rec)
            return 0

        hdr = ("20260101T000000Z", "deadbeefcafe", {"utc": "x", "repo_commit": "deadbeefcafe", "klt": "test"})
        patches = [mock.patch.object(recordkit, "corner_matrix_check", fake_check),
                   mock.patch.object(recordkit, "write_record", fake_write),
                   mock.patch.object(recordkit, "header", return_value=hdr),
                   mock.patch.object(recordkit, "ngspice_banner", return_value="ngspice-test")]
        with patches[0], patches[1], patches[2], patches[3]:
            rc = mod.main(argv)
        return rc, written, calls

    def report_file(self, corners):
        p = os.path.join(self.tmp.name, "rep%d.json" % len(self._reps))
        with open(p, "w") as fh:
            json.dump({"corners": corners}, fh)
        self._reps.append(p)
        return p

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self._reps = []

    def tearDown(self):
        self.tmp.cleanup()

    @staticmethod
    def corner(cid):
        return {"corner_id": cid, "status": "pass"}   # no raw: every unit ungrades, no ngspice

    def test_steady_state_pairs_grid_then_r8(self):
        grid = self.report_file([self.corner("typical/5.000V/27C/params:iload=0.05")])
        r8 = self.report_file([self.corner("typical/5.000V/27C/params:iload=0.25,lfac=1")])
        entry = dict(self.ENTRY, matrix="matrix_grid.json")
        rc, written, calls = self.collect("steady-state", ["--report", grid, "--report", r8], [entry])
        self.assertEqual((rc, calls), (0, [("matrix_grid.json", os.path.basename(grid)),
                                           ("matrix_r8.json", os.path.basename(r8))]))
        self.assertEqual(written[0]["environment"]["corner_matrix"][0]["matrix"], "matrix_grid.json")

    def test_load_step_pairs_tol_full_avg(self):
        cid = "typical/5.0V/27C/params:lfac=1.0,ceff=4.7e-06,esr=0.01"
        args = []
        for k in ("tol", "full", "avg"):
            args += ["--" + k, self.report_file([self.corner(cid)])]
        rc, written, calls = self.collect("load-step", args, [self.ENTRY])
        self.assertEqual((rc, calls), (0, [("matrix_tol.json", "rep0.json"),
                                           ("matrix_full.json", "rep1.json"),
                                           ("matrix_avg.json", "rep2.json")]))
        self.assertEqual(len(written[0]["environment"]["corner_matrix"]), 3)

    def test_soft_start_pairs_the_grid_matrix(self):
        rep = self.report_file([self.corner("typical/5.000V/27C/params:rload=1000000000")])
        rc, written, calls = self.collect("soft-start", ["--report", rep], [self.ENTRY])
        self.assertEqual((rc, calls), (0, [("matrix_grid.json", os.path.basename(rep))]))
        self.assertIn("corner_matrix", written[0]["environment"])

    def test_current_limit_pairs_ramp_and_min(self):
        ramp = self.report_file([self.corner("typical/5.0V/27C/params:i_end=3.0,t_ramp=300e-06")])
        mn = self.report_file([self.corner("typical/5.5V/27C/params:iload=0.5,lfac=0.8")])
        rc, written, calls = self.collect("current-limit", ["--ramp", ramp, "--min", mn], [self.ENTRY])
        self.assertEqual((rc, calls), (0, [("matrix_ramp.json", os.path.basename(ramp)),
                                           ("matrix_min.json", os.path.basename(mn))]))
        self.assertEqual(len(written[0]["environment"]["corner_matrix"]), 2)

    def test_device_stress_pairs_the_named_set_and_both_records_carry_it(self):
        rep = self.report_file([self.corner("typical/5.000V/27C/params:iload=0.25")])
        rc, written, calls = self.collect("device-stress", ["--report", rep, "--set", "ctyp"], [self.ENTRY])
        self.assertEqual((rc, calls), (0, [("matrix_ctyp.json", os.path.basename(rep))]))
        self.assertEqual(len(written), 2)   # the R2 record and the R14 record
        for rec in written:
            self.assertEqual(rec["environment"]["corner_matrix"][0]["matrix"], "matrix_ctyp.json")

    def test_coverage_failure_exits_nonzero_after_writing_the_record(self):
        grid = self.report_file([self.corner("typical/5.000V/27C/params:iload=0.05")])
        r8 = self.report_file([self.corner("typical/5.000V/27C/params:iload=0.25,lfac=1")])
        missing = dict(self.ENTRY, missing=["typical/4.500V/27C/params:iload=0"])
        rc, written, _ = self.collect("steady-state", ["--report", grid, "--report", r8], [missing])
        self.assertEqual(rc, 1)
        self.assertEqual(len(written), 1, "a run that happened is evidence: the record is kept")
        self.assertEqual(written[0]["environment"]["corner_matrix"][0]["missing"],
                         ["typical/4.500V/27C/params:iload=0"])

    def test_full_coverage_with_a_failing_corner_exits_zero(self):
        """out_of_bounds is a klt fail verdict on a covered corner: recorded, never a gate."""
        rep = self.report_file([self.corner("typical/5.000V/27C/params:rload=1000000000")])
        entry = dict(self.ENTRY, out_of_bounds=["typical/5.000V/27C/params:rload=1000000000"])
        rc, written, _ = self.collect("soft-start", ["--report", rep], [entry])
        self.assertEqual(rc, 0)
        self.assertEqual(written[0]["environment"]["corner_matrix"][0]["out_of_bounds"],
                         ["typical/5.000V/27C/params:rload=1000000000"])

    def test_a_refusal_exits_nonzero_and_is_recorded(self):
        rep = self.report_file([self.corner("typical/5.000V/27C/params:rload=1000000000")])
        rc, written, _ = self.collect("soft-start", ["--report", rep],
                                      [{"error": "report has no corners[] array"}])
        self.assertEqual(rc, 1)
        self.assertIn("error", written[0]["environment"]["corner_matrix"][0])

    def test_dry_gates_too_and_writes_nothing(self):
        grid = self.report_file([self.corner("typical/5.000V/27C/params:iload=0.05")])
        r8 = self.report_file([self.corner("typical/5.000V/27C/params:iload=0.25,lfac=1")])
        rc, written, _ = self.collect("steady-state", ["--report", grid, "--report", r8, "--dry"],
                                      [dict(self.ENTRY, missing=["x"])])
        self.assertEqual(rc, 1)
        self.assertEqual(written, [])
        rc, written, _ = self.collect("steady-state", ["--report", grid, "--report", r8, "--dry"],
                                      [self.ENTRY])
        self.assertEqual((rc, written), (0, []))


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
