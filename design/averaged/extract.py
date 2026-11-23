#!/usr/bin/env python3
"""Extract crossover fc, phase margin and gain margin from the averaged-model
loop-gain sweep and write the JSON record. Standard library only.

Loop gain: the bench breaks the loop with a series voltage injection between
Vout (node vo) and the feedback input (node b), so b = vo + vinj and, with
negative feedback, vo = -T*b. T(f) = -v(vo)/v(b).

Definitions (per point):
  fc  highest-frequency downward 0 dB crossing of |T| (log-f / log-|T|
      interpolation); n_unity counts every downward crossing.
  PM  180 + unwrapped phase(T) at fc, degrees (phase interpolated in log f).
  GM  min over every -180 degree phase crossing of -20*log10|T|, dB;
      "none" when the phase never reaches -180 inside the swept band.
Phase is unwrapped from the lowest frequency sample, where T is an integrator.

Record plumbing is sim/lib/recordkit.py, the one shared copy (stdlib-only too).

A full record (points inlined) is written only for a results_sha256 not already
in --out-dir. An equal-hash re-run writes no record: it appends one provenance
row to <out-dir>/runs.jsonl (append-only), naming the record that holds the
payload. Existing records are never edited (issue #173).
"""
import argparse
import hashlib
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "sim", "lib"))
import recordkit  # noqa: E402

TARGET = {"fc_hz_min": 100e3, "fc_hz_max": 250e3, "pm_deg_min": 45.0, "gm_db_min": 10.0}
# Printed precision: the record stores these rounded values, so a re-run that
# reproduces them to this precision produces an identical record.
FC_KHZ_DIGITS, PM_DIGITS, GM_DIGITS = 3, 2, 2


def unwrap_deg(phases):
    out, prev = [], None
    for p in phases:
        if prev is None:
            cur = p
        else:
            d = (p - prev + 180.0) % 360.0 - 180.0
            cur = out[-1] + d
        out.append(cur)
        prev = p
    return out


def margins(freqs, t):
    """freqs: ascending Hz; t: complex loop gain. Returns dict of raw values."""
    mag = [abs(x) for x in t]
    ph = unwrap_deg([math.degrees(math.atan2(x.imag, x.real)) for x in t])
    fc = pm = None
    n_unity = 0
    for i in range(len(freqs) - 1):
        m0, m1 = mag[i], mag[i + 1]
        if m0 >= 1.0 > m1:
            n_unity += 1
            w = -math.log(m0) / (math.log(m1) - math.log(m0))
            fc = freqs[i] * (freqs[i + 1] / freqs[i]) ** w
            pm = 180.0 + ph[i] + (ph[i + 1] - ph[i]) * w
    gm = None
    n180 = 0
    for i in range(len(freqs) - 1):
        a, b = ph[i] + 180.0, ph[i + 1] + 180.0
        if a == 0.0 or a * b < 0.0:
            n180 += 1
            w = 0.0 if a == 0.0 else a / (a - b)
            m = math.exp(math.log(mag[i]) * (1 - w) + math.log(mag[i + 1]) * w)
            g = -20.0 * math.log10(m)
            gm = g if gm is None else min(gm, g)
    return {"fc_hz": fc, "pm_deg": pm, "gm_db": gm, "n_unity": n_unity, "n_180": n180}


def grade(m):
    """Printed-precision point result with per-bound pass/fail."""
    fc_khz = None if m["fc_hz"] is None else round(m["fc_hz"] / 1e3, FC_KHZ_DIGITS)
    pm = None if m["pm_deg"] is None else round(m["pm_deg"], PM_DIGITS)
    gm = "none" if m["gm_db"] is None else round(m["gm_db"], GM_DIGITS)
    checks = {
        "fc": fc_khz is not None
        and TARGET["fc_hz_min"] / 1e3 <= fc_khz <= TARGET["fc_hz_max"] / 1e3,
        "pm": pm is not None and pm >= TARGET["pm_deg_min"],
        "gm": gm == "none" or gm >= TARGET["gm_db_min"],
    }
    return {
        "fc_khz": fc_khz, "pm_deg": pm, "gm_db": gm,
        "n_unity_crossings": m["n_unity"], "n_180_crossings": m["n_180"],
        "pass": {**checks, "all": all(checks.values())},
    }


def load_point(sidecar):
    with open(sidecar) as fh:
        d = json.load(fh)
    vo, b = d["data"]["v(vo)"], d["data"]["v(b)"]
    t = []
    for k in range(len(d["frequency_hz"])):
        a = complex(vo["real"][k], vo["imag"][k])
        c = complex(b["real"][k], b["imag"][k])
        t.append(-a / c)
    return d["frequency_hz"], t


AXES = ("vin", "lfac", "ceff", "esr", "iload")


