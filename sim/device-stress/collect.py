#!/usr/bin/env python3
"""Grade a finished device-stress run: write one R2 record and one R14 (top-level) record.

  python3 -I sim/device-stress/collect.py --report REPORT.json --set ctyp|grid [--dry]

Reads the klt sim report, grades each unit's waveform.raw (sim/lib/rawgrade.py for the clock and the
spec 0.4 settled test, sim/lib/stressmeas.py for the R2 peaks, the edge-window step and the R14 dead
times), and writes
  sim/device-stress/records/<UTC>-<sha>.json       R2  (SW >= -0.7 V, every power-device terminal <= 6.0 V)
  sim/dead-time/records/<UTC>-<sha>-top.json       R14 (dead time 1..6 ns, zero overlap) on buck_top

Verdict rules (nothing is relaxed): a limit exceeded anywhere in the saved window FAILS the unit, settled
or not, resolved or not (a coarser step can only under-read a peak, and R2 takes no transient credit); a
PASS needs a settled run, edge windows <= 100 ps, and every value inside its limit; a row is `pass` only
when the full 135-unit PVT grid is present and every unit is a pass (a subset such as C-typ never passes), and `not_demonstrated` otherwise. A unit that timed
out or errored contributes no value. Simulated, never measured.
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(HERE, "..", "lib"))
import rawgrade  # noqa: E402
import recordkit  # noqa: E402
import stressmeas as sm  # noqa: E402
from recordkit import parse_id  # noqa: E402

EXPECTED = {"grid": 135, "ctyp": 3}            # C-full x 3 loads; C-typ x 3 loads
R14_MIN, R14_TYP, R14_MAX = 1e-9, 3e-9, 6e-9   # spec target tier
LOADS = (0.0, 0.05, 0.5)
GATE_VECTORS = ("v(xtop.gh)", "v(xtop.gl)", "v(vin_d)", "v(gnd_d)")


def meas(corner, name):
    for m in corner.get("measurements") or []:
        if m.get("name") == name:
            return m.get("value")
    return None


def unit_record(corner):
    key = parse_id(corner["corner_id"])
    u = {"id": corner["corner_id"], **key, "klt_status": corner.get("status"),
         "klt_diagnostics": [d.get("code") for d in corner.get("diagnostics") or []],
         "vth_n_v": meas(corner, "vthn"), "vth_p_v": meas(corner, "vthp")}
    raw = (corner.get("artifacts") or {}).get("raw")
    if corner.get("status") not in ("pass", "fail") or not raw or not os.path.exists(raw):
        u.update(graded=False, settled=False, reason="no waveform: klt status %s %s" % (corner.get("status"), u["klt_diagnostics"]))
        return u
    try:
        c = rawgrade.read_ascii_raw(raw)
        missing = [v for v in GATE_VECTORS if v not in c]
        if missing:
            raise ValueError("rawfile lacks vectors %s" % missing)
    except (OSError, ValueError) as exc:
        u.update(graded=False, settled=False, reason=str(exc))
        return u
    t = c["time"]
    p = sm.stress_peaks(t, c["v(vin_d)"], c["v(sw_d)"], c["v(gnd_d)"], c["v(xtop.gh)"], c["v(xtop.gl)"])
    u["window_saved_s"] = [t[0], t[-1]]
    u["peaks"] = p
    u["sw_ok"], u["term_ok"] = sm.r2_verdict(p)
    u["edge"] = sm.edge_resolution(t, c["v(sw_d)"], key["vin_v"], c["v(xtop.gh)"], c["v(xtop.gl)"])
    g = rawgrade.grade(raw, key["vin_v"], key["iload_a"], 2.5e-9)
    u["graded"] = g["graded"]
    if not g["graded"]:
        u.update(settled=False, reason=g["reason"])
        win = (t[0], t[-1])
    else:
        st = g["settle"]
        u.update(settled=st["settled"], clock_hz=g["clock"]["f_hz"], settled_since_s=st["settled_since_s"],
                 mean_delta_rel=st["mean_vout_delta_rel"], ipk_delta_rel=st["ipk_delta_rel"])
        if not st["settled"]:
            u["reason"] = st.get("reason")
        win = tuple(st["measure_window_s"]) if st["settled"] else (t[0], t[-1])
    u["measure_window_s"] = list(win)
    vn, vp = u["vth_n_v"], u["vth_p_v"]
    if vn is None or vp is None:
        u["dead_time"] = None
        u["r14_reason"] = "Vth replica level missing: no threshold, no dead-time value"
    else:
        args = (t, c["v(vin_d)"], c["v(gnd_d)"], c["v(xtop.gh)"], c["v(xtop.gl)"], vn, vp)
        u["dead_time"] = sm.dead_time(*args, win[0], win[1])
        u["dead_time_saved_window"] = sm.dead_time(*args, t[0], t[-1])
    return u


def status_of(u, key, margin):
    """('fail'|'pass'|'no_value', margin). Fail beats everything (observed anywhere in the saved window)."""
    if margin is None:
        return "no_value"
    if margin < 0:
        return "fail"
    if u.get("settled") and (u.get("edge") or {}).get("ok"):
        return "pass"
    return "no_value"


def r2_margin(u):
    p = u.get("peaks")
    if not p:
        return None
    return min(p["sw_min_v"] - sm.R2_SW_MIN, sm.R2_TERM_MAX - max(p["terminal_max"]["abs_v"], p["sw_max_v"]))


def r14_margin(u):
    """Smallest slack to the 1..6 ns band over the measurement window; any overlap makes it negative."""
    d, w = u.get("dead_time"), u.get("dead_time_saved_window")
    if not d:
        return None
    cands = []
    for rec in (d, w):
        if rec["overlap_s"] > 0:
            cands.append(-rec["overlap_s"])
    if d["min_s"] is not None:
        cands += [d["min_s"] - R14_MIN, R14_MAX - d["max_s"]]
    return min(cands) if cands else None


def judge(units, name, margin_fn, expected, what, extra):
    marks = []
    for u in units:
        m = margin_fn(u)
        marks.append((u, m, status_of(u, name, m)))
    fails = [x for x in marks if x[2] == "fail"]
    passes = [x for x in marks if x[2] == "pass"]
    novalue = [x for x in marks if x[2] == "no_value"]
    valued = [x for x in marks if x[1] is not None]
    bind = min(valued, key=lambda x: x[1]) if valued else None
    # Completeness is measured against the full PVT grid, never against the subset the request named:
    # `expected` only labels the request (n_expected); a clean C-typ subset cannot pass.
    complete = len(units) == EXPECTED["grid"]
    verdict = "fail" if fails else ("pass" if complete and len(passes) == len(units) else "not_demonstrated")
    return {"what": what, "n_units": len(units), "n_expected": expected, "n_grid": EXPECTED["grid"], "corner_set_complete": complete,
            "verdict": verdict, "n_pass": len(passes), "n_fail": len(fails), "n_no_value": len(novalue),
            "binding": None if bind is None else {"id": bind[0]["id"], "margin": bind[1], "status": bind[2]},
            "failing_units": [x[0]["id"] for x in fails], "no_value_units": [x[0]["id"] for x in novalue],
            "unit_status": {x[0]["id"]: x[2] for x in marks}, **extra}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--report", required=True)
    ap.add_argument("--set", choices=sorted(EXPECTED), required=True, help="corner set the request named")
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args(argv)
    rep = json.load(open(a.report))
    units = [unit_record(c) for c in rep["corners"]]
    ts, sha, env = recordkit.header(HERE)
    n_corners = len({(u["process"], u["vin_v"], u["temp_c"]) for u in units})
    common = {
        "record": "simulated, not measured; pre-layout; C-%s x loads %s mA = %d units (%d corner points)" % (
            "full" if a.set == "grid" else "typ", [int(x * 1000) for x in LOADS], len(units), n_corners),
        "environment": {**env, "local_grader_python": sys.version.split()[0], "local_ngspice_banner": recordkit.ngspice_banner(),
                        "report": {"file": os.path.basename(a.report), "status": rep.get("status"),
                                   "remote": recordkit.remote_subset(rep),
                                   "jobs": ((rep.get("environment") or {}).get("remote") or {}).get("jobs") or None},
                        "files_sha256": recordkit.files_sha256(
                            HERE, ("bench.spice", "../steady-state/opamp_two_stage.spice", "request_%s.json" % a.set, "gen_requests.py"),
                            ("design/netlists/buck_top.spice",), ("stressmeas.py", "rawgrade.py"))},
        "method": {
            "analysis": ".tran 100p 600u, waveforms saved from 540u (a 60 us tail); max step 100 ps over the WHOLE run (spec 0.4 edge-window step)",
            "edge_window": "[-2 ns, +10 ns] around every mid-swing crossing of SW and both gates; the unit's largest step inside them is units[].edge.max_step_s, "
                           "and a unit with any step > 100 ps has no PASS",
            "startup": "Vin ramps 0 -> Vin over 10 us, control rails/bias over 5 us, EN at 20 us (soft start ~200 us), load applied 0 -> I at 260 us over 0.5 us",
            "steady_state": "spec 0.4: two consecutive 20-cycle windows < 0.1 % in mean Vout and < 1 % in peak I(L); the record gives settled_since_s and "
                            "measure_window_s per unit; an unsettled unit can fail but not pass",
            "terminals": "die-side nodes sw_d, vin_d, gnd_d and the power-device gates v(xtop.gh), v(xtop.gl); bond-wire L and R are in the bench (2 wires per net, spec 0.3 typical)",
            "threshold": "per-unit constant-current Vth of a 10 um replica of each power device at its drawn L, 100 nA * W/L (bench.spice), same corner",
            "corner_set": a.set},
        "units": [{k: v for k, v in u.items() if k not in ("dead_time_saved_window",)} for u in units]}
    r2 = judge(units, "r2", r2_margin, EXPECTED[a.set],
               "SW >= -0.7 V (die side, also vs the die ground) and every power-device Vgs / Vds / Vgd <= 6.0 V, peaks over the saved window, no transient credit",
               {"limits": {"sw_min_v": sm.R2_SW_MIN, "terminal_max_v": sm.R2_TERM_MAX},
                "margin": "min(sw_min + 0.7, 6.0 - max(|terminal|, sw_max)); negative = failing"})
    r14 = judge(units, "r14", r14_margin, EXPECTED[a.set],
                "dead time 1..6 ns (typ 3 ns) at |Vgs| = Vth, zero overlap (no time with both |Vgs| above Vth), buck_top, closed loop",
                {"limits": {"min_s": R14_MIN, "typ_s": R14_TYP, "max_s": R14_MAX},
                 "zero_overlap": {u["id"]: (None if not u.get("dead_time") else
                                            u["dead_time"]["overlap_s"] == 0 and u["dead_time_saved_window"]["overlap_s"] == 0) for u in units},
                 "margin": "min(dead_min - 1 ns, 6 ns - dead_max); any overlap = -overlap duration",
                 "new_versus_gate_drive_bench": "gate-drive bench (records/20261101T182827Z-*) is one typical point with a DC sink; this is the closed loop buck_top, C-%s x loads, "
                                                "with the unit's own Vth instead of the 0.5 V conservative level" % ("full" if a.set == "grid" else "typ")})
    rec2 = {**common, "row": "R2", "rows": {"R2": r2}}
    rec14 = {**common, "row": "R14", "rows": {"R14": r14}}
    rc = recordkit.write_record(os.path.join(HERE, "records", "%s-%s.json" % (ts, sha)), rec2, a.dry)
    rc |= recordkit.write_record(os.path.join(ROOT, "sim", "dead-time", "records", "%s-%s-top.json" % (ts, sha)), rec14, a.dry)
    if a.dry:
        print(json.dumps({"R2": {k: v for k, v in r2.items() if k not in ("unit_status",)},
                          "R14": {k: v for k, v in r14.items() if k not in ("unit_status", "zero_overlap")}}, indent=1))
    return rc


if __name__ == "__main__":
    sys.exit(main())
