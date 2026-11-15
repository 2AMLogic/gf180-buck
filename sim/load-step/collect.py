#!/usr/bin/env python3
"""Grade a finished load-step bench and write one append-only record.

  python3 -I sim/load-step/collect.py --tol TOL.json --full FULL.json --avg AVG.json [--dry]

Reads the klt sim reports of the three requests (gen_requests.py), grades every switched
unit's waveform.raw with sim/lib/buckmeas.py (load_step_pair, spec 0.4: each step only after
the settled test passes), judges R12 against the target-tier bounds, reports R13(b) per
tolerance corner, and cross-checks R13(c): switched peak deviation and recovery time against
the same load step on the averaged model (design/averaged/buck_avg.spice, unchanged), +-30 %.
A unit that timed out, errored or did not settle before a step carries NO value for that step;
nothing is relaxed. Simulated, never measured. Writes sim/load-step/records/<UTC>-<sha>.json.
"""
import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "lib"))
import buckmeas  # noqa: E402
import rawgrade  # noqa: E402
import recordkit  # noqa: E402

# Target-tier R12 bounds (spec/target-spec.md section 1)
DEV_MAX = 0.090        # V   deviation, larger of under/overshoot
BAND = 0.018           # V   recovery band, 1 % of 1.8 V
REC_MAX = 25e-6        # s   recovery time to the last exit from the band
XTOL = 0.30            # R13(c)
F_AVG = 2.0e6          # Hz  averaged model has no clock; cycle counts use the commanded 2 MHz
EXPECTED = {"tol": 18, "full": 90, "avg": 54}   # C-full = 45 x 2 tolerance corners = 90


def bench_timing():
    txt = open(os.path.join(HERE, "bench.spice")).read()
    line = re.search(r"^\.param i_lo=.*$", txt, re.M).group(0)
    kv = dict(re.findall(r"(\w+)=([0-9.eE+-]+u?)", line))

    def val(x):
        return float(x[:-1]) * 1e-6 if x.endswith("u") else float(x)
    return {k: val(v) for k, v in kv.items()}


def parse_id(cid):
    """Corner id -> process, vin_v, temp_c, lfac, ceff_f, esr_ohm. The averaged bench has no supply
    source, so its id carries a non-numeric supply segment ("novdd") and Vin comes from the `vin` param."""
    proc, vin_seg, rest = cid.split("/", 2)
    if not re.fullmatch(r"[0-9.]+V", vin_seg):
        vin_seg = "0V"
    key, params = recordkit.parse_corner("/".join((proc, vin_seg, rest)))
    return {"process": key["process"], "vin_v": params.get("vin", key["vin_v"]), "temp_c": key["temp_c"],
            "lfac": params["lfac"], "ceff_f": params.get("c_out", params.get("ceff")), "esr_ohm": params["esr"]}


def tol_key(u):
    return "L x%g, Ceff %g uF, ESR %g mohm" % (u["lfac"], u["ceff_f"] * 1e6, u["esr_ohm"] * 1e3)


