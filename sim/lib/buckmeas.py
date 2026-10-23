"""buckmeas: grade a switching-converter .tran the way spec/target-spec.md §0.4 says.

PDK-free, stdlib-only (no numpy), so `python3 -m unittest discover sim/lib`
runs on a bare host. It reads ngspice `wrdata` output (time, V(out), I(L),
V(sw), input power) and returns, for the last settled 20 cycles:

  R4   mean Vout                      R9/R10  efficiency (whole cycles only)
  R7   switching frequency (>= 100)   R11     ripple after a 20 MHz 1st-order LP
  R8   inductor ripple p-p            R12     load-step deviation and recovery

Each result restates the run length, the step and the window it was measured
on, as §0.4 requires. Results are simulated, never measured; nothing here
compares a number against a spec row.

Cycle boundaries come from the commanded clock (`f_sw`, `t_clk0`), not from
threshold detection, except R7, which is measured from V(sw) crossings.
"""

import argparse
import bisect
import json
import math
import sys

WRDATA_COLUMNS = ("t", "vout", "il", "vsw", "pin")

WINDOW_CYCLES = 20  # §0.4: measurement and settling window
MEAN_TOL = 1e-3  # §0.4: consecutive windows differ < 0.1 % in mean Vout ...
IPK_TOL = 1e-2  # ... and < 1 % in peak inductor current
MIN_FSW_CYCLES = 100  # R7: fundamental over >= 100 settled cycles
LOAD_STEP_MIN_CYCLES = 100  # §0.4: run >= 100 cycles after the step ...
BAND_CYCLES = 20  # ... or 20 consecutive in-band cycles, whichever is longer
RIPPLE_LP_HZ = 20e6  # R11
STEP_DIVISOR = 200  # §0.4: max step T/200
_EPS_CYCLES = 1e-6  # a time this close to a cycle boundary is on it


def read_wrdata(path, names=WRDATA_COLUMNS):
    """Read an ngspice wrdata file into {name: [floats]}.

    Accepts the `set wr_singlescale` layout (one time column) and the default
    one (a time column repeated before every vector). Non-numeric lines
    (a `wr_vecnames` header) are skipped.
    """
    n = len(names) - 1
    rows = []
    with open(path) as fh:
        for line in fh:
            parts = line.split()
            if not parts:
                continue
            try:
                rows.append([float(p) for p in parts])
            except ValueError:
                continue
    if not rows:
        raise ValueError(f"{path}: no numeric rows")
    width = len(rows[0])
    if width == n + 1:
        value_cols = range(1, n + 1)
    elif width == 2 * n:
        value_cols = range(1, 2 * n, 2)
    else:
        raise ValueError(f"{path}: {width} columns, expected {n + 1} (singlescale) or {2 * n}")
    if any(len(r) != width for r in rows):
        raise ValueError(f"{path}: ragged rows")
    data = {names[0]: [r[0] for r in rows]}
    for name, col in zip(names[1:], value_cols):
        data[name] = [r[col] for r in rows]
    t = data[names[0]]
    if any(b < a for a, b in zip(t, t[1:])):
        raise ValueError(f"{path}: time is not monotonic")
    return data


def _interp(t, y, x):
    i = bisect.bisect_right(t, x)
    if i == 0:
        return y[0]
    if i >= len(t):
        return y[-1]
    t0, t1 = t[i - 1], t[i]
    if t1 == t0:
        return y[i]
    return y[i - 1] + (y[i] - y[i - 1]) * (x - t0) / (t1 - t0)


def window(t, ys, t0, t1):
    """Samples of each y in [t0, t1], with interpolated end points."""
    lo = bisect.bisect_right(t, t0)
    hi = bisect.bisect_left(t, t1)
    tt = [t0] + t[lo:hi] + [t1]
    return tt, [[_interp(t, y, t0)] + y[lo:hi] + [_interp(t, y, t1)] for y in ys]


def _integral(tt, yy):
    return sum(0.5 * (yy[i] + yy[i - 1]) * (tt[i] - tt[i - 1]) for i in range(1, len(tt)))


def window_mean(t, y, t0, t1):
    tt, (yy,) = window(t, [y], t0, t1)
    return _integral(tt, yy) / (t1 - t0)


def cycle_floor(t_x, f_sw, t_clk0=0.0):
    """Latest cycle boundary at or before t_x."""
    return t_clk0 + math.floor((t_x - t_clk0) * f_sw + _EPS_CYCLES) / f_sw


