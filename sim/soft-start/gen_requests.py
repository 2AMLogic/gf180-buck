#!/usr/bin/env python3
"""Write the klt sim request and corner matrix of the soft-start bench (spec R15, R6 clause).

  request_grid.json   C-full (5 process x 3 T x 3 Vin = 45) x load {none, 3.6 ohm} = 90 units
  matrix_grid.json    the matrix `klt corner-matrix check` diffs it against

Process bundles as in sim/steady-state/gen_requests.py (spec 0.1).
Run: python3 -I sim/soft-start/gen_requests.py   (deterministic)
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
FAMILY = {"typical": "typical", "ff": "ff", "ss": "ss", "fs": "typical", "sf": "typical"}
PROCESS = [{"name": p, "sections": [p, "mimcap_" + f, "cap_mim", "res_" + f]} for p, f in FAMILY.items()]
VIN = [4.5, 5.0, 5.5]
TEMP = [-40, 27, 125]
RLOAD = [1e9, 3.6]                  # ohm: 1e9 = no load; 3.6 = 500 mA at 1.8 V
# EN rises at 20 us; R15 allows up to 500 us, so the ramp is done by 520 us. .tran 2.5n (= T/200 at
# 2 MHz) to 700 us (180 us of regulation after the latest start), saved from EN.
TRAN = "2.5n 700u 20u 2.5n"
OPTIONS = {"keep_artifacts": True, "waveforms": True, "timeout_s": 900, "threads_per_worker": 1,
           "save_vectors": ["v(out)", "i(lind)", "v(sw_d)", "v(xtop.trip)"]}
BATCH = {"max_units_per_job": 1, "max_concurrent_jobs": 12}   # one unit per job, as steady-state

grid = {"process": PROCESS, "supply_v": {"vsrc": VIN}, "supply_waveforms": ["vsrc"],
        "temperature_c": TEMP, "params": {"rload": RLOAD}}
req = {"netlist": "bench.spice", "engine": "ngspice",
       "models": {"pdk": "gf180mcuD", "lib": "libs.tech/ngspice/sm141064.ngspice"},
       "analysis": {"kind": "tran", "args": TRAN}, "corners": grid,
       "measurements": [{"name": "vout_last", "spice": ".meas tran vout_last FIND v(out) AT=699u", "unit": "V"}],
       "batch": BATCH, "options": OPTIONS}
for name, obj in (("request_grid.json", req), ("matrix_grid.json", {k: grid[k] for k in ("process", "supply_v", "temperature_c", "params")})):
    with open(os.path.join(HERE, name), "w") as fh:
        json.dump(obj, fh, indent=1)
        fh.write("\n")
