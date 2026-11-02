#!/usr/bin/env python3
"""Write the klt sim request and corner matrix of the soft-start bench (spec R15, R6 clause).

  request_grid.json   C-full (5 process x 3 T x 3 Vin = 45) x load {none, 3.6 ohm} = 90 units
  matrix_grid.json    the matrix `klt corner-matrix check` diffs it against

Process bundles as in sim/steady-state/gen_requests.py (spec 0.1).
Run: python3 -I sim/soft-start/gen_requests.py   (deterministic)
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "lib"))
import genkit  # noqa: E402
from genkit import PROCESS, TEMP, VIN  # noqa: E402
RLOAD = [1e9, 3.6]                  # ohm: 1e9 = no load; 3.6 = 500 mA at 1.8 V
# EN rises at 20 us; R15 allows up to 500 us, so the ramp is done by 520 us. .tran 2.5n (= T/200 at
# 2 MHz) to 700 us (180 us of regulation after the latest start), saved from EN.
TRAN = "2.5n 700u 20u 2.5n"
OPTIONS = {"keep_artifacts": True, "waveforms": True, "timeout_s": 900, "threads_per_worker": 1,
           "save_vectors": ["v(out)", "i(lind)", "v(sw_d)", "v(xtop.trip)"]}

grid = {"process": PROCESS, "supply_v": {"vsrc": VIN}, "supply_waveforms": ["vsrc"],
        "temperature_c": TEMP, "params": {"rload": RLOAD}}
genkit.dump(HERE, "request_grid.json", genkit.request(grid, TRAN, [genkit.vout_last(699)], OPTIONS))
genkit.dump(HERE, "matrix_grid.json", genkit.matrix(grid))