def lowpass(t, y, fc):
    """First-order low-pass of a piecewise-linear signal, exact per step."""
    tau = 1.0 / (2.0 * math.pi * fc)
    out = [y[0]]
    for i in range(1, len(t)):
        dt = t[i] - t[i - 1]
        if dt <= 0:
            out.append(out[-1])
            continue
        slope_tau = (y[i] - y[i - 1]) / dt * tau
        decay = math.exp(-dt / tau)
        out.append(y[i] - slope_tau * -math.expm1(-dt / tau) + (out[-1] - y[i - 1]) * decay)
    return out


def _win_info(t0, t1, f_sw):
    return {"t_start_s": t0, "t_end_s": t1, "cycles": round((t1 - t0) * f_sw, 6)}


def settle(t, vout, il, f_sw, *, t_end=None, t_clk0=0.0, window_cycles=WINDOW_CYCLES,
           mean_tol=MEAN_TOL, ipk_tol=IPK_TOL):
    """§0.4 steady-state test on consecutive windows stepped back from t_end.

    Settled iff the last two windows differ < mean_tol in mean Vout and
    < ipk_tol in peak I(L). `settled_since_s` is the start of the earliest
    window of the unbroken chain of passing pairs before them.
    """
    span = window_cycles / f_sw
    if t_end is None:
        t_end = cycle_floor(t[-1], f_sw, t_clk0)
    res = {
        "settled": False, "window_cycles": window_cycles, "t_end_s": t_end,
        "mean_tol": mean_tol, "ipk_tol": ipk_tol,
        "mean_vout_delta_rel": None, "ipk_delta_rel": None,
        "window_start_s": None, "settled_since_s": None, "measure_window_s": None,
    }

    def stats(k):
        a, b = t_end - (k + 1) * span, t_end - k * span
        if a < t[0] - _EPS_CYCLES / f_sw:
            return None
        tt, (vv, ii) = window(t, [vout, il], a, b)
        return a, _integral(tt, vv) / span, max(ii)

    w0, w1 = stats(0), stats(1)
    if w0 is None or w1 is None:
        res["reason"] = f"run shorter than 2 x {window_cycles} cycles before t_end"
        return res
    dm = abs(w0[1] - w1[1]) / max(abs(w0[1]), 1e-30)
    di = abs(w0[2] - w1[2]) / max(abs(w0[2]), 1e-30)
    res.update(mean_vout_delta_rel=dm, ipk_delta_rel=di, window_start_s=w1[0],
               measure_window_s=[w0[0], t_end])
    if dm < mean_tol and di < ipk_tol:
        res["settled"] = True
        since, newer, k = w1[0], w1, 2
        while True:
            older = stats(k)
            if older is None:
                break
            if not (abs(newer[1] - older[1]) / max(abs(newer[1]), 1e-30) < mean_tol
                    and abs(newer[2] - older[2]) / max(abs(newer[2]), 1e-30) < ipk_tol):
                break
            since, newer, k = older[0], older, k + 1
        res["settled_since_s"] = since
    else:
        res["reason"] = "consecutive windows differ by more than the §0.4 tolerances"
    return res


def switching_frequency(t, vsw, vin, t0, t1, *, min_cycles=MIN_FSW_CYCLES):
    """R7: rising crossings of vin/2 on V(sw) in [t0, t1], Schmitt-guarded
    against edge ringing. Unavailable below `min_cycles` cycles."""
    vth, vlo = vin / 2.0, vin / 4.0
    armed, crossings = False, []
    for i in range(1, len(t)):
        if vsw[i - 1] < vlo:
            armed = True
        if armed and vsw[i - 1] < vth <= vsw[i]:
            dv = vsw[i] - vsw[i - 1]
            tx = t[i - 1] + (vth - vsw[i - 1]) / dv * (t[i] - t[i - 1])
            armed = False
            if t0 <= tx <= t1:
                crossings.append(tx)
    cycles = max(len(crossings) - 1, 0)
    res = {"available": False, "hz": None, "cycles": cycles, "t_start_s": t0, "t_end_s": t1,
           "min_cycles": min_cycles}
    if cycles < min_cycles:
        res["reason"] = f"{cycles} settled cycles in window, need >= {min_cycles}"
        return res
    res.update(available=True, hz=cycles / (crossings[-1] - crossings[0]))
    return res


