#!/usr/bin/env python3
"""Grade finished current-limit benches and write one append-only record (spec R16).

  python3 -I sim/current-limit/collect.py --ramp RAMP.json --min MIN.json [--dry]

ramp: C-full, load ramped 0 -> 3 A after soft start; the trip current is I(L) at the first rising
      crossing of TRIP (xtop.trip) after the ramp starts, judged against 0.70 - 2.1 A. A unit whose
      TRIP never asserts has NO trip value ("no trip"), never a pass; the row is then not_demonstrated.
min:  R16 min bound, L -20 %, Vin 5.5 V, 500 mA, all process x T points: TRIP must not assert while
      the 500 mA is held, and peak I(L) must stay below 0.70 A. The condition is "f min": the free-running
      oscillator's f of each unit is measured, and the row is `pass` only if every unit ran at or below
      1.7 MHz; otherwise it is `not_demonstrated` (the no-trip result is still recorded per unit).
Nothing is relaxed. Simulated, never measured.
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "lib"))
import buckmeas  # noqa: E402
import rawgrade  # noqa: E402
import recordkit  # noqa: E402

TRIP_BOUNDS = (0.70, 2.1)             # A, R16
F_MIN_HZ = 1.7e6                      # R7 min
TRIP_LEVEL = 1.65                     # V, VDD33 / 2
T_R0 = 600e-6                         # s, bench.spice: load ramp starts
MIN_SETTLE_S = 10e-6                  # min case: peak I(L) and f read from 10 us after the 1 us load step
V_REG_MIN = 0.9 * 1.8                 # V: Vout at the start of the load must be >= 90 % of target (start-up done)
STEP_MAX = 2.5e-9
NEEDED = ("time", "v(out)", "i(lind)", "v(sw_d)", "v(xtop.trip)")


def unit_base(c):
    key, p = recordkit.parse_corner(c["corner_id"])
    u = {"id": c["corner_id"], **key, "params": p, "klt_status": c.get("status")}
    raw = (c.get("artifacts") or {}).get("raw")
    if c.get("status") not in ("pass", "fail") or not raw or not os.path.exists(raw):
        u.update(graded=False, reason="no waveform: klt status %s %s" % (c.get("status"), [(d.get("code"), (d.get("message") or "")[-90:]) for d in c.get("diagnostics") or []][:1]))
        return u, None
    d = rawgrade.read_ascii_raw(raw, NEEDED)
    t = d["time"]
    u.update(graded=True, window_s=[t[0], t[-1]], step_max_s=max(b - a for a, b in zip(t, t[1:])))
    u["step_ok"] = u["step_max_s"] <= STEP_MAX * (1 + 1e-3)
    return u, d


def ramp_unit(c):
    u, d = unit_base(c)
    if d is None:
        return u
    t, il, trip = d["time"], d["i(lind)"], d["v(xtop.trip)"]
    ev = buckmeas.trip_event(t, trip, il, TRIP_LEVEL, t_from=T_R0)
    u["trip"] = ev
    u["vout_at_load_start_v"] = d["v(out)"][0]
    u["in_regulation_at_load_start"] = d["v(out)"][0] >= V_REG_MIN
    if ev["engaged"]:
        p = u["params"]
        u["load_at_trip_a"] = min(p["i_end"], p["i_end"] * (ev["t_trip_s"] - T_R0) / p["t_ramp"])
        u["trip_il_a"] = ev["trip_il_a"]
    else:
        u["reason"] = ev["reason"]
    return u


def min_unit(c):
    u, d = unit_base(c)
    if d is None:
        return u
    t, il, trip = d["time"], d["i(lind)"], d["v(xtop.trip)"]
    t0 = T_R0 + MIN_SETTLE_S
    ev = buckmeas.trip_event(t, trip, il, TRIP_LEVEL, t_from=T_R0)
    xs = [x for x in rawgrade.sw_rising_crossings(t, d["v(sw_d)"], u["vin_v"]) if x >= t0]
    f_sw = (len(xs) - 1) / (xs[-1] - xs[0]) if len(xs) > 2 else None
    tt, (ii,) = buckmeas.window(t, [il], t0, t[-1])
    u.update(vout_at_load_start_v=d["v(out)"][0], in_regulation_at_load_start=d["v(out)"][0] >= V_REG_MIN)
    u.update(trip=ev, n_trip_assertions=ev["n_assertions"], peak_il_a=max(ii), f_sw_hz=f_sw,
             f_cycles=max(len(xs) - 1, 0), f_min_condition=None if f_sw is None else f_sw <= F_MIN_HZ,
             window_s=[t0, t[-1]], hold_s=t[-1] - T_R0)
    return u


def judge(ramp, mn):
    rows = {}
    nov = [u["id"] for u in ramp if u.get("trip_il_a") is None]
    val = [u for u in ramp if u.get("trip_il_a") is not None]
    out = [u for u in val if not TRIP_BOUNDS[0] <= u["trip_il_a"] <= TRIP_BOUNDS[1]]
    lo = min(val, key=lambda u: u["trip_il_a"], default=None)
    hi = max(val, key=lambda u: u["trip_il_a"], default=None)
    rows["R16_trip_window"] = {
        "what": "cycle-by-cycle limit: I(L) at first TRIP assertion while the load ramps 0 -> 3 A over 300 us, C-full; bounds %.2f - %.1f A "
                "(a die-protection threshold, not a precision limit)" % TRIP_BOUNDS,
        "bounds_a": list(TRIP_BOUNDS), "n_units": len(ramp), "n_valued": len(val), "n_no_trip_or_no_value": len(nov),
        "n_out_of_bounds": len(out),
        "n_not_in_regulation_at_ramp_start": sum(1 for u in ramp if u.get("in_regulation_at_load_start") is False),
        "not_in_regulation_units": [u["id"] for u in ramp if u.get("in_regulation_at_load_start") is False],
        "regulation_note": "a unit whose Vout is below 90 % of 1.8 V when the ramp starts never finished soft start (R15 fails there); "
                           "its trip value is recorded but the ramp did not start from a regulating converter",
        "verdict": "fail" if out else ("not_demonstrated" if nov or not ramp else "pass"),
        "binding_min": None if lo is None else {"id": lo["id"], "trip_il_a": lo["trip_il_a"], "margin_a": lo["trip_il_a"] - TRIP_BOUNDS[0]},
        "binding_max": None if hi is None else {"id": hi["id"], "trip_il_a": hi["trip_il_a"], "margin_a": TRIP_BOUNDS[1] - hi["trip_il_a"]},
        "failing_units": [u["id"] for u in out], "no_trip_or_no_value_units": nov}
    mv = [u for u in mn if "n_trip_assertions" in u and u["in_regulation_at_load_start"]]
    noreg = [u["id"] for u in mn if "n_trip_assertions" in u and not u["in_regulation_at_load_start"]]
    tripped = [u["id"] for u in mv if u["n_trip_assertions"] > 0 or u["peak_il_a"] >= TRIP_BOUNDS[0]]
    mnov = [u["id"] for u in mn if "n_trip_assertions" not in u]
    notf = [u["id"] for u in mv if not u["f_min_condition"]]
    worst = max(mv, key=lambda u: u["peak_il_a"], default=None)
    verdict = "fail" if tripped else ("not_demonstrated" if mnov or noreg or notf or not mn else "pass")
    rows["R16_min_bound_no_trip"] = {
        "what": "no trip at 500 mA, L -20 %, Vin 5.5 V, all process x T, at f min (<= 1.7 MHz measured per unit); peak I(L) < 0.70 A. "
                "Judged only on units whose Vout was in regulation (>= 90 % of 1.8 V) when the 500 mA was applied",
        "n_units": len(mn), "n_no_waveform": len(mnov), "n_not_in_regulation_at_load_start": len(noreg),
        "n_valued": len(mv), "n_tripped_or_peak_over_min": len(tripped),
        "n_f_not_at_min": len(notf), "verdict": verdict,
        "binding": None if worst is None else {"id": worst["id"], "peak_il_a": worst["peak_il_a"], "f_sw_hz": worst["f_sw_hz"],
                                              "margin_a": TRIP_BOUNDS[0] - worst["peak_il_a"]},
        "failing_units": tripped, "no_value_units": mnov, "not_in_regulation_units": noreg, "units_not_at_f_min": notf,
        "note": "the oscillator free-runs; a unit with f_sw above 1.7 MHz shows no trip but does not exercise the f-min condition"}
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ramp", required=True)
    ap.add_argument("--min", required=True, dest="mn")
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args(argv)
    reps = {k: json.load(open(p)) for k, p in (("ramp", a.ramp), ("min", a.mn))}
    ramp = [ramp_unit(c) for c in reps["ramp"]["corners"]]
    mn = [min_unit(c) for c in reps["min"]["corners"]]
    rows = judge(ramp, mn)
    ts, sha, hdr = recordkit.header(HERE)
    fields = ("provider", "job_id", "instance_type", "state")

    def env(k, p):
        return recordkit.report_env(reps[k], p, fields)
    rec = {
        "record": "simulated, not measured; pre-layout; spec R16",
        "environment": {**hdr, "reports": [env("ramp", a.ramp), env("min", a.mn)],
                        "files_sha256": recordkit.files_sha256(
                            HERE, ("bench.spice", "request_ramp.json", "request_min.json", "gen_requests.py"),
                            ("design/netlists/buck_top.spice",), ("buckmeas.py", "rawgrade.py"))},
        "method": {
            "analysis_ramp": ".tran 2.5n 920u, saved from 600 us; max step 2.5 ns = T/200 at 2 MHz; soft start done by 520 us (R15 max), "
                             "load 0 -> 3 A linear over 300 us from 600 us (10 mA/us, ~5 mA per cycle)",
            "analysis_min": ".tran 2.5n 760u, saved from 600 us; 500 mA reached in 1 us at 600 us and held 160 us (~320 cycles); "
                            "peak I(L) and f are read from 610 us (10 us after the step)",
            "trip": "I(L) interpolated at the first rising crossing of 1.65 V (VDD33 / 2) on xtop.trip after 600 us; the digital delay "
                    "between the sense crossing and TRIP is included in the value",
            "steady_state": "the ramp is quasi-static against the loop (fc 100 - 250 kHz); no steady-state claim is made on the ramp run. "
                            "The min case holds 500 mA for ~320 cycles (> the 100-cycle step rule of 0.4)",
            "corner_counts": {"ramp": len(ramp), "min": len(mn)}},
        "rows": rows, "units": {"ramp": ramp, "min": mn}}
    if a.dry:
        print(json.dumps(rows, indent=1))
        return 0
    return recordkit.write_record(os.path.join(HERE, "records", "%s-%s.json" % (ts, sha)), rec)


if __name__ == "__main__":
    sys.exit(main())
