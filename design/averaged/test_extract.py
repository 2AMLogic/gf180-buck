import cmath
import hashlib
import json
import math
import os
import tempfile
import unittest
from unittest import mock

import extract


def sweep(fn, f0=1e3, f1=1e8, per_dec=200):
    n = int(round(math.log10(f1 / f0) * per_dec))
    fs = [f0 * 10 ** (i / per_dec) for i in range(n + 1)]
    return fs, [fn(f) for f in fs]


class IntegratorDelay(unittest.TestCase):
    """T = (fu/jf) * exp(-j*2*pi*f*tau): closed-form margins.
    fc = fu; PM = 90 - 360*fu*tau; -180 crossing at f = 1/(4*tau);
    GM = 20*log10(1/(4*tau*fu))."""
    fu, tau = 100e3, 0.5e-6

    def test_known_fc_pm_gm(self):
        fs, t = sweep(lambda f: self.fu / (1j * f) * cmath.exp(-2j * math.pi * f * self.tau))
        m = extract.margins(fs, t)
        self.assertAlmostEqual(m["fc_hz"], self.fu, delta=self.fu * 1e-3)
        self.assertAlmostEqual(m["pm_deg"], 90 - 360 * self.fu * self.tau, delta=0.05)
        self.assertAlmostEqual(m["gm_db"], 20 * math.log10(1 / (4 * self.tau * self.fu)), delta=0.05)
        self.assertEqual((m["n_unity"], m["n_180"]), (1, 1))

    def test_grade_pass_fail_and_rounding(self):
        fs, t = sweep(lambda f: self.fu / (1j * f) * cmath.exp(-2j * math.pi * f * self.tau))
        g = extract.grade(extract.margins(fs, t))
        self.assertEqual(g["pass"], {"fc": True, "pm": True, "gm": True, "all": True})
        self.assertAlmostEqual(g["pm_deg"], 72.0, delta=0.05)
        self.assertAlmostEqual(g["gm_db"], 13.98, delta=0.05)
        # same loop gain with a long delay: PM 90-360*100e3*2e-6 = 18 deg fails
        fs, t = sweep(lambda f: 100e3 / (1j * f) * cmath.exp(-2j * math.pi * f * 2e-6))
        g = extract.grade(extract.margins(fs, t))
        self.assertFalse(g["pass"]["pm"])
        self.assertFalse(g["pass"]["all"])

    def test_deterministic(self):
        fs, t = sweep(lambda f: self.fu / (1j * f) * cmath.exp(-2j * math.pi * f * self.tau))
        self.assertEqual(extract.grade(extract.margins(fs, t)), extract.grade(extract.margins(fs, t)))


class EdgeCases(unittest.TestCase):
    def test_pure_integrator_has_no_180_crossing(self):
        fs, t = sweep(lambda f: 200e3 / (1j * f))
        m = extract.margins(fs, t)
        self.assertIsNone(m["gm_db"])
        self.assertAlmostEqual(m["pm_deg"], 90.0, delta=1e-6)
        self.assertEqual(extract.grade(m)["gm_db"], "none")
        self.assertTrue(extract.grade(m)["pass"]["gm"])

    def test_gain_never_reaches_unity(self):
        fs, t = sweep(lambda f: 0.5 / (1j * f / 1e3))
        m = extract.margins(fs, t)
        self.assertIsNone(m["fc_hz"])
        g = extract.grade(m)
        self.assertIsNone(g["fc_khz"])
        self.assertFalse(g["pass"]["fc"])
        self.assertFalse(g["pass"]["all"])

    def test_fc_outside_band_fails_only_fc(self):
        fs, t = sweep(lambda f: 50e3 / (1j * f))
        g = extract.grade(extract.margins(fs, t))
        self.assertFalse(g["pass"]["fc"])
        self.assertTrue(g["pass"]["pm"])

    def test_unwrap_through_minus_180(self):
        out = extract.unwrap_deg([-170.0, 179.0, 170.0])
        self.assertEqual(out, [-170.0, -181.0, -190.0])