def grade_unit(corner, bench, tm):
    key = parse_id(corner["corner_id"])
    u = {"id": corner["corner_id"], "bench": bench, **key, "klt_status": corner.get("status"),
         "klt_diagnostics": [d.get("code") for d in corner.get("diagnostics") or []]}
    raw, reason = recordkit.waveform_or_reason(corner)
    if reason:
        u.update(graded=False, reason=reason)
        return u
    avg = bench == "avg"
    need = ("time", "v(vo)", "i(l1)") if avg else rawgrade.NEEDED
    c = rawgrade.read_ascii_raw(raw, need)
    t = c["time"]
    if avg:
        vout, il, f_sw, t_clk0 = c["v(vo)"], c["i(l1)"], F_AVG, 0.0
        u["clock"] = {"source": "commanded %g Hz (the averaged model has no clock)" % F_AVG}
    else:
        clk = rawgrade.clock_from_crossings(rawgrade.sw_rising_crossings(t, c["v(sw_d)"], key["vin_v"]))
        if clk["f_hz"] is None:
            u.update(graded=False, reason=clk["reason"])
            return u
        f_sw, t_clk0, vout, il = clk["f_hz"], clk["t_clk0_s"], c["v(out)"], c["i(lind)"]
        u["clock"] = {"source": "rising crossings of Vin/2 on V(sw) over the saved tail", "f_hz": f_sw, "crossings": clk["crossings"]}
    max_dt, run_step_ok = buckmeas.step_check(t)   # the run's §0.4 step, not the per-step step_ok() below
    u["run"] = {"t_first_s": t[0], "t_last_s": t[-1], "step_max_observed_s": max_dt, "step_ok": run_step_ok}
    if not run_step_ok:
        # Spec 0.4 gates every graded row (spec/decision-records/0009-max-step-gates-graded-rows.md):
        # neither edge of this run carries a value, so the unit gains no `up`/`back` and keeps `run`.
        u.update(graded=False, reason=buckmeas.step_reason(max_dt))
        return u
    pair = buckmeas.load_step_pair(t, vout, il, f_sw, tm["t_up"], tm["t_dn"], BAND, t_clk0=t_clk0)
    u["graded"] = True
    for name, r in pair.items():
        s = r["settle_before_step"]
        u[name] = {"settled": s["settled"], "settle_measure_window_s": s["measure_window_s"],
                   "settled_since_s": s["settled_since_s"], "available": r["available"]}
        if r["available"]:
            u[name].update({k: r[k] for k in ("t_step_s", "t_end_s", "cycles_after_step", "v_ref_v", "v_pre_step_mean_v",
                                              "undershoot_v", "overshoot_v", "deviation_v", "recovered",
                                              "recovery_time_s", "run_long_enough")})
        else:
            u[name]["reason"] = r.get("reason")
    return u


def step_ok(r):
    """Per-step R12 verdict: True/False, or None when the step carries no value."""
    if not r or not r.get("available"):
        return None
    return bool(r["recovered"] and r["run_long_enough"] and r["deviation_v"] <= DEV_MAX and r["recovery_time_s"] <= REC_MAX)


def judge_r12(units):
    rows, novalue, failing = [], [], []
    for u in units:
        for name in ("up", "back"):
            r = u.get(name)
            ok = step_ok(r)
            if ok is None:
                novalue.append("%s [%s]" % (u["id"], name))
            elif not ok:
                failing.append("%s [%s]" % (u["id"], name))
            if r and r.get("available"):
                rows.append((u, name, r))
    verdict = "fail" if failing else ("not_demonstrated" if novalue or not rows else "pass")
    bind_dev = max(rows, key=lambda x: x[2]["deviation_v"], default=None)
    bind_rec = max(rows, key=lambda x: x[2]["recovery_time_s"] if x[2]["recovery_time_s"] is not None else float("inf"), default=None)
    def b(x, f):
        return None if x is None else {"id": x[0]["id"], "step": x[1], "value": x[2][f]}
    return {"what": "load-step transient 50 -> 450 -> 50 mA at 1 A/us, switched: deviation <= %g V and recovery to +-%g V within %g s, "
                    "each step graded only after the 0.4 settled test; >= 100 cycles after each step" % (DEV_MAX, BAND, REC_MAX),
            "bounds": {"deviation_v_max": DEV_MAX, "band_v": BAND, "recovery_s_max": REC_MAX},
            "n_units": len(units), "n_steps_valued": len(rows), "n_steps_failing": len(failing), "n_steps_no_value": len(novalue),
            "verdict": verdict, "binding_deviation": b(bind_dev, "deviation_v"), "binding_recovery": b(bind_rec, "recovery_time_s"),
            "failing_steps": failing, "no_value_steps": novalue}


def r13b_table(units):
    out = {}
    for u in units:
        k = tol_key(u)
        steps = [step_ok(u.get("up")), step_ok(u.get("back"))]
        e = out.setdefault(k, {"n_steps": 0, "pass": 0, "fail": 0, "no_value": 0})
        for s in steps:
            e["n_steps"] += 1
            e["pass" if s else ("no_value" if s is None else "fail")] += 1
    for e in out.values():
        e["verdict"] = "fail" if e["fail"] else ("not_demonstrated" if e["no_value"] else "pass")
    return out


def step_withheld_ids(units):
    """Ids of units withheld from a graded table for a §0.4 step violation (decision record 0009)."""
    return [u["id"] for u in units if (u.get("run") or {}).get("step_ok") is False]