def efficiency(t, vout, pin, i_load, f_sw, *, t_end=None, t_clk0=0.0, n_cycles=WINDOW_CYCLES):
    """R9/R10: Pout/Pin over `n_cycles` whole cycles ending on a cycle boundary.
    Pout = Vout x i_load (ideal current sink); a partial last cycle is dropped."""
    if t_end is None:
        t_end = cycle_floor(t[-1], f_sw, t_clk0)
    t0 = t_end - n_cycles / f_sw
    if t0 < t[0] - _EPS_CYCLES / f_sw:
        raise ValueError("efficiency window starts before the data")
    span = t_end - t0
    pout = i_load * window_mean(t, vout, t0, t_end)
    pin_w = window_mean(t, pin, t0, t_end)
    return {**_win_info(t0, t_end, f_sw), "pout_w": pout, "pin_w": pin_w,
            "eta": pout / pin_w if pin_w > 0 else None, "i_load_a": i_load, "span_s": span}


def load_step(t, vout, t_step, v_ref, band, f_sw):
    """R12: deviation (larger of under/overshoot about v_ref) and recovery time
    (to the last exit from +-band, measured from t_step). Recovered only if
    Vout ends the run inside the band for >= 20 consecutive cycles."""
    t_last = t[-1]
    tt, (vv,) = window(t, [vout], t_step, t_last)
    under = max(v_ref - min(vv), 0.0)
    over = max(max(vv) - v_ref, 0.0)
    last_out = None
    for i in range(len(tt) - 1, -1, -1):
        if abs(vv[i] - v_ref) > band:
            last_out = i
            break
    if last_out is None:
        t_exit = t_step
    elif last_out == len(tt) - 1:
        t_exit = None
    else:
        # linear crossing of the band edge between the last outside sample and the next
        edge = band if vv[last_out] > v_ref else -band
        a, b = vv[last_out] - v_ref, vv[last_out + 1] - v_ref
        t_exit = tt[last_out] + (edge - a) / (b - a) * (tt[last_out + 1] - tt[last_out])
    recovered = t_exit is not None and (t_last - t_exit) >= BAND_CYCLES / f_sw
    cycles_after = (t_last - t_step) * f_sw
    return {
        "t_step_s": t_step, "t_end_s": t_last, "cycles_after_step": cycles_after,
        "v_ref_v": v_ref, "band_v": band,
        "undershoot_v": under, "overshoot_v": over, "deviation_v": max(under, over),
        "recovered": recovered,
        "recovery_time_s": (t_exit - t_step) if recovered else None,
        "run_long_enough": recovered and cycles_after >= LOAD_STEP_MIN_CYCLES,
    }


def ideal_vout(vin, duty, i_load, *, dcr, r_wire, wires, ron_hs, ron_ls):
    """Hand-derived open-loop DC value: D*Vin less the DC drops. The SW wires
    and DCR carry the load current all cycle; the VIN path (wires + HS) for D,
    the GND path (wires + LS) for 1-D. Not traced; the bench checks it."""
    r_net = r_wire / wires
    r_path = dcr + r_net + duty * (r_net + ron_hs) + (1.0 - duty) * (r_net + ron_ls)
    return duty * vin - i_load * r_path


