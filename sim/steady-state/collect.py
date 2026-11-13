#!/usr/bin/env python3
"""Grade a finished steady-state bench and write one append-only record.

  python3 -I sim/steady-state/collect.py --report GRID.json --report R8.json [--dry]

Reads the klt sim report(s) (grid + R8), grades every unit's waveform.raw with
sim/lib/rawgrade.py (-> buckmeas, spec 0.4), then judges each spec row against the
target-tier bounds below and writes sim/steady-state/records/<UTC>-<sha>.json.
A unit that timed out, errored or did not settle contributes NO value; a row with any
such unit is `not_demonstrated` (or `fail` if a valued unit is out of bounds). Nothing
is relaxed to make a row pass. Simulated, never measured.
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
from recordkit import parse_id as _parse_id  # noqa: E402

# Target-tier bounds (spec/target-spec.md section 1)
R4 = (1.728, 1.872)          # V   mean Vout
R7 = (1.7e6, 2.3e6)          # Hz
R8 = (0.119, 0.270)          # A p-p
R9_MIN = 0.85                # peak efficiency, C-typ, pre-layout
R11_MAX = 0.018              # V p-p after the 20 MHz low-pass
R6_MAX_GAP = 1.5             # longest period / median period: above it a pulse was skipped


def parse_id(cid):
    return _parse_id(cid, lfac_default=1.0)


def unit_record(corner, bench):
    key = parse_id(corner["corner_id"])
    u = {"id": corner["corner_id"], **key, "bench": bench, "klt_status": corner.get("status"),
         "klt_diagnostics": [d.get("code") for d in corner.get("diagnostics") or []]}
    raw, reason = recordkit.waveform_or_reason(corner)
    if reason:
        u.update(graded=False, settled=False, reason=reason)
        return u
    g = rawgrade.grade(raw, key["vin_v"], key["iload_a"], buckmeas.STEP_MAX_S)
    u["graded"] = g["graded"]
    if not g["graded"]:
        u.update(settled=False, reason=g["reason"])
        return u
    st = g["settle"]
    u.update(settled=st["settled"], clock_hz=g["clock"]["f_hz"], step_max_ok=g["run"]["step_ok"],
             window_s=st["measure_window_s"], settled_since_s=st["settled_since_s"],
             mean_delta_rel=st["mean_vout_delta_rel"], ipk_delta_rel=st["ipk_delta_rel"],
             pwm=g["pwm_regularity"])
    if st["settled"]:
        u.update(vout_v=g["R4_vout_mean"]["mean_v"], il_pp_a=g["R8_il_pp"]["pp_a"],
                 ripple_v=g["R11_ripple"]["pp_v"], eta=g["R9_R10_efficiency"]["eta"],
                 f_sw_hz=g["R7_f_sw"]["hz"], f_sw_cycles=g["R7_f_sw"]["cycles"],
                 f_sw_reason=g["R7_f_sw"].get("reason"))
    else:
        u["reason"] = st.get("reason")
    return u


def brief(u, field):
    return {"id": u["id"], field: u.get(field)}


def judge_row(units, field, lo, hi, what, binding="worst"):
    """Generic [lo, hi] row over `units`. Binding = valued unit farthest outside (or closest to) the band."""
    valued = [u for u in units if u.get(field) is not None]
    novalue = [u["id"] for u in units if u.get(field) is None]
    out_of = [u for u in valued if (lo is not None and u[field] < lo) or (hi is not None and u[field] > hi)]

    def margin(u):  # >0 inside, <0 outside; smallest = binding
        m = []
        if lo is not None:
            m.append(u[field] - lo)
        if hi is not None:
            m.append(hi - u[field])
        return min(m) if m else 0.0
    worst = min(valued, key=margin) if valued else None
    verdict = "fail" if out_of else ("not_demonstrated" if novalue or not valued else "pass")
    return {"what": what, "bounds": [lo, hi], "n_units": len(units), "n_valued": len(valued),
            "n_out_of_bounds": len(out_of), "n_no_value": len(novalue), "verdict": verdict,
            "binding": None if worst is None else {"id": worst["id"], "value": worst[field], "margin": margin(worst)},
            "min": None if not valued else min(u[field] for u in valued),
            "max": None if not valued else max(u[field] for u in valued),
            "no_value_units": novalue}


def judge(grid, r8):
    rows = {}
    rows["R4"] = judge_row(grid, "vout_v", R4[0], R4[1], "mean Vout, C-full x load {0, 50, 250, 500 mA}, untrimmed")
    # R6: forced PWM at 0 and 50 mA over C-full
    r6u = [u for u in grid if u["iload_a"] in (0.0, 0.05)]
    for u in r6u:
        reg = u.get("pwm")
        u["r6_ok"] = None if reg is None else (reg["max_over_median"] <= R6_MAX_GAP and (u["iload_a"] > 0 or reg["il_min_a"] < 0))
    bad6 = [u["id"] for u in r6u if u["r6_ok"] is False]
    nov6 = [u["id"] for u in r6u if u["r6_ok"] is None]
    worst6 = max((u for u in r6u if u.get("pwm")), key=lambda u: u["pwm"]["max_over_median"], default=None)
    rows["R6"] = {"what": "forced PWM at 0 and 50 mA, C-full: a rising SW edge every period (longest period / median <= %.1f), "
                          "inductor current negative at 0 load, switching continues to the end of the run" % R6_MAX_GAP,
                  "n_units": len(r6u), "n_with_waveform": len(r6u) - len(nov6), "n_failing": len(bad6), "n_no_value": len(nov6),
                  "verdict": "fail" if bad6 else ("not_demonstrated" if nov6 or not r6u else "pass"),
                  "binding": None if worst6 is None else {"id": worst6["id"], "max_over_median": worst6["pwm"]["max_over_median"],
                                                         "il_min_a": worst6["pwm"]["il_min_a"]},
                  "failing_units": bad6, "no_value_units": nov6,
                  "not_observed": "the OCP trip net is not saved: 'does not trip' is inferred from uninterrupted switching only"}
    rows["R7"] = judge_row(grid, "f_sw_hz", R7[0], R7[1], "switching frequency over >= 100 settled cycles, C-full x all loads")
    obs = [u["clock_hz"] for u in grid if u.get("clock_hz") is not None and u.get("f_sw_hz") is None]
    if obs:  # diagnostic only: NOT an R7 value (the run did not settle, so spec 0.4 grants none)
        rows["R7"]["unsettled_clock_observation_hz"] = {
            "n": len(obs), "min": min(obs), "max": max(obs),
            "note": "mean period of V(sw) rising edges over the saved tail of runs that did NOT settle; not a graded value"}
    rows["R8"] = judge_row(r8, "il_pp_a", R8[0], R8[1], "inductor ripple p-p, the three Vin / L combinations of R8 (typical, 27 C, 250 mA)")
    for u in r8:
        if u.get("vout_v") and u.get("f_sw_hz"):
            L = 3.3e-6 * u["lfac"]
            u["il_pp_arith_a"] = u["vout_v"] * (1 - u["vout_v"] / u["vin_v"]) / (L * u["f_sw_hz"])
    ctyp = [u for u in grid if u["process"] == "typical" and u["temp_c"] == 27 and u["vin_v"] == 5.0 and u["iload_a"] > 0]
    rows["R9"] = judge_row(ctyp, "eta", R9_MIN, None, "PRE-LAYOUT peak efficiency, C-typ, best of loads {50, 250, 500 mA} "
                                                    "(100 mA not run); graded value is post-layout (#27)")
    valued9 = [u for u in ctyp if u.get("eta") is not None]
    if valued9:
        best = max(valued9, key=lambda u: u["eta"])
        rows["R9"]["peak"] = {"id": best["id"], "eta": best["eta"]}
        rows["R9"]["verdict"] = "pass" if best["eta"] >= R9_MIN and len(valued9) == len(ctyp) else (
            "fail" if best["eta"] < R9_MIN else "not_demonstrated")
        rows["R9"]["binding"] = rows["R9"]["peak"]
    u500 = [u for u in grid if u["iload_a"] == 0.5]
    rows["R10"] = judge_row(u500, "eta", None, None, "PRE-LAYOUT efficiency at 500 mA, C-full (report only: no floor is ratified)")
    rows["R10"]["verdict"] = "reported" if rows["R10"]["n_valued"] and not rows["R10"]["n_no_value"] else "not_demonstrated"
    valued10 = [u for u in u500 if u.get("eta") is not None]
    if valued10:
        lo10 = min(valued10, key=lambda u: u["eta"])
        rows["R10"]["binding"] = {"id": lo10["id"], "value": lo10["eta"], "kind": "lowest efficiency"}
    u11 = [u for u in grid if u["iload_a"] in (0.05, 0.5)]
    rows["R11"] = judge_row(u11, "ripple_v", None, R11_MAX, "Vout ripple p-p after 20 MHz 1st-order LP, C-full x load {50, 500 mA}")
    rows["R11"]["spec_expects_binding_at"] = "Vin max, hot, ss"
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--report", action="append", required=True, help="klt sim report JSON (grid, then r8)")
    ap.add_argument("--dry", action="store_true", help="print, do not write a record")
    a = ap.parse_args(argv)
    units, envs = [], []
    for path in a.report:
        rep = json.load(open(path))
        bench = "r8" if "lfac" in json.dumps([c["corner_id"] for c in rep["corners"]][:1]) else "grid"
        envs.append(recordkit.report_env(rep, path, jobs=True))
        for c in rep["corners"]:
            units.append(unit_record(c, bench))
    grid = [u for u in units if u["bench"] == "grid"]
    r8 = [u for u in units if u["bench"] == "r8"]
    rows = judge(grid, r8)
    ts, sha, env = recordkit.header(HERE)
    rec = {
        "record": "simulated, not measured; pre-layout; R9/R10 are not the graded (post-layout) value",
        "environment": {**env, "local_grader_python": sys.version.split()[0], "reports": envs,
                        "files_sha256": recordkit.files_sha256(
                            HERE, ("bench.spice", "opamp_two_stage.spice", "request_grid.json", "request_r8.json", "gen_requests.py"),
                            ("design/netlists/buck_top.spice",), ("bench_harness.spice", "buckmeas.py", "rawgrade.py"))},
        "method": {"analysis": ".tran 2.5n 600u, waveforms saved from 480u (a 120 us tail); max step 2.5 ns = T/200 at 2 MHz",
                   "startup": "Vin ramps 0 -> Vin over 10 us, control rails/bias over 5 us, EN at 20 us (soft start ~200 us), load applied 0 -> I at 260 us over 0.5 us",
                   "steady_state": "spec 0.4: two consecutive 20-cycle windows < 0.1 % in mean Vout and < 1 % in peak I(L), at the measured cycle period, "
                                   "stepped back from the last whole cycle; the record gives the window and when the chain of passing windows starts",
                   "settling_window_start": "per unit: units[].settled_since_s; measurement window units[].window_s",
                   "clock": "cycle period and phase from rising crossings of Vin/2 on V(sw) over the saved tail (free-running oscillator)",
                   "corner_counts": {"grid": len(grid), "grid_per_load": len(grid) // 4 if grid else 0, "r8": len(r8)}},
        "rows": rows, "units": units}
    if a.dry:
        print(json.dumps({k: {kk: vv for kk, vv in v.items() if kk not in ("no_value_units", "failing_units")} for k, v in rows.items()}, indent=1))
        return 0
    return recordkit.write_record(os.path.join(HERE, "records", "%s-%s.json" % (ts, sha)), rec)


if __name__ == "__main__":
    sys.exit(main())
