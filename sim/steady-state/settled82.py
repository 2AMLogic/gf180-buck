"""Spec 0.4 settled test on a klt sim waveform.raw.json (issue #82): consecutive 20-clock-cycle windows,
mean Vout (time-weighted) differing < 0.1 % and peak inductor current < 1 %. Stdlib only.
usage: settled82.py waveform.raw.json [t_from_us]"""
import json
import sys


def main(path, t_from_us=0.0):
    with open(path) as fh:
        d = json.load(fh)
    names = [v["name"] for v in d["variables"]]
    pts = d["points"]
    ti, vo, il, ck = (names.index(n) for n in ("time", "v(out)", "i(lind)", "v(xtop.clk)")) if "time" in names else (
        0, names.index("v(out)"), names.index("i(lind)"), names.index("v(xtop.clk)"))
    edges = [
        k for k in range(1, len(pts)) if pts[k - 1][ck] < 1.65 <= pts[k][ck] and pts[k][ti] >= t_from_us * 1e-6
    ]
    wins = []
    for a, b in zip(edges[0:-20:20], edges[20::20]):
        s = pts[a:b + 1]
        wsum = sum(s[k + 1][ti] - s[k][ti] for k in range(len(s) - 1))
        mean = sum(s[k][vo] * (s[k + 1][ti] - s[k][ti]) for k in range(len(s) - 1)) / wsum
        wins.append((pts[a][ti] * 1e6, pts[b][ti] * 1e6, mean, max(abs(p[il]) for p in s)))
    print("win_start_us win_end_us vout_mean  ipk   d_mean_%  d_ipk_%  consec_ok")
    prev = None
    for w in wins:
        if prev:
            dm = 100 * abs(w[2] - prev[2]) / abs(prev[2])
            di = 100 * abs(w[3] - prev[3]) / abs(prev[3])
            print(f"{w[0]:9.1f} {w[1]:9.1f} {w[2]:9.4f} {w[3]:6.3f} {dm:8.3f} {di:8.3f}  {dm < 0.1 and di < 1.0}")
        else:
            print(f"{w[0]:9.1f} {w[1]:9.1f} {w[2]:9.4f} {w[3]:6.3f}")
        prev = w


if __name__ == "__main__":
    main(sys.argv[1], float(sys.argv[2]) if len(sys.argv) > 2 else 0.0)
