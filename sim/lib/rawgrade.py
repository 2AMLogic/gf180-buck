#!/usr/bin/env python3
"""rawgrade: grade one klt-sim switching-converter corner with sim/lib/buckmeas.py.

Input: the corner's ngspice ASCII `waveform.raw` (vectors v(out) i(lind) v(sw_d)
v(vsrc) i(vsrc), saved only from the request's .tran tstart on). The bench's
oscillator free-runs, so the cycle boundaries buckmeas needs are taken from the
run itself: rising crossings of Vin/2 on V(sw) (the R7 definition) give the
period and the clock phase over the whole saved tail; buckmeas then grades whole
cycles of that period. Pin is taken at the board-side source: -v(vsrc)*i(vsrc).
Stdlib only. Exit 0 = graded (settled or not; see `settle.settled`), 1 = unusable input.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import buckmeas  # noqa: E402

NEEDED = ("time", "i(lind)", "v(out)", "v(sw_d)", "v(vsrc)", "i(vsrc)")


def read_ascii_raw(path, needed=NEEDED):
    """ngspice ASCII rawfile (real, one plot) -> {name: [floats]}. `needed` lists the vectors that must be present."""
    with open(path) as fh:
        text = fh.read()
    head, _, body = text.partition("\nValues:\n")
    names = []
    in_vars = False
    for line in head.splitlines():
        if line.startswith("Variables:"):
            in_vars = True
            continue
        if in_vars and line.strip():
            names.append(line.split()[1].lower())
    n = len(names)
    toks = body.split()
    if n == 0 or len(toks) % (n + 1):
        raise ValueError("malformed rawfile: %d tokens for %d variables" % (len(toks), n))
    cols = {name: [] for name in names}
    for k in range(0, len(toks), n + 1):  # token 0 of each point is its index
        for j, name in enumerate(names):
            cols[name].append(float(toks[k + 1 + j]))
    missing = [v for v in needed if v not in cols]
    if missing:
        raise ValueError("rawfile lacks vectors %s" % missing)
    return cols


def sw_rising_crossings(t, vsw, vin):
    """Rising crossings of vin/2 on V(sw), Schmitt-guarded (as buckmeas R7)."""
    vth, vlo = vin / 2.0, vin / 4.0
    armed, out = False, []
    for i in range(1, len(t)):
        if vsw[i - 1] < vlo:
            armed = True
        if armed and vsw[i - 1] < vth <= vsw[i]:
            out.append(buckmeas.lerp_crossing(t[i - 1], t[i], vsw[i - 1], vsw[i], vth))
            armed = False
    return out


def grade(raw_path, vin, iload, step_max):
    c = read_ascii_raw(raw_path)
    t = c["time"]
    xs = sw_rising_crossings(t, c["v(sw_d)"], vin)
    if len(xs) < 41:
        return {"graded": False, "reason": "fewer than 41 switching cycles in the saved tail (%d)" % len(xs)}
    f_sw = (len(xs) - 1) / (xs[-1] - xs[0])
    pin = [-v * i for v, i in zip(c["v(vsrc)"], c["i(vsrc)"])]
    res = buckmeas.analyze_columns(t, c["v(out)"], c["i(lind)"], c["v(sw_d)"], pin, f_sw=f_sw,
                                   vin=vin, tier_params={"i_load": iload}, step_max=step_max,
                                   t_clk0=xs[0])
    res["clock"] = {"source": "rising crossings of Vin/2 on V(sw) over the whole saved tail",
                    "f_hz": f_sw, "t_clk0_s": xs[0], "crossings": len(xs)}
    # R6 evidence: forced PWM means a rising SW edge every period (no skipped pulse, no burst
    # gap) and, at light load, inductor current that goes negative. Over the whole saved tail.
    gaps = sorted(b - a for a, b in zip(xs, xs[1:]))
    median = gaps[len(gaps) // 2]
    res["pwm_regularity"] = {
        "crossings": len(xs), "median_period_s": median, "max_period_s": gaps[-1],
        "min_period_s": gaps[0], "max_over_median": gaps[-1] / median,
        "il_min_a": min(c["i(lind)"]), "il_max_a": max(c["i(lind)"]),
        "window_s": [t[0], t[-1]]}
    res["graded"] = True
    return res


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("raw")
    ap.add_argument("--vin", type=float, required=True, help="board-side Vin of this corner [V]")
    ap.add_argument("--iload", type=float, required=True, help="load current [A]")
    ap.add_argument("--step-max", type=float, default=2.5e-9, help="spec 0.4 max step [s]")
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    try:
        res = grade(a.raw, a.vin, a.iload, a.step_max)
    except (OSError, ValueError) as exc:
        print("grade.py: %s" % exc, file=sys.stderr)
        return 1
    text = json.dumps(res, indent=1)
    if a.out:
        with open(a.out, "w") as fh:
            fh.write(text + "\n")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