def analyze(wrdata_path, *, f_sw, vin, tier_params, step_max, t_settle_end=None,
            load_step_spec=None, t_clk0=0.0, fc_ripple=RIPPLE_LP_HZ):
    """Grade one wrdata run. `tier_params` is the flat parameter dict of the
    bench (i_load is required; duty, dcr, r_wire, wires, ron_hs, ron_ls enable
    the ideal-value comparison). `load_step_spec` = {t_step, band_v[, v_ref]}."""
    d = read_wrdata(wrdata_path)
    t, vout, il, vsw, pin = (d[k] for k in WRDATA_COLUMNS)
    T = 1.0 / f_sw
    max_dt = max(b - a for a, b in zip(t, t[1:]))
    run = {
        "t_first_s": t[0], "t_last_s": t[-1], "run_length_s": t[-1] - t[0],
        "n_points": len(t), "f_sw_commanded_hz": f_sw, "period_s": T,
        "run_cycles": (t[-1] - t[0]) * f_sw,
        "step_max_spec_s": step_max, "step_max_observed_s": max_dt,
        "step_ok": max_dt <= step_max * (1 + 1e-3),
        "analysis": "ngspice .tran (no periodic steady state), settled per spec §0.4",
    }
    if t_settle_end is None:
        t_settle_end = cycle_floor(load_step_spec["t_step"] if load_step_spec else t[-1],
                                   f_sw, t_clk0)
    st = settle(t, vout, il, f_sw, t_end=t_settle_end, t_clk0=t_clk0)
    out = {"run": run, "tier_params": tier_params, "settle": st}
    na = {"available": False, "reason": "not settled: no value is reported (§0.4)"}
    out.update(R4_vout_mean=na, R7_f_sw=na, R8_il_pp=na, R9_R10_efficiency=na,
               R11_ripple=na, R12_load_step=na)
    if st["settled"]:
        a, b = st["measure_window_s"]
        w = _win_info(a, b, f_sw)
        mean_v = window_mean(t, vout, a, b)
        r4 = {"available": True, **w, "mean_v": mean_v}
        keys = ("duty", "dcr", "r_wire", "wires", "ron_hs", "ron_ls")
        if all(k in tier_params for k in keys):
            ideal = ideal_vout(vin, tier_params["duty"], tier_params["i_load"],
                               **{k: tier_params[k] for k in keys[1:]})
            r4.update(
                ideal_v=ideal, rel_err_vs_ideal=(mean_v - ideal) / ideal,
                ideal_formula="D*Vin - I*(DCR + Rnet + D*(Rnet+Ron_hs) + (1-D)*(Rnet+Ron_ls)),"
                              " Rnet = r_wire/wires",
                d_vin_v=tier_params["duty"] * vin)
        out["R4_vout_mean"] = r4
        tt, (ii,) = window(t, [il], a, b)
        out["R8_il_pp"] = {"available": True, **w, "pp_a": max(ii) - min(ii)}
        w1s = st["window_start_s"]
        tt, (vv,) = window(t, [vout], w1s, b)
        filt = lowpass(tt, vv, fc_ripple)
        sel = [f for x, f in zip(tt, filt) if x >= a]
        out["R11_ripple"] = {"available": True, **w, "pp_v": max(sel) - min(sel),
                             "lowpass_hz": fc_ripple, "lowpass_order": 1,
                             "lowpass_warmup_from_s": w1s}
        out["R9_R10_efficiency"] = {"available": True, **efficiency(
            t, vout, pin, tier_params["i_load"], f_sw, t_end=b, t_clk0=t_clk0)}
        out["R7_f_sw"] = switching_frequency(t, vsw, vin, st["settled_since_s"], b)
    if load_step_spec:
        if not st["settled"]:
            out["R12_load_step"] = {"available": False,
                                    "reason": "step applied to a run that was not settled"}
        else:
            t_step = load_step_spec["t_step"]
            v_ref = load_step_spec.get("v_ref")
            if v_ref is None:
                tail_end = cycle_floor(t[-1], f_sw, t_clk0)
                v_ref = window_mean(t, vout, tail_end - WINDOW_CYCLES * T, tail_end)
                v_ref_src = "mean Vout over the last 20 whole cycles of the run"
            else:
                v_ref_src = "given"
            # Same 20 MHz first-order low-pass as R11: raw edge spikes (ESL) would
            # otherwise set the deviation and keep Vout out of the 1 % band.
            vout_lp = lowpass(t, vout, fc_ripple)
            out["R12_load_step"] = {
                "available": True, "v_ref_source": v_ref_src, "lowpass_hz": fc_ripple,
                "lowpass_order": 1,
                **load_step(t, vout_lp, t_step, v_ref, load_step_spec["band_v"], f_sw)}
    return out


def _main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("wrdata")
    ap.add_argument("--params", required=True, help="bench params.json (flat)")
    ap.add_argument("--out", help="write JSON here instead of stdout")
    args = ap.parse_args(argv)
    with open(args.params) as fh:
        p = json.load(fh)
    spec = None
    if "t_step" in p:
        spec = {"t_step": p["t_step"], "band_v": p["band_v"]}
    res = analyze(args.wrdata, f_sw=p["f_sw"], vin=p["vin"], tier_params=p,
                  step_max=1.0 / (STEP_DIVISOR * p["f_sw"]), load_step_spec=spec)
    text = json.dumps(res, indent=2, sort_keys=True) + "\n"
    if args.out:
        with open(args.out, "w") as fh:
            fh.write(text)
    else:
        sys.stdout.write(text)
    return 0 if res["settle"]["settled"] else 2


if __name__ == "__main__":
    sys.exit(_main())
