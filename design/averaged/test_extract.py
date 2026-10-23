import cmath
import math
import unittest

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


if __name__ == "__main__":
    unittest.main()
