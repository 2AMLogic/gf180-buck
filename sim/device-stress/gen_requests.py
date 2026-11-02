#!/usr/bin/env python3
"""Write the klt sim requests and corner matrices of the device-stress / top-level dead-time bench.

  request_grid.json   C-full (5 process x 3 T x 3 Vin = 45) x load {0, 50, 500 mA} = 135 units  (R2, R14)
  request_ctyp.json   C-typ (typical, 27 C, 5.0 V) x the same three loads = 3 units: the part of the grid
                      that fits one session on the batch fleet (see README "What ran")
  matrix_grid.json, matrix_ctyp.json   the matrices `klt corner-matrix check` diffs them against

One run serves both rows: R2 and R14 name the same corners and loads (spec target tier), so the same
waveform is graded twice by collect.py. Corner bundles follow spec 0.1 (as sim/steady-state/gen_requests.py).
Run: python3 -I sim/device-stress/gen_requests.py   (rewrites the four files, deterministic)
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "lib"))
import genkit  # noqa: E402
from genkit import PROCESS, TEMP, VIN  # noqa: E402
LOADS = [0.0, 0.05, 0.5]                    # A: R2 and R14 target tier
# Spec 0.4: the edge windows use <= 100 ps, and ngspice cannot vary .tran's max step inside one run, so
# the whole run is 100 ps (default and tighter tolerances were tried: edge steps stayed >= 1 ns).
# Saved from 540 us: 60 us = >= 40 cycles above 0.7 MHz, which the settled test (two 20-cycle windows) needs.
TRAN = "100p 600u 540u 100p"
VECTORS = ["v(out)", "i(lind)", "v(sw_d)", "v(vsrc)", "i(vsrc)",          # rawgrade (settle, clock)
           "v(xtop.gh)", "v(xtop.gl)", "v(vin_d)", "v(gnd_d)"]            # power-device terminals
# 100 ps over 600 us is ~6 M points: measured 0.19 ms/point in the quiet start-up, so ~1200-1800 s per unit.
# One unit per job (genkit.BATCH; sharing an instance is slower than serial, see steady-state), 3300 s < the 3600 s job ceiling.
OPTIONS = {"keep_artifacts": True, "waveforms": True, "timeout_s": 3300, "threads_per_worker": 1,
           "save_vectors": VECTORS}
MEAS = [  # DC levels of the Vth replicas (constant-current Vth, bench.spice), read late in the run
    {"name": "vthn", "spice": ".meas tran vthn FIND v(vthn) AT=599u", "unit": "V"},
    {"name": "vthp", "spice": ".meas tran vthp FIND v(vthp) AT=599u", "unit": "V"}]


def base(corners):
    return genkit.request(corners, TRAN, MEAS, OPTIONS)


def dump(name, obj):
    genkit.dump(HERE, name, obj)


def main():
    grid = {"process": PROCESS, "supply_v": {"vsrc": VIN}, "supply_waveforms": ["vsrc"],
            "temperature_c": TEMP, "params": {"iload": LOADS}}
    dump("request_grid.json", base(grid))
    dump("matrix_grid.json", genkit.matrix(grid))
    ctyp = {"process": [PROCESS[0]], "supply_v": {"vsrc": [5.0]}, "supply_waveforms": ["vsrc"],
            "temperature_c": [27], "params": {"iload": LOADS}}
    dump("request_ctyp.json", base(ctyp))
    dump("matrix_ctyp.json", genkit.matrix(ctyp))


if __name__ == "__main__":
    main()
