#!/usr/bin/env python3
"""Write the klt sim requests and corner matrices of the load-step bench (issue #59).

  request_tol.json    switched, C-typ (typical, 27 C, Vin 5.0) x all 18 P-T tolerance combinations
                      (L x{0.8,1,1.2}, Ceff {4.7,6,12} uF, ESR {5,10} mOhm)            = 18 units
  request_full.json   switched, C-full (5 process x 3 T x 3 Vin = 45) x the two tolerance corners that
                      bind R12 deviation (Ceff 4.7 uF, ESR 10 mOhm, L x0.8 and x1.2)    = 90 units
  request_avg.json    averaged model (design/averaged/buck_avg.spice + load step), Vin {4.5,5,5.5} x the
                      18 tolerance combinations                                          = 54 units
  matrix_*.json       the matrices `klt corner-matrix check` diffs them against

Why these tolerance corners: R12 deviation ~ dI/(2*pi*fc*Ceff) + dI*ESR, so Ceff 4.7 uF / ESR 10 mOhm is the
worst case for deviation at any L; L only moves the loop (checked at both extremes). Recovery time need not
bind at the same corner, so the full tolerance cube is run at C-typ and the binding corner is read from there.
The C-full x full-cube product (810 units) is not run; collect.py says so in the record.
Run: python3 -I sim/load-step/gen_requests.py   (deterministic)
"""
import itertools
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "lib"))
import genkit  # noqa: E402
from genkit import PROCESS, TEMP, VIN  # noqa: E402
LFAC = [0.8, 1.0, 1.2]
CEFF = [4.7e-6, 6e-6, 12e-6]
ESR = [5e-3, 10e-3]
CUBE = list(itertools.product(LFAC, CEFF, ESR))                 # 18
WORST = [(0.8, 4.7e-6, 10e-3), (1.2, 4.7e-6, 10e-3)]
# .tran: 2.5 ns = T/200 at 2 MHz; steps at 600 / 680 us (bench.spice), stop 760 us, saved from 480 us
TRAN = "2.5n 760u 480u 2.5n"
OPTIONS = {"keep_artifacts": True, "waveforms": True, "timeout_s": 1200, "threads_per_worker": 1,
           "save_vectors": ["v(out)", "i(lind)", "v(sw_d)", "v(vsrc)", "i(vsrc)"]}


def params(rows, names):
    return {n: [r[i] for r in rows] for i, n in enumerate(names)}


def switched(corners):
    return genkit.request(corners, TRAN, [genkit.vout_last(759)], OPTIONS)


def dump(name, obj):
    genkit.dump(HERE, name, obj)


NAMES = ("lfac", "c_out", "esr")
tol = {"process": [PROCESS[0]], "supply_v": {"vsrc": [5.0]}, "supply_waveforms": ["vsrc"],
       "temperature_c": [27], "params": params(CUBE, NAMES)}
dump("request_tol.json", switched(tol))
dump("matrix_tol.json", genkit.matrix(tol))

full = {"process": PROCESS, "supply_v": {"vsrc": VIN}, "supply_waveforms": ["vsrc"],
        "temperature_c": TEMP, "params": params(WORST, NAMES)}
dump("request_full.json", switched(full))
dump("matrix_full.json", genkit.matrix(full))

# averaged: klt params rows zip by index, so the Vin x tolerance cross product is expanded here
rows = list(itertools.product(VIN, LFAC, CEFF, ESR))
avg = {"params": params(rows, ("vin", "lfac", "ceff", "esr"))}
dump("request_avg.json", {
    "netlist": "avg_step.spice", "engine": "ngspice", "corners": avg,
    "analysis": {"kind": "tran", "args": TRAN},
    "measurements": [{"name": "vout_last", "spice": ".meas tran vout_last FIND v(vo) AT=759u", "unit": "V"}],
    "options": {"keep_artifacts": True, "waveforms": True, "timeout_s": 300, "save_vectors": ["v(vo)", "i(l1)"]}})
dump("matrix_avg.json", avg)
assert len(CUBE) == 18 and len(rows) == 54
