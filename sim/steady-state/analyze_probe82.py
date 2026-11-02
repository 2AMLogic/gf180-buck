"""Windowed summary of a klt sim waveform.raw.json (issue #82 diagnosis probes)."""

import functools
import json
import sys

import numpy as np


def _wavg(x, m, dt, wsum):
    return float((x[m] * dt).sum() / wsum)


def main(path, win_us=25.0):
    with open(path) as fh:
        d = json.load(fh)
    names = [v["name"] for v in d["variables"]]
    a = np.array(d["points"])
    t = a[:, 0]
    col = {n: a[:, i] for i, n in enumerate(names)}
    print(
        "window_us  vout_mean  vout_out_of[-0.5,2.2]%  vc_min  vc_max  fbn_mean  vref_mean  duty  clk_MHz  iL_mean"
    )
    t0 = t[0]
    w = win_us * 1e-6
    while t0 < t[-1] - 1e-9:
        m = (t >= t0) & (t < t0 + w)
        if m.sum() > 10:
            tt = t[m]
            dt = np.diff(tt, append=tt[-1])
            wsum = dt.sum()
            wavg = functools.partial(_wavg, m=m, dt=dt, wsum=wsum)
            vo = col["v(out)"][m]
            clk = col["v(xtop.clk)"][m]
            up = np.where((clk[:-1] < 1.65) & (clk[1:] >= 1.65))[0]
            f = len(up) / (tt[-1] - tt[0]) / 1e6
            duty = float(((col["v(pwm)"][m] > 1.65) * dt).sum() / wsum)
            print(
                f"{t0 * 1e6:7.0f} {wavg(col['v(out)']):9.3f} {100 * np.mean((vo < -0.5) | (vo > 2.2)):8.2f} "
                f"{col['v(vc)'][m].min():7.2f} {col['v(vc)'][m].max():7.2f} {wavg(col['v(xtop.xcomp.fbn)']):8.3f} "
                f"{wavg(col['v(xtop.vref)']):8.3f} {duty:6.3f} {f:6.2f} {wavg(col['i(lind)']):7.3f}"
            )
        t0 += w


if __name__ == "__main__":
    main(sys.argv[1])
