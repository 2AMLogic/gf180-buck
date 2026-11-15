"""Unit tests for layout/: the committed GDS is what the generator produces, and
the power path measured out of it meets the 500 mA EM row.

Drift guard, not a redraw: CI re-hashes layout/buck.gds against the manifest,
which catches an edited GDS but not a gen_layout.py that has drifted from the
GDS it is cited as producing (manifests/item2-attestation.json names
`python3 layout/gen_layout.py` as the generator).

Needs the klayout Python module (both scripts import klayout.db); no PDK, no
ngspice, no klt. The first test regenerates the whole layout, so it takes tens
of seconds.

Run: python3 -m unittest discover -s layout -p 'test_*.py'
(not `-I`: it drops the user site-packages directory, which is where a
no-host-install klayout usually lives)
"""
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest

import klayout.db as db

HERE = os.path.dirname(os.path.abspath(__file__))
GDS = os.path.join(HERE, "buck.gds")


def sha256(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def run(script, *args):
    """Run one of the layout scripts under this interpreter (see above re `-I`)."""
    return subprocess.run([sys.executable, os.path.join(HERE, script), *args],
                          capture_output=True, text=True)


class GeneratorTests(unittest.TestCase):
    def test_generator_output_matches_committed_gds(self):
        """gen_layout.py still reproduces buck.gds byte for byte."""
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, "buck.gds")
            r = run("gen_layout.py", "--out", out, "--info", os.path.join(d, "buck.info.json"))
            self.assertEqual(r.returncode, 0,
                             "gen_layout.py failed (%d):\n%s%s" % (r.returncode, r.stdout, r.stderr))
            self.assertEqual(
                sha256(out), sha256(GDS),
                "gen_layout.py no longer reproduces layout/buck.gds. If the generator "
                "change is intended, regenerate the GDS and re-attest T1 item 2 "
                "(layout/README.md), otherwise the committed GDS is not what the "
                "cited generator produces.")


class PowerPathTests(unittest.TestCase):
    def test_power_path_meets_500ma_row(self):
        """check_layout.py measures the committed GDS and passes the 500 mA EM row."""
        r = run("check_layout.py")
        self.assertEqual(r.returncode, 0,
                         "check_layout.py failed (%d):\n%s%s" % (r.returncode, r.stdout, r.stderr))

    def test_cut_coverage_assertion_bites_in_both_directions(self):
        """The coverage assertion names orphan cuts below AND above on a violating GDS.

        The committed GDS is clean in all six probes; this mutant re-creates the
        two orphan classes #182 fixed -- a Via1 under Metal2 with no Metal1
        below it (the 1260), and a Via1 on Metal1 with no Metal2 above it (the
        720) -- and asserts check_layout.py exits non-zero naming both. A
        below-only proof does not satisfy the AC.
        """
        with open(os.path.join(HERE, "buck.info.json")) as fh:
            info = json.load(fh)
        rows_bot = info["rows_y"]["HS"][0]   # HS row-0 gate-rail bottom = COMP base - 5.1
        w = info["width_um"]
        ly = db.Layout()
        ly.read(GDS)
        top = ly.top_cell()
        via1 = ly.layer(35, 0)
        # below-orphan: in the HS gate-bus band (Metal2, x -30..W) beyond the row
        # extent, where no Metal1 exists
        top.shapes(via1).insert(db.DBox(w - 6.0, rows_bot - 2.35, w - 6.0 + 0.26, rows_bot - 2.35 + 0.26))
        # above-orphan: on the row-0 gate-rail Metal1 (full width) inside a strap
        # gap of period x0 = 288 (gap 299.7..300.3), where no Metal2 exists
        top.shapes(via1).insert(db.DBox(299.87, rows_bot + 0.55, 299.87 + 0.26, rows_bot + 0.55 + 0.26))
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "mutant.gds")
            ly.write(p)
            r = run("check_layout.py", "--gds", p)
        self.assertNotEqual(r.returncode, 0,
                            "coverage assertion did not bite on orphan cuts:\n%s" % r.stdout)
        self.assertIn("not covered by Metal1", r.stdout,
                      "below-direction did not bite:\n%s" % r.stdout)
        self.assertIn("not covered by Metal2", r.stdout,
                      "above-direction did not bite:\n%s" % r.stdout)


if __name__ == "__main__":
    unittest.main()
