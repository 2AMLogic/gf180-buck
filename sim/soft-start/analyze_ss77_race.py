"""Issue #77 probe 9: per clock edge, CLK pulse width vs the time RST takes to clear (set-vs-comparator race), and whether PWM rose.
Probe-only helper. stdlib + sim/lib. usage: python3 -I analyze_ss77_race.py waveform.raw (needs probe_ss77_dd.json nets)"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import rawgrade  # noqa: E402

N = ("time", "v(xtop.clk)", "v(xtop.xpwm.rst)", "v(xtop.xpwm.q)", "v(pwm)", "v(vc)", "v(gnd_d)", "v(xtop.ramp)")
d = rawgrade.read_ascii_raw(sys.argv[1], N)
t, clk, rst, q, pw, vc, g, rp = (d[n] for n in N)
H = 1.65


def cross(v, k0, up, kmax):
    for k in range(k0, min(kmax, len(t) - 1)):
        if (v[k] < H <= v[k + 1]) if up else (v[k] >= H > v[k + 1]):
            return t[k] + (H - v[k]) / (v[k + 1] - v[k]) * (t[k + 1] - t[k])
    return None


for k in range(1, len(t) - 1):
    if clk[k - 1] < H <= clk[k]:
        tc = t[k]
        kend = k + 400
        if t[-1] - tc < 100e-9:
            break
        tf = cross(clk, k, False, kend)
        tr = cross(rst, k, False, kend)       # RST clearing (comparator says ramp < vc)
        tq = cross(q, k, True, kend)
        # ramp valley in the 60 ns after the clock edge, and vc then
        w = [j for j in range(k, min(kend, len(t))) if t[j] - tc < 60e-9]
        vmin = min(rp[j] - g[j] for j in w)
        vcm = sum(vc[j] - g[j] for j in w) / len(w)
        print("clk %.3f us  width %s ns  RST clears %s ns after edge  Q set %s  margin vc-ramp_valley %.3f V"
              % (tc * 1e6, "%.1f" % ((tf - tc) * 1e9) if tf else "-", "%.1f" % ((tr - tc) * 1e9) if tr else "-",
                 "yes" if tq and tq - tc < 100e-9 else "NO", vcm - vmin))
