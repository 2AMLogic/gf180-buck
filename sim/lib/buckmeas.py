"""buckmeas: grade a switching-converter .tran the way spec/target-spec.md §0.4 says.

PDK-free, stdlib-only (no numpy), so `python3 -m unittest discover sim/lib`
runs on a bare host. It reads ngspice `wrdata` output (time, V(out), I(L),
V(sw), input power) and returns, for the last settled 20 cycles:

  R4   mean Vout                      R9/R10  efficiency (whole cycles only)
  R7   switching frequency (>= 100)   R11     ripple after a 20 MHz 1st-order LP
  R8   inductor ripple p-p            R12     load-step deviation and recovery

and, on a start-up / over-current run, `soft_start` (R15: 0 -> 90 % time,
monotonicity, overshoot, peak I(L)) and `trip_event` (R16: the inductor
current at which the cycle-by-cycle limit first asserts; no assertion means
no trip value, never a pass).

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
F_SW_SPEC_HZ = 2.0e6  # §0.4: the commanded switching clock every bench of this block is run at
STEP_MAX_S = 1.0 / (STEP_DIVISOR * F_SW_SPEC_HZ)  # 2.5 ns: the §0.4 max step at F_SW_SPEC_HZ
STEP_TOL = 1e-3  # §0.4: the max step is met to 0.1 %
MONO_EPS_V = 1e-3  # R15: a per-cycle mean may sag this far (1 mV) before "monotonic" fails
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


def step_check(t, step_max=STEP_MAX_S):
    """§0.4 max-step rule on a time column -> (largest observed step [s], within the rule).

    The rule is met to STEP_TOL (0.1 %), so a run whose largest step is exactly
    `step_max * (1 + STEP_TOL)` still passes. One implementation for every bench:
    `analyze_columns` and the collectors all grade the step this way.
    """
    max_dt = max(b - a for a, b in zip(t, t[1:]))
    return max_dt, max_dt <= step_max * (1 + STEP_TOL)


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


def load_step_pair(t, vout, il, f_sw, t_up, t_dn, band, *, t_clk0=0.0, fc_ripple=RIPPLE_LP_HZ):
    """R12: an up step at t_up and the step back at t_dn on one run.

    Each step is graded only if the §0.4 settled test passes on the cycles just
    before it (50 mA state for the up step, 450 mA state for the step back); else
    that step reports no value. Deviation and recovery use the 20 MHz low-pass of
    Vout (as R11) and the reference Vout the run settles to after the step: the
    mean over the last 20 whole cycles of that step's hold (up: before t_dn;
    back: end of run). The up step's hold is cut at t_dn so the second edge
    cannot leak into it."""
    T = 1.0 / f_sw
    lp = lowpass(t, vout, fc_ripple)
    out = {}
    for name, ts, te, t_hold_end in (("up", t_up, t_dn, t_dn), ("back", t_dn, None, t[-1])):
        st = settle(t, vout, il, f_sw, t_end=cycle_floor(ts, f_sw, t_clk0), t_clk0=t_clk0)
        res = {"settle_before_step": st, "available": False}
        if not st["settled"]:
            res["reason"] = "not settled before the step: no value is reported (§0.4)"
            out[name] = res
            continue
        end = cycle_floor(t_hold_end, f_sw, t_clk0)
        v_ref = window_mean(t, vout, end - WINDOW_CYCLES * T, end)
        tt, (vv,) = window(t, [lp], t[0], t_hold_end)
        ls = load_step(tt, vv, ts, v_ref, band, f_sw)
        v_pre = window_mean(t, vout, st["measure_window_s"][0], st["measure_window_s"][1])
        res.update(available=True, v_pre_step_mean_v=v_pre, lowpass_hz=fc_ripple,
                   v_ref_window_s=[end - WINDOW_CYCLES * T, end], **ls)
        out[name] = res
    return out


def crosscheck(switched, predicted, tol=0.30):
    """R13(c): |switched - predicted| / predicted within +-tol. Relative error is
    undefined when predicted is 0: equal zeros agree, anything else does not.
    A missing value on either side is `no_value`, never a pass."""
    if switched is None or predicted is None:
        return {"switched": switched, "predicted": predicted, "rel_err": None, "tol": tol,
                "verdict": "no_value"}
    if predicted == 0:
        ok = switched == 0
        return {"switched": switched, "predicted": predicted, "rel_err": 0.0 if ok else None,
                "tol": tol, "verdict": "pass" if ok else "fail"}
    rel = (switched - predicted) / predicted
    return {"switched": switched, "predicted": predicted, "rel_err": rel, "tol": tol,
            "verdict": "pass" if abs(rel) <= tol else "fail"}


def crossings(t, y, level, rising=True, t_from=None):
    """Linearly interpolated crossing times of y through `level` (rising or
    falling) at or after t_from. Rising: y[i-1] < level <= y[i]; falling:
    y[i-1] >= level > y[i]. The one edge-timing definition for R7, R14, R15, R16."""
    out = []
    for i in range(1, len(t)):
        if (t_from is not None and t[i] < t_from):
            continue
        if (rising and y[i - 1] < level <= y[i]) or (not rising and y[i - 1] >= level > y[i]):
            out.append(lerp_crossing(t[i - 1], t[i], y[i - 1], y[i], level))
    return out


def lerp_crossing(t0, t1, a, b, level):
    """Time at which the segment (t0, a) -> (t1, b) passes `level` (a != b)."""
    return t0 + (level - a) / (b - a) * (t1 - t0)


def cycle_means(t, y, edges):
    """Mean of y over each cycle between consecutive `edges`: [(t_mid, mean)]."""
    out = []
    for a, b in zip(edges, edges[1:]):
        tt, (yy,) = window(t, [y], a, b)
        out.append(((a + b) / 2.0, _integral(tt, yy) / (b - a)))
    return out


def soft_start(t, vout, il, edges, *, t_en, v_target, v_reg_max, frac=0.9,
               mono_eps=MONO_EPS_V, fc_over=RIPPLE_LP_HZ):
    """R15 on a start-up .tran. `edges` are the switching-cycle boundaries.

    t_90: time from t_en until the per-cycle mean of Vout first reaches
    frac * v_target (interpolated). monotonic: no cycle mean below its running
    maximum by more than `mono_eps`, up to that crossing (`max_drawdown_v`
    reported). overshoot: peak of Vout after the same 20 MHz first-order
    low-pass as R11, above `v_reg_max` (R4 max). peak_il: max I(L) from t_en.
    A run that never reaches the fraction has no t_90 and no monotonic verdict.
    """
    thr = frac * v_target
    res = {"available": False, "t_en_s": t_en, "v_target_v": v_target, "frac": frac,
           "threshold_v": thr, "t_start_s": t[0], "t_end_s": t[-1], "mono_eps_v": mono_eps,
           "cycles_seen": max(len(edges) - 1, 0)}
    cm = [(tm, m) for tm, m in cycle_means(t, vout, edges) if tm >= t_en]
    hit = next((i for i, (_, m) in enumerate(cm) if m >= thr), None)
    if hit is None:
        res["reason"] = "Vout never reached %.0f %% of target in the run" % (100 * frac)
        return res
    if hit == 0:
        t90 = cm[0][0]
    else:
        (ta, ma), (tb, mb) = cm[hit - 1], cm[hit]
        t90 = ta + (thr - ma) / (mb - ma) * (tb - ta)
    peak, draw = -math.inf, 0.0
    for _, m in cm[:hit + 1]:
        peak = max(peak, m)
        draw = max(draw, peak - m)
    tt, (vv, ii) = window(t, [vout, il], t_en, t[-1])
    over = max(lowpass(tt, vv, fc_over))
    res.update(available=True, t_90_s=t90 - t_en, t_90_abs_s=t90, monotonic=draw <= mono_eps,
               max_drawdown_v=draw, vout_peak_lp_v=over, overshoot_v=max(over - v_reg_max, 0.0),
               v_reg_max_v=v_reg_max, peak_il_a=max(ii), lowpass_hz=fc_over)
    return res


def trip_event(t, trip, il, level, *, t_from=None):
    """R16: inductor current at the first rising crossing of `level` on the
    trip net. Not asserted -> engaged False and no trip value."""
    xs = crossings(t, trip, level, True, t_from)
    res = {"engaged": False, "trip_il_a": None, "t_start_s": t[0], "t_end_s": t[-1],
           "t_from_s": t_from, "level_v": level, "n_assertions": len(xs),
           "il_max_a": max(il)}
    if not xs:
        res["reason"] = "TRIP never asserted in the window: no trip value"
        return res
    t0 = xs[0]
    tt, (ii,) = window(t, [il], t0, t[-1])
    res.update(engaged=True, t_trip_s=t0, trip_il_a=_interp(t, il, t0), il_peak_after_a=max(ii))
    return res


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
    return analyze_columns(*(d[k] for k in WRDATA_COLUMNS), f_sw=f_sw, vin=vin,
                           tier_params=tier_params, step_max=step_max,
                           t_settle_end=t_settle_end, load_step_spec=load_step_spec,
                           t_clk0=t_clk0, fc_ripple=fc_ripple)


def analyze_columns(t, vout, il, vsw, pin, *, f_sw, vin, tier_params, step_max,
                    t_settle_end=None, load_step_spec=None, t_clk0=0.0,
                    fc_ripple=RIPPLE_LP_HZ):
    """`analyze` on already-parsed columns (same arguments, same result)."""
    T = 1.0 / f_sw
    max_dt, step_ok = step_check(t, step_max)
    run = {
        "t_first_s": t[0], "t_last_s": t[-1], "run_length_s": t[-1] - t[0],
        "n_points": len(t), "f_sw_commanded_hz": f_sw, "period_s": T,
        "run_cycles": (t[-1] - t[0]) * f_sw,
        "step_max_spec_s": step_max, "step_max_observed_s": max_dt,
        "step_ok": step_ok,
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
