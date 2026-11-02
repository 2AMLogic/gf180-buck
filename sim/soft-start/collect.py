#!/usr/bin/env python3
"""Grade a finished soft-start bench and write one append-only record (spec R15, R6 clause).

  python3 -I sim/soft-start/collect.py --report GRID.json [--dry]

Reads the klt sim report, measures every unit's waveform.raw with buckmeas.soft_start
(0 -> 90 % of 1.8 V from EN, monotonic, overshoot above R4 max, peak I(L)) and buckmeas.trip_event
(TRIP = xtop.trip), then judges against the target-tier bounds below. A unit with no waveform, a
timeout, or a Vout that never reaches 90 % contributes NO value: the row is `not_demonstrated`
(or `fail` if another unit is out of bounds). Nothing is relaxed. Simulated, never measured.
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

V_TARGET = 1.8                        # V, R4 typ
V_REG_MAX = 1.872                     # V, R4 max
T90 = (100e-6, 500e-6)                # s, R15
OVERSHOOT_MAX = 0.090                 # V, R15 (5 % of Vout) above R4 max
IL_TRIP_MIN = 0.70                    # A, R16 min trip: the peak I(L) during start must stay below
T_EN = 20e-6                          # s, bench.spice EN rise
TRIP_LEVEL = 1.65                     # V, VDD33 / 2 on the digital TRIP net
R6_TAIL_S = 100e-6                    # R6 clause is read on the last 100 us (~200 cycles) at 0 load
STEP_MAX = 2.5e-9
NEEDED = ("time", "v(out)", "i(lind)", "v(sw_d)", "v(xtop.trip)")


def unit_record(c):
    key, params = recordkit.parse_corner(c["corner_id"])
    u = {"id": c["corner_id"], **key, "rload_ohm": params["rload"], "klt_status": c.get("status")}
    u["load"] = "none" if u["rload_ohm"] > 1e6 else "%g ohm" % u["rload_ohm"]
    raw = (c.get("artifacts") or {}).get("raw")
    if c.get("status") not in ("pass", "fail") or not raw or not os.path.exists(raw):
        u.update(graded=False, reason="no waveform: klt status %s %s" % (c.get("status"), [(d.get("code"), (d.get("message") or "")[-90:]) for d in c.get("diagnostics") or []][:1]))
        return u
    d = rawgrade.read_ascii_raw(raw, NEEDED)
    t = d["time"]
    edges = rawgrade.sw_rising_crossings(t, d["v(sw_d)"], u["vin_v"])
    if not edges or edges[0] <= t[0] or abs(d["v(out)"][0]) > 0.05 * V_TARGET:
        u.update(graded=False, reason="switching already under way at the start of the saved window (EN): start-up not captured")
        return u
    u.update(graded=True, step_max_s=max(b - a for a, b in zip(t, t[1:])), window_s=[t[0], t[-1]],
             run_cycles_saved=len(edges) - 1)
    u["step_ok"] = u["step_max_s"] <= STEP_MAX * (1 + 1e-3)
    ss = buckmeas.soft_start(t, d["v(out)"], d["i(lind)"], edges, t_en=T_EN, v_target=V_TARGET, v_reg_max=V_REG_MAX)
    u["soft_start"] = ss
    tail = buckmeas.trip_event(t, d["v(xtop.trip)"], d["i(lind)"], TRIP_LEVEL, t_from=t[-1] - R6_TAIL_S)
    whole = buckmeas.trip_event(t, d["v(xtop.trip)"], d["i(lind)"], TRIP_LEVEL)
    u["trip_tail"] = {k: tail[k] for k in ("engaged", "n_assertions", "t_from_s", "t_end_s")}
    u["trip_whole_run"] = {k: whole[k] for k in ("engaged", "n_assertions", "trip_il_a")}
    if ss["available"]:
        checks = {"t_90": T90[0] <= ss["t_90_s"] <= T90[1], "monotonic": ss["monotonic"],
                  "overshoot": ss["overshoot_v"] <= OVERSHOOT_MAX, "peak_il": ss["peak_il_a"] < IL_TRIP_MIN}
        u["r15_checks"] = checks
        u["r15_ok"] = all(checks.values()) and u["step_ok"]
    elif t[-1] - T_EN > T90[1]:
        # a valid, step-checked run in which Vout is still below 90 % after the 500 us limit: a definite
        # failure of the t_90 bound (no time value), not missing data
        u["r15_checks"] = {"t_90": False, "monotonic": None, "overshoot": None, "peak_il": None}
        u["r15_ok"] = False
        u["r15_fail_reason"] = "%s within %.0f us of EN (limit %.0f us)" % (ss["reason"], (t[-1] - T_EN) * 1e6, T90[1] * 1e6)
        u["peak_il_a_whole_run"] = max(d["i(lind)"])
    else:
        u["r15_ok"] = None
        u["reason"] = ss["reason"]
    if u["rload_ohm"] > 1e6:
        u["r6_ok"] = not tail["engaged"]
    return u


def margins(u):
    s = u["soft_start"]
    return {"t_90_s": min(s["t_90_s"] - T90[0], T90[1] - s["t_90_s"]), "overshoot_v": OVERSHOOT_MAX - s["overshoot_v"],
            "peak_il_a": IL_TRIP_MIN - s["peak_il_a"], "max_drawdown_v": s["mono_eps_v"] - s["max_drawdown_v"]}


def judge(units):
    rows = {}
    nov = [u["id"] for u in units if u.get("r15_ok") is None]
    bad = [u["id"] for u in units if u.get("r15_ok") is False]
    valued = [u for u in units if u.get("r15_ok") is not None]
    timed = [u for u in valued if u["soft_start"]["available"]]
    bind = {}
    for k in ("t_90_s", "overshoot_v", "peak_il_a", "max_drawdown_v"):
        if timed:
            w = min(timed, key=lambda u: margins(u)[k])
            bind[k] = {"id": w["id"], "value": w["soft_start"][k], "margin": margins(w)[k]}
    per_load = {}
    for load in sorted({u["load"] for u in units}):
        v = [u for u in valued if u["load"] == load]
        per_load[load] = {"n_valued": len(v), "n_fail": sum(1 for u in v if not u["r15_ok"])}
    rows["R15"] = {
        "what": "soft start 0 -> 90 %% of %.1f V from EN: %g - %g us, monotonic (per-cycle mean, %g mV floor), overshoot above R4 max <= %g mV, "
                "peak I(L) < %.2f A (R16 min trip); C-full x load {none, 3.6 ohm}" % (
                    V_TARGET, T90[0] * 1e6, T90[1] * 1e6, 1e3 * buckmeas.MONO_EPS_V, OVERSHOOT_MAX * 1e3, IL_TRIP_MIN),
        "n_units": len(units), "n_valued": len(valued), "n_fail": len(bad), "n_no_value": len(nov),
        "n_never_reached_90pct_in_window": sum(1 for u in units if u.get("r15_fail_reason")),
        "verdict": "fail" if bad else ("not_demonstrated" if nov or not units else "pass"),
        "binding_per_criterion": bind, "per_load": per_load, "failing_units": bad, "no_value_units": nov}
    r6u = [u for u in units if u["rload_ohm"] > 1e6]
    r6_nov = [u["id"] for u in r6u if u.get("r6_ok") is None]
    r6_bad = [u["id"] for u in r6u if u.get("r6_ok") is False]
    rows["R6_no_trip_at_0_load"] = {
        "what": "R6 clause: at 0 load the reverse inductor peak does not trip the limit; TRIP (xtop.trip) never asserts in the last %g us "
                "of the run (Vout in regulation), C-full" % (R6_TAIL_S * 1e6),
        "n_units": len(r6u), "n_no_value": len(r6_nov), "n_fail": len(r6_bad),
        "verdict": "fail" if r6_bad else ("not_demonstrated" if r6_nov or not r6u else "pass"),
        "failing_units": r6_bad, "no_value_units": r6_nov,
        "il_min_note": "TRIP assertions during the start itself are recorded per unit (trip_whole_run), not graded here; R15 grades the start by peak I(L)"}
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--report", required=True, help="klt sim report JSON of request_grid.json")
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args(argv)
    rep = json.load(open(a.report))
    units = [unit_record(c) for c in rep["corners"]]
    rows = judge(units)
    ts, sha, hdr = recordkit.header(HERE)
    rec = {
        "record": "simulated, not measured; pre-layout; spec R15 and the R6 no-trip clause",
        "environment": {**hdr,
                        "report": {"file": os.path.basename(a.report), "status": rep.get("status"),
                                   "remote": recordkit.remote_subset(rep, ("provider", "job_id", "instance_type", "state"))},
                        "files_sha256": recordkit.files_sha256(
                            HERE, ("bench.spice", "request_grid.json", "gen_requests.py"),
                            ("design/netlists/buck_top.spice",), ("buckmeas.py", "rawgrade.py"))},
        "method": {
            "analysis": ".tran 2.5n 700u, saved from 20 us (EN); max step 2.5 ns = T/200 at 2 MHz (unit.step_ok)",
            "startup": "Vin ramps 0 -> Vin over 10 us, control rails / bias over 5 us, EN at 20 us; load resistor present from t = 0",
            "t_90": "per-cycle mean of Vout (cycles between rising crossings of Vin/2 on V(sw)) first >= 0.9 x 1.8 V, interpolated, from EN",
            "steady_state": "not applicable to the start itself: the run ends 180 us after the latest allowed 90 % time; the R6 clause "
                            "reads the last 100 us (~200 cycles) at 0 load",
            "overshoot": "peak of Vout after the 20 MHz first-order low-pass (as R11), minus the R4 max 1.872 V",
            "corner_count": len(units)},
        "rows": rows, "units": units}
    if a.dry:
        print(json.dumps(rows, indent=1))
        return 0
    return recordkit.write_record(os.path.join(HERE, "records", "%s-%s.json" % (ts, sha)), rec)


if __name__ == "__main__":
    sys.exit(main())
