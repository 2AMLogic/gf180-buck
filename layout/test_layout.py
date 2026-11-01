"""pytest-style check: the committed GDS is what the generator produces and meets the 500 mA row."""
import hashlib
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))


def test_generator_is_deterministic_and_matches_committed():
    with tempfile.TemporaryDirectory() as d:
        out = os.path.join(d, "b.gds")
        subprocess.run([sys.executable, os.path.join(HERE, "gen_layout.py"), "--out", out,
                        "--info", os.path.join(d, "i.json")], check=True)
        assert hashlib.sha256(open(out, "rb").read()).digest() == \
            hashlib.sha256(open(os.path.join(HERE, "buck.gds"), "rb").read()).digest()


def test_power_path_meets_500ma_row():
    r = subprocess.run([sys.executable, os.path.join(HERE, "check_layout.py")])
    assert r.returncode == 0
