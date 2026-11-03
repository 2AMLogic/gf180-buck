"""Issue #77 probe 6/7: crossing order and I(L) along the OCP trip chain at one PWM fall, or I(L) at every PWM fall.
Probe-only helper, not a graded record. stdlib + sim/lib.
usage: python3 -I analyze_ss77_trip.py chain waveform.raw   (needs the nets saved by probe_ss77_dense.json)
       python3 -I analyze_ss77_trip.py falls waveform.raw   (needs v(pwm), i(lind))"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import rawgrade  # noqa: E402

mode, path = sys.argv[1], sys.argv[2]
d = rawgrade.read_ascii_raw(path, ("time", "v(pwm)", "i(lind)"))
t, pw, il = d["time"], d["v(pwm)"], d["i(lind)"]
falls = [k for k in range(1, len(t)) if pw[k - 1] >= 1.65 > pw[k]]
if mode == "falls":
    pk = [max(il[max(0, k - 3):k + 1]) for k in falls]
    print("saved %.1f..%.1f us, %d PWM falls, I(L) at fall: min %.3f max %.3f mean %.3f A"
          % (t[0] * 1e6, t[-1] * 1e6, len(falls), min(pk), max(pk), sum(pk) / len(pk)))
else:
    CHAIN = (("v(xtop.xocp.raw)", True), ("v(xtop.xocp.trn)", False), ("v(xtop.trip)", True), ("v(xtop.xpwm.ocpb)", False),
             ("v(xtop.xpwm.rst)", True), ("v(xtop.xpwm.q)", False), ("v(pwm)", False))
    d = rawgrade.read_ascii_raw(path, ("time",) + tuple(c for c, _ in CHAIN) + ("i(lind)",))
    t0 = t[falls[0]]
    print("first PWM fall at %.4f us; max timestep near it %.3f ns" % (t0 * 1e6, max(b - a for a, b in zip(t, t[1:]) if abs(a - t0) < 100e-9) * 1e9))
    for c, up in CHAIN:
        v = d[c]
        for k in range(1, len(t)):
            if abs(t[k] - t0) < 20e-9 and ((v[k - 1] < 1.65 <= v[k]) if up else (v[k - 1] >= 1.65 > v[k])):
                x = t[k - 1] + (1.65 - v[k - 1]) / (v[k] - v[k - 1]) * (t[k] - t[k - 1])
                print("%-20s %-4s %+.3f ns vs PWM fall  I(L) %.4f A" % (c, "rise" if up else "fall", (x - t0) * 1e9, il[k]))
