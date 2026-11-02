"""Issue #77: R15 numbers from a single-corner probe waveform (stdlib + sim/lib). Not a graded record.
usage: python3 -I analyze_ss77.py waveform.raw   (needs v(out), i(lind), v(xtop.clk), v(gnd_d), v(vc), v(xtop.vref))"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import buckmeas  # noqa: E402
import rawgrade  # noqa: E402

NEED = ("time", "v(out)", "i(lind)", "v(xtop.clk)", "v(gnd_d)", "v(vc)", "v(xtop.vref)")
d = rawgrade.read_ascii_raw(sys.argv[1], NEED)
t, vo, il, ck = d["time"], d["v(out)"], d["i(lind)"], d["v(xtop.clk)"]
edges = [t[k - 1] + (1.65 - ck[k - 1]) / (ck[k] - ck[k - 1]) * (t[k] - t[k - 1]) for k in range(1, len(t)) if ck[k - 1] < 1.65 <= ck[k]]  # times (s)
print("saved %.1f..%.1f us, %d clock edges, step_max %.2f ns" % (t[0] * 1e6, t[-1] * 1e6, len(edges), max(b - a for a, b in zip(t, t[1:])) * 1e9))
ss = buckmeas.soft_start(t, vo, il, edges, t_en=20e-6, v_target=1.8, v_reg_max=1.872)
print({k: ss.get(k) for k in ("available", "t_90_s", "monotonic", "max_drawdown_v", "overshoot_v", "peak_il_a", "reason")})
print("clock MHz over run: %.3f" % ((len(edges) - 1) / (edges[-1] - edges[0]) / 1e6))
for lo in range(20, 700, 40):
    s = [k for k in range(len(t)) if lo * 1e-6 <= t[k] < (lo + 40) * 1e-6]
    if s:
        m = sum(vo[k] for k in s) / len(s)
        print("%3d-%3d us  Vout mean %.3f  vc-gnd_d %.2f  vref_ss-gnd_d %.3f  ipk %.3f A" % (lo, lo + 40, m, sum(d['v(vc)'][k] - d['v(gnd_d)'][k] for k in s) / len(s), sum(d['v(xtop.vref)'][k] - d['v(gnd_d)'][k] for k in s) / len(s), max(abs(il[k]) for k in s)))
