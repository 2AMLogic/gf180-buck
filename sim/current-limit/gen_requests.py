#!/usr/bin/env python3
"""Write the klt sim requests and corner matrices of the current-limit bench (spec R16).

  request_ramp.json   C-full (45) with the load ramped 0 -> 3 A over 300 us after soft start (600 us):
                      the trip current per corner, bounds 0.70 - 2.1 A
  request_min.json    R16 min-bound case: no trip at 500 mA, L -20 %, Vin max (5.5 V), all 15
                      process x T points; oscillator bias scaled by OSC_K (see README for f)
  matrix_ramp.json, matrix_min.json   the matrices `klt corner-matrix check` diffs them against

Run: python3 -I sim/current-limit/gen_requests.py   (deterministic)
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "lib"))
import genkit  # noqa: E402
from genkit import PROCESS, TEMP, VIN  # noqa: E402
OSC_K = 1.0   # oscillator bias scale for the min-bound case; the measured f of every unit is recorded
OPTIONS = {"keep_artifacts": True, "waveforms": True, "timeout_s": 1200, "threads_per_worker": 1,
           "save_vectors": ["v(out)", "i(lind)", "v(sw_d)", "v(xtop.trip)"]}


def base(corners, tran, last):
    return genkit.request(corners, tran, [genkit.vout_last(last)], OPTIONS)


def dump(name, obj):
    genkit.dump(HERE, name, obj)


# soft start is done by 520 us at the latest; the ramp starts at t_r0 = 600 us, saved from there
ramp = {"process": PROCESS, "supply_v": {"vsrc": VIN}, "supply_waveforms": ["vsrc"], "temperature_c": TEMP,
        "params": {"i_end": [3.0], "t_ramp": [300e-6], "lfac": [1.0], "osc_k": [1.0]}}
dump("request_ramp.json", base(ramp, "2.5n 920u 600u 2.5n", 919))
dump("matrix_ramp.json", genkit.matrix(ramp))

# min bound: 500 mA reached in 1 us at 600 us and held 160 us (~320 cycles); L -20 %, Vin max
mn = {"process": PROCESS, "supply_v": {"vsrc": [5.5]}, "supply_waveforms": ["vsrc"], "temperature_c": TEMP,
      "params": {"i_end": [0.5], "t_ramp": [1e-6], "lfac": [0.8], "osc_k": [OSC_K]}}
dump("request_min.json", base(mn, "2.5n 760u 600u 2.5n", 759))
dump("matrix_min.json", genkit.matrix(mn))
