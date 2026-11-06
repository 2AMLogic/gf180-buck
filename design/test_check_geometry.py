"""Unit tests for check_geometry.py: synthetic netlists only, no PDK, no klt.

Run: python3 -I -m unittest discover -s design -p 'test_check_geometry.py'
"""

import io
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_geometry as cg  # noqa: E402


def run_on(text, known, name="t.spice"):
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, name)
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(text)
        out, err = io.StringIO(), io.StringIO()
        rc = cg.run([p], known, out=out, err=err)
        return rc, out.getvalue(), err.getvalue()


# 6 V pfet, 0.5 um fingers with m on a continuation line: passes.
OK_CONT = (
    "XMP1 D G S S pfet_06v0 L=0.55u W=50u nf=100 ad='W/nf'\n"
    "+ pd='2*(W/nf)' nrd='0.18u / W'\n"
    "+ sa=0 sb=0 sd=0 m=53\n"
)
# 0.1887 um fingers, below the 0.30 um 6 V COMP minimum.
LOW = "XMP2 D G S S pfet_06v0 L=0.55u W=79.245u\n+ nf=420 m=53\n"
# Exactly at the minimum: 6 V finger 0.30 um (W=30u nf=100), L=0.55 pfet.
AT_MIN = "XMN3 D G S S pfet_06v0 L=0.55u W=30u nf=100\n"


class ParseTests(unittest.TestCase):
    def test_suffixes(self):
        self.assertAlmostEqual(cg.parse_value("79.245u") * 1e6, 79.245)
        self.assertAlmostEqual(cg.parse_value("0.55U") * 1e6, 0.55)
        self.assertAlmostEqual(cg.parse_value("550n") * 1e6, 0.55)
        self.assertAlmostEqual(cg.parse_value("1e-6") * 1e6, 1.0)
        with self.assertRaises(ValueError):
            cg.parse_value("int((nf+1)/2)")

    def test_continuation_and_m(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "t.spice")
            with open(p, "w") as fh:
                fh.write(LOW)
            (dev,) = cg.parse_netlist(p)
        self.assertEqual((dev.nf, dev.m), (420, 53))
        self.assertAlmostEqual(dev.finger_um, 79.245 / 420)  # m does not enter

    def test_nf_defaults_to_one(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "t.spice")
            with open(p, "w") as fh:
                fh.write("XM1 D G S B nfet_03v3 L=0.28u W=0.5u\n")
            (dev,) = cg.parse_netlist(p)
        self.assertEqual(dev.nf, 1)
        self.assertAlmostEqual(dev.finger_um, 0.5)


class CheckTests(unittest.TestCase):
    def test_pass_with_continuation_m(self):
        rc, out, _ = run_on(OK_CONT, {})
        self.assertEqual(rc, 0, out)

    def test_exactly_at_minimum_passes(self):
        rc, _, err = run_on(AT_MIN, {})
        self.assertEqual(rc, 0, err)

    def test_below_minimum_fails_and_names_device(self):
        rc, _, err = run_on(LOW, {})
        self.assertEqual(rc, 1)
        self.assertIn("XMP2", err)
        self.assertIn("W/nf=0.1887", err)
        self.assertIn("comp.width.mv.1", err)
        self.assertIn("sha256:", err)

    def test_known_violation_is_warning_only(self):
        rc, out, err = run_on(LOW, {("t.spice", "XMP2", "comp.width.mv.1"): "#109"})
        self.assertEqual(rc, 0, err)
        self.assertIn("WARNING known violation (#109)", out)

    def test_stale_known_entry_fails(self):
        rc, _, err = run_on(OK_CONT, {("t.spice", "XMP1", "comp.width.mv.1"): "#109"})
        self.assertEqual(rc, 1)
        self.assertIn("stale", err)

    def test_length_minimums_by_flavour(self):
        cases = [
            ("XM1 D G S B nfet_03v3 L=0.27u W=1u\n", 1),
            ("XM1 D G S B nfet_03v3 L=0.28u W=1u\n", 0),
            ("XM1 D G S B nfet_06v0 L=0.55u W=1u\n", 1),  # nfet 6 V needs 0.70
            ("XM1 D G S B nfet_06v0 L=0.70u W=1u\n", 0),
            ("XM1 D G S B pfet_06v0 L=0.50u W=1u\n", 1),  # pfet 6 V needs 0.55
        ]
        for text, want in cases:
            with self.subTest(text=text):
                rc, _, _ = run_on(text, {})
                self.assertEqual(rc, want)

    def test_unparseable_instance_exits_2(self):
        rc, _, err = run_on("XM1 D G S B nfet_03v3 L='a+b' W=1u\n", {})
        self.assertEqual(rc, 2)
        self.assertIn("XM1", err)

    def test_non_mos_and_comments_ignored(self):
        rc, _, _ = run_on("* XM9 pfet_06v0 W=1u\nXR1 a b res W=0.01u\n", {})
        self.assertEqual(rc, 0)


class RepoTests(unittest.TestCase):
    def test_committed_netlists_pass(self):
        # Pure-Python read of committed netlists: still no PDK or klt needed.
        self.assertEqual(cg.main([]), 0)


if __name__ == "__main__":
    unittest.main()