def build_record(report, request_path):
    env = report.get("environment", {})
    points, problems = [], []
    for c in report["corners"]:
        p = c.get("params") or {}
        sidecar = (c.get("artifacts") or {}).get("complex_vectors")
        if c.get("status") == "error" or not sidecar or not os.path.exists(sidecar):
            problems.append(c.get("corner_id"))
            continue
        freqs, t = load_point(sidecar)
        res = grade(margins(freqs, t))
        res["params"] = {k: p[k] for k in AXES}
        res["lf_t0_db"] = round(20 * math.log10(abs(t[0])), 1)
        points.append(res)
    points.sort(key=lambda r: tuple(r["params"][k] for k in AXES))
    sha = hashlib.sha256(json.dumps(points, sort_keys=True).encode()).hexdigest()
    failing = [x for x in points if not x["pass"]["all"]]
    return {
        "schema": 1,
        "kind": "averaged-loop-gain-sweep (simulated, not measured)",
        "target": TARGET,
        "bounds_note": "pass/fail per point: fc in [100,250] kHz, PM >= 45 deg, GM >= 10 dB (GM 'none' = no -180 crossing in band)",
        "ngspice": env.get("engine_version"),
        "ngspice_banner": (env.get("engine_build") or {}).get("version_banner", "").splitlines()[1:2],
        "deck_sha256": env.get("netlist_sha256"),
        "request_sha256": recordkit.sha256(request_path),
        "precision": {"fc": "kHz, %d decimals" % FC_KHZ_DIGITS, "pm": "deg, %d decimals" % PM_DIGITS, "gm": "dB, %d decimals" % GM_DIGITS},
        "point_count": len(points),
        "expected_point_count": len(report["corners"]),
        "errored_corners": problems,
        "summary": {
            "pass_all": len(points) - len(failing),
            "fail_any": len(failing),
            "fail_fc": sum(not x["pass"]["fc"] for x in points),
            "fail_pm": sum(not x["pass"]["pm"] for x in points),
            "fail_gm": sum(not x["pass"]["gm"] for x in points),
            "fc_khz_min": min((x["fc_khz"] for x in points if x["fc_khz"] is not None), default=None),
            "fc_khz_max": max((x["fc_khz"] for x in points if x["fc_khz"] is not None), default=None),
            "pm_deg_min": min((x["pm_deg"] for x in points if x["pm_deg"] is not None), default=None),
            "gm_db_min": min((x["gm_db"] for x in points if x["gm_db"] != "none"), default=None),
        },
        "results_sha256": sha,
        "points": points,
    }


RUNS_LOG = "runs.jsonl"


def find_record_for_hash(out_dir, sha):
    """Name of the first record in out_dir carrying results_sha256 == sha, else None.
    Reads the key only; runs.jsonl is not a record (it does not end in .json)."""
    if not os.path.isdir(out_dir):
        return None
    for name in sorted(os.listdir(out_dir)):
        if not name.endswith(".json"):
            continue
        with open(os.path.join(out_dir, name)) as fh:
            if json.load(fh).get("results_sha256") == sha:
                return name
    return None


def run_row(rec, record_name):
    env, remote = rec["environment"], rec["environment"].get("remote") or {}
    return {
        "generated_utc": rec["generated_utc"],
        "results_sha256": rec["results_sha256"],
        "record": record_name,
        "ngspice": rec["ngspice"],
        "remote": {k: remote.get(k) for k in ("job_id", "client_klt_version", "runner_klt_version")},
        "environment": {k: env.get(k) for k in ("repo_commit", "files_sha256")},
    }


def append_run(out_dir, row):
    """Append one sorted-key JSON line to runs.jsonl. A malformed existing line is a
    hard error (ValueError): the log is evidence, so it is never skipped or rewritten."""
    path = os.path.join(out_dir, RUNS_LOG)
    if os.path.exists(path):
        with open(path) as fh:
            for n, line in enumerate(fh, 1):
                try:
                    if not isinstance(json.loads(line), dict):
                        raise ValueError("not an object")
                except ValueError as e:
                    raise ValueError("%s:%d is malformed (%s); refusing to append" % (path, n, e))
    os.makedirs(out_dir, exist_ok=True)
    with open(path, "a") as fh:
        fh.write(json.dumps(row, sort_keys=True) + "\n")
    return path


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--report", required=True, help="klt sim --report-out JSON")
    ap.add_argument("--request", required=True, help="the klt sim request that produced it")
    ap.add_argument("--out-dir", required=True, help="records directory (append-only)")
    ap.add_argument("--tag", default="", help="suffix for the record file name")
    ap.add_argument("--fail-on-violation", action="store_true", help="exit 3 when any point misses a bound")
    a = ap.parse_args(argv)
    with open(a.report) as fh:
        report = json.load(fh)
    rec = build_record(report, a.request)
    if rec["errored_corners"] or not rec["point_count"]:
        print("extract.py: %d corner(s) produced no loop gain: %s" % (len(rec["errored_corners"]), rec["errored_corners"][:3]), file=sys.stderr)
        return 1
    ts, _, hdr = recordkit.header(HERE)
    rec["environment"] = {
        **hdr,
        **recordkit.report_env(report, a.report),
        "files_sha256": recordkit.files_sha256(
            HERE, ("buck_avg.spice", "sweep_request.json", "extract.py", "gen_request.py"),
            lib_files=("genkit.py",)),
    }
    rec["generated_utc"] = ts
    try:
        existing = find_record_for_hash(a.out_dir, rec["results_sha256"])
        if existing:
            print("extract.py: results_sha256 %s already recorded in %s; no new record" % (
                rec["results_sha256"][:16], existing))
            print("extract.py: run row appended to %s" % append_run(a.out_dir, run_row(rec, existing)))
    except ValueError as e:
        print("extract.py: %s" % e, file=sys.stderr)
        return 1
    if not existing:
        path = os.path.join(a.out_dir, "%s-%s%s.json" % (ts, rec["results_sha256"][:12], a.tag))
        rc = recordkit.write_record(path, rec, tool="extract.py")
        if rc:
            return rc
    s = rec["summary"]
    print("points %d  pass %d  fail %d (fc %d, pm %d, gm %d)  results_sha256 %s" % (
        rec["point_count"], s["pass_all"], s["fail_any"], s["fail_fc"], s["fail_pm"], s["fail_gm"], rec["results_sha256"][:16]))
    print("fc %s..%s kHz  PM min %s deg  GM min %s dB" % (s["fc_khz_min"], s["fc_khz_max"], s["pm_deg_min"], s["gm_db_min"]))
    return 3 if (a.fail_on_violation and s["fail_any"]) else 0


if __name__ == "__main__":
    sys.exit(main())