def r13c(sw_units, avg_units):
    """R13(c) over every switched and averaged unit. Ungraded units are excluded from the table as
    before, but one withheld for a §0.4 step violation is counted (decision record 0009): without
    that count the row could still read `pass` on a silently smaller set."""
    withheld = step_withheld_ids(sw_units) + step_withheld_ids(avg_units)
    sw_units = [u for u in sw_units if u.get("graded")]
    avg_units = [u for u in avg_units if u.get("graded")]
    amap = {(u["vin_v"], u["lfac"], u["ceff_f"], u["esr_ohm"]): u for u in avg_units}
    table = []
    for u in sw_units:
        a = amap.get((u["vin_v"], u["lfac"], u["ceff_f"], u["esr_ohm"]))
        e = {"switched_id": u["id"], "averaged_id": a["id"] if a else None, "tolerance_corner": tol_key(u), "vin_v": u["vin_v"], "checks": {}}
        for step in ("up", "back"):
            for f in ("deviation_v", "recovery_time_s"):
                sv = (u.get(step) or {}).get(f) if (u.get(step) or {}).get("available") else None
                av = (a.get(step) or {}).get(f) if a and (a.get(step) or {}).get("available") else None
                if f == "recovery_time_s" and ((u.get(step) or {}).get("recovered") is False or ((a or {}).get(step) or {}).get("recovered") is False):
                    sv = av = None  # a run that never recovers has no recovery time to compare
                e["checks"]["%s.%s" % (step, f)] = buckmeas.crosscheck(sv, av, XTOL)
        vs = [c["verdict"] for c in e["checks"].values()]
        e["verdict"] = "fail" if "fail" in vs else ("no_value" if "no_value" in vs else "pass")
        table.append(e)
    n = {v: sum(1 for e in table if e["verdict"] == v) for v in ("pass", "fail", "no_value")}
    errs = [(abs(c["rel_err"]), e["switched_id"], k, c) for e in table for k, c in e["checks"].items() if c["rel_err"] is not None]
    worst = max(errs, key=lambda x: x[0], default=None)
    return {"what": "R13(c): switched step vs averaged-model step, peak deviation and recovery time of both edges, +-%d %%" % (XTOL * 100),
            "n_units": len(table), **{"n_" + k: v for k, v in n.items()},
            "n_withheld_step_violation": len(withheld), "withheld_step_violation_units": withheld,
            "withheld_note": "a unit whose largest saved step exceeds the spec 0.4 limit is withheld from this table and counted here, "
                             "so the row cannot read `pass` on a smaller set (decision record 0009). Units withheld for no waveform or "
                             "an unlocked clock are not counted: that pre-existing drop is unchanged here",
            "verdict": "fail" if n["fail"] else ("not_demonstrated" if n["no_value"] or withheld or not table else "pass"),
            "worst": None if worst is None else {"id": worst[1], "check": worst[2], "rel_err": worst[3]["rel_err"],
                                                 "switched": worst[3]["switched"], "predicted": worst[3]["predicted"]},
            "table": table}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    for k in ("tol", "full", "avg"):
        ap.add_argument("--" + k, required=True, help="klt sim report JSON of request_%s.json" % k)
    ap.add_argument("--dry", action="store_true", help="print, do not write a record")
    a = ap.parse_args(argv)
    tm = bench_timing()
    units, envs = {"tol": [], "full": [], "avg": []}, []
    for k in ("tol", "full", "avg"):
        rep = json.load(open(getattr(a, k)))
        envs.append({"request": "request_%s.json" % k, **recordkit.report_env(rep, getattr(a, k))})
        for c in rep["corners"]:
            units[k].append(grade_unit(c, "avg" if k == "avg" else k, tm))
    counts = {k: len(v) for k, v in units.items()}
    seen, sw = set(), []
    for u in units["tol"] + units["full"]:   # one unit per corner id: the worst tolerance corner at C-typ is in both requests
        if u["id"] not in seen:
            seen.add(u["id"])
            sw.append(u)
    rows = {"R12": judge_r12(sw), "R13b": {"what": "R13(b): the switched step per P-T tolerance corner (same grading as R12)",
                                           "per_tolerance_corner": r13b_table(sw)},
            "R13c": r13c(sw, units["avg"])}
    rows["R13b"]["verdict"] = ("fail" if any(e["verdict"] == "fail" for e in rows["R13b"]["per_tolerance_corner"].values())
                               else "not_demonstrated" if any(e["verdict"] != "pass" for e in rows["R13b"]["per_tolerance_corner"].values()) else "pass")
    ts, sha, hdr = recordkit.header(HERE)
    files = recordkit.files_sha256(
        HERE, ("bench.spice", "avg_step.spice", "request_tol.json", "request_full.json", "request_avg.json", "gen_requests.py"),
        root_files=("design/netlists/buck_top.spice", "design/averaged/buck_avg.spice", "sim/steady-state/opamp_two_stage.spice"),
        lib_files=("bench_harness.spice", "buckmeas.py", "rawgrade.py"))
    rec = {
        "record": "simulated, not measured; pre-layout; target tier (5 V -> 1.8 V, 50 -> 450 -> 50 mA); rows R12, R13(b), R13(c)",
        "environment": {**hdr,
                        "local_grader_python": sys.version.split()[0], "reports": envs, "files_sha256": files},
        "method": {
            "analysis": ".tran 2.5n 760u, waveforms saved from 480u; max step 2.5 ns = T/200 at 2 MHz",
            "startup": "Vin ramps 0 -> Vin over 10 us, rails/bias over 5 us, EN at 20 us (soft start ~200 us), load 0 -> 50 mA at 260 us",
            "load_step": {"t_up_s": tm["t_up"], "t_dn_s": tm["t_dn"], "i_lo_a": tm["i_lo"], "i_hi_a": tm["i_hi"], "edge_s": tm["t_edge"],
                          "slew": "1 A/us", "hold_after_up_s": tm["t_dn"] - tm["t_up"], "hold_after_back_s": 760e-6 - tm["t_dn"],
                          "cycles_after_each_step": "~%d at 2 MHz (spec 0.4 needs >= 100 or 20 in-band cycles, whichever is longer)" % round((tm["t_dn"] - tm["t_up"]) * 2e6)},
            "steady_state": "spec 0.4 settled test (two consecutive 20-cycle windows, < 0.1 % mean Vout, < 1 % peak I(L)) on the cycles just "
                            "before each edge; a step that fails it reports no value (units[].up / .back .settled)",
            "measurement": "deviation = larger of under/overshoot about the Vout the run settles to after the step (mean of the last 20 whole "
                           "cycles of the hold), on Vout after the 20 MHz first-order low-pass (as R11); recovery = last exit from +-18 mV, "
                           "from the start of the load edge",
            "clock": "switched: cycle period/phase from rising crossings of Vin/2 on V(sw) over the saved tail; averaged: commanded 2 MHz",
            "averaged_prediction": "design/averaged/records/ hold loop-gain metrics only (fc, PM, GM); no deviation/recovery prediction exists "
                                   "there. It is derived here by a transient run of design/averaged/buck_avg.spice, unchanged, with the same "
                                   "0.4 A step pair added at the output (avg_step.spice); the averaged model has no process/T axes",
            "tolerance_coverage": "C-typ (typical, 27 C, 5.0 V) x all 18 tolerance combinations (request_tol); C-full (45) x the two corners with "
                                  "Ceff 4.7 uF, ESR 10 mohm and L x0.8 / x1.2 (request_full). C-full x the full 18-combination cube (810 units) "
                                  "was NOT run; deviation ~ dI/(2 pi fc Ceff) + dI ESR is worst at 4.7 uF / 10 mohm for any L, but this is "
                                  "an argument, not a run, for the other process/T/Vin corners",
            "corner_counts": {**counts, "expected": EXPECTED, "c_full": 45, "switched_unique": len(sw)}},
        "rows": rows, "units": {k: v for k, v in units.items()}}
    if a.dry:
        brief = {k: {kk: vv for kk, vv in v.items() if kk not in ("table", "failing_steps", "no_value_steps")} for k, v in rows.items()}
        print(json.dumps(brief, indent=1))
        return 0
    return recordkit.write_record(os.path.join(HERE, "records", "%s-%s.json" % (ts, sha)), rec)


if __name__ == "__main__":
    sys.exit(main())
