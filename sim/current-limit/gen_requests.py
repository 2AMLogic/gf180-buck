#!/usr/bin/env python3
"""Write the klt sim requests and corner matrices of the current-limit bench (spec R16).

  request_ramp.json   C-full (45) with the load ramped 0 -> 3 A over 300 us after soft start (600 us):
                      the trip current per corner, bounds 0.70 - 2.1 A
  request_min.json    R16 min-bound case: no trip at 500 mA, L -20 %, Vin max (5.5 V), all 15
                      process x T points; oscillator bias scaled by OSC_K (see README for f)
  matrix_ramp.json, matrix_min.json   the matrices `klt corner-matrix check` diffs them against

Run: python3 -I sim/current-limit/gen_requests.py   (deterministic)
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
FAMILY = {"typical": "typical", "ff": "ff", "ss": "ss", "fs": "typical", "sf": "typical"}
PROCESS = [{"name": p, "sections": [p, "mimcap_" + f, "cap_mim", "res_" + f]} for p, f in FAMILY.items()]
VIN = [4.5, 5.0, 5.5]
TEMP = [-40, 27, 125]
OSC_K = 1.0   # oscillator bias scale for the min-bound case; the measured f of every unit is recorded
OPTIONS = {"keep_artifacts": True, "waveforms": True, "timeout_s": 1200, "threads_per_worker": 1,
           "save_vectors": ["v(out)", "i(lind)", "v(sw_d)", "v(xtop.trip)"]}
BATCH = {"max_units_per_job": 1, "max_concurrent_jobs": 12}


def base(corners, tran, last):
    return {"netlist": "bench.spice", "engine": "ngspice",
            "models": {"pdk": "gf180mcuD", "lib": "libs.tech/ngspice/sm141064.ngspice"},
            "analysis": {"kind": "tran", "args": tran}, "corners": corners,
            "measurements": [{"name": "vout_last", "spice": ".meas tran vout_last FIND v(out) AT=%du" % last, "unit": "V"}],
            "batch": BATCH, "options": OPTIONS}


def dump(name, obj):
    with open(os.path.join(HERE, name), "w") as fh:
        json.dump(obj, fh, indent=1)
        fh.write("\n")


# soft start is done by 520 us at the latest; the ramp starts at t_r0 = 600 us, saved from there
ramp = {"process": PROCESS, "supply_v": {"vsrc": VIN}, "supply_waveforms": ["vsrc"], "temperature_c": TEMP,
        "params": {"i_end": [3.0], "t_ramp": [300e-6], "lfac": [1.0], "osc_k": [1.0]}}
dump("request_ramp.json", base(ramp, "2.5n 920u 600u 2.5n", 919))
dump("matrix_ramp.json", {k: ramp[k] for k in ("process", "supply_v", "temperature_c", "params")})

# min bound: 500 mA reached in 1 us at 600 us and held 160 us (~320 cycles); L -20 %, Vin max
mn = {"process": PROCESS, "supply_v": {"vsrc": [5.5]}, "supply_waveforms": ["vsrc"], "temperature_c": TEMP,
      "params": {"i_end": [0.5], "t_ramp": [1e-6], "lfac": [0.8], "osc_k": [OSC_K]}}
dump("request_min.json", base(mn, "2.5n 760u 600u 2.5n", 759))
dump("matrix_min.json", {k: mn[k] for k in ("process", "supply_v", "temperature_c", "params")})