class RecordEnvelope(unittest.TestCase):
    """The issue #169 consolidation invariant: results_sha256 covers `points`
    alone, so growing the provenance envelope (repo_commit, klt, files_sha256)
    cannot move the graded numbers -- and every committed record reproduces it."""

    PARAMS = {"vin": 5.0, "lfac": 1.0, "ceff": 4.7e-6, "esr": 0.005, "iload": 0.25}

    @staticmethod
    def write_sidecar(path, fs, t):
        """A klt complex_vectors artifact for T = t(f): v(b) = 1, v(vo) = -T."""
        with open(path, "w") as fh:
            json.dump({"frequency_hz": fs,
                       "data": {"v(vo)": {"real": [-x.real for x in t], "imag": [-x.imag for x in t]},
                                "v(b)": {"real": [1.0] * len(fs), "imag": [0.0] * len(fs)}}}, fh)

    def fixture(self, d, banner="ngspice-47", remote=None):
        fs, t = sweep(lambda f: 100e3 / (1j * f) * cmath.exp(-2j * math.pi * f * 0.5e-6))
        p = os.path.join(d, "point.json")
        self.write_sidecar(p, fs, t)
        return {"environment": {"engine_version": banner, "engine_build": {"version_banner": "x\n%s\ny" % banner},
                                "netlist_sha256": "deadbeef", "remote": remote or {}},
                "corners": [{"corner_id": "typical/5.0V/27C/params:" + ",".join(
                                "%s=%r" % (k, v) for k, v in self.PARAMS.items()),
                             "status": "pass", "params": dict(self.PARAMS),
                             "artifacts": {"complex_vectors": p}}]}

    def test_results_sha_covers_points_alone(self):
        with tempfile.TemporaryDirectory() as d:
            rec = extract.build_record(self.fixture(d), self.request_file(d))
        self.assertEqual(rec["results_sha256"],
                         hashlib.sha256(json.dumps(rec["points"], sort_keys=True).encode()).hexdigest())

    def test_envelope_cannot_move_the_hash(self):
        with tempfile.TemporaryDirectory() as d:
            req = self.request_file(d, "{}")
            a = extract.build_record(self.fixture(d, banner="ngspice-44", remote={"job_id": "a"}), req)
            b = extract.build_record(self.fixture(d, banner="ngspice-47", remote={"job_id": "b"}), req)
        self.assertEqual(a["results_sha256"], b["results_sha256"])
        self.assertEqual(a["points"], b["points"])
        self.assertNotEqual((a["ngspice_banner"], a["deck_sha256"]), (b["ngspice_banner"], b["deck_sha256"]))

    def test_request_bytes_do_not_move_the_hash(self):
        with tempfile.TemporaryDirectory() as d:
            a = extract.build_record(self.fixture(d), self.request_file(d, '{"netlist": "a"}'))
            b = extract.build_record(self.fixture(d), self.request_file(d, '{"netlist": "b"}'))
        self.assertNotEqual(a["request_sha256"], b["request_sha256"])
        self.assertEqual(a["results_sha256"], b["results_sha256"])

    def test_committed_records_reproduce_their_hash(self):
        """Append-only evidence: every committed record's results_sha256 is the
        formula over its own points, and the newest record still carries the
        781e1a29003d prefix the whole history shares."""
        records = sorted(os.listdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), "records")))
        newest = None
        for name in records:
            if not name.endswith(".json"):
                continue
            with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "records", name)) as fh:
                rec = json.load(fh)
            self.assertEqual(rec["results_sha256"],
                             hashlib.sha256(json.dumps(rec["points"], sort_keys=True).encode()).hexdigest(),
                             name)
            newest = rec
        self.assertTrue(newest and newest["results_sha256"].startswith("781e1a29003d"), records[-1])

    def run_main(self, d, out, banner="ngspice-47", job="a", tag=()):
        report = os.path.join(d, "report.json")
        with open(report, "w") as fh:
            json.dump(self.fixture(d, banner=banner, remote={"job_id": job}), fh)
        # sweep_request.json is generated and gitignored, so stub the file hash. header()
        # shells out to `klt` and `git`, neither of which the stdlib-only CI lane has before
        # the pinned klt install, so pin it too and keep the test hermetic.
        hdr = {"utc": "20000101T000000Z", "repo_commit": "0" * 12, "klt": "klt-stub"}
        with mock.patch.object(extract.recordkit, "files_sha256", return_value={"x": "0"}), \
                mock.patch.object(extract.recordkit, "header", return_value=("20000101T000000Z", "0" * 12, hdr)):
            return extract.main(["--report", report, "--request", self.request_file(d),
                                 "--out-dir", out, *tag])

    def test_new_hash_writes_full_record_and_no_run_row(self):
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, "records")
            self.assertEqual(self.run_main(d, out), 0)
            self.assertEqual([n.endswith(".json") for n in os.listdir(out)], [True])

    def test_equal_hash_appends_one_row_and_no_record(self):
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, "records")
            self.run_main(d, out)
            (first,) = os.listdir(out)
            self.assertEqual(self.run_main(d, out, banner="ngspice-48", job="b", tag=["--tag=-x"]), 0)
            self.assertEqual(sorted(os.listdir(out)), sorted([first, "runs.jsonl"]))
            with open(os.path.join(out, "runs.jsonl")) as fh:
                rows = [json.loads(x) for x in fh]
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["record"], first)
            self.assertEqual(rows[0]["remote"]["job_id"], "b")
            self.assertEqual(self.run_main(d, out, job="c"), 0)
            with open(os.path.join(out, "runs.jsonl")) as fh:
                self.assertEqual(len(fh.readlines()), 2)

    def test_malformed_runs_log_is_a_hard_error(self):
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, "records")
            self.run_main(d, out)
            with open(os.path.join(out, "runs.jsonl"), "w") as fh:
                fh.write("{broken\n")
            self.assertEqual(self.run_main(d, out), 1)
            with open(os.path.join(out, "runs.jsonl")) as fh:
                self.assertEqual(fh.read(), "{broken\n")

    @staticmethod
    def request_file(d, body='{"netlist": "buck_avg.spice"}'):
        p = os.path.join(d, "sweep_request.json")
        with open(p, "w") as fh:
            fh.write(body)
        return p


if __name__ == "__main__":
    unittest.main()
