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
import os
import subprocess
import sys
import tempfile
import unittest

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


if __name__ == "__main__":
    unittest.main()
