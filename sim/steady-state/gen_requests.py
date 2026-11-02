#!/usr/bin/env python3
"""Write the klt sim requests and corner matrices of the steady-state bench.

  request_grid.json   C-full (5 process x 3 T x 3 Vin = 45) x load {0, 50, 250, 500 mA} = 180 units
  request_r8.json     R8 C-ex: the three Vin / L combinations of spec R8 (3 units)
  matrix_grid.json, matrix_r8.json   the matrices `klt corner-matrix check` diffs them against

The bundles follow spec 0.1: ff / ss skew every family (their MOS, mimcap, resistor
sections); fs / sf skew MOS only, so the mimcap and resistor sections stay typical.
Run: python3 -I sim/steady-state/gen_requests.py   (rewrites the four files, deterministic)
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
FAMILY = {"typical": "typical", "ff": "ff", "ss": "ss", "fs": "typical", "sf": "typical"}
PROCESS = [{"name": p, "sections": [p, "mimcap_" + f, "cap_mim", "res_" + f]} for p, f in FAMILY.items()]
VIN = [4.5, 5.0, 5.5]                       # R1: 5.0 V +/- 10 %
TEMP = [-40, 27, 125]
LOADS = [0.0, 0.05, 0.25, 0.5]              # A
# .tran 2.5n (= T/200 at 2 MHz) stop 600u, saved from 480u (120 us tail)
TRAN = "2.5n 600u 480u 2.5n"
OPTIONS = {"keep_artifacts": True, "waveforms": True, "timeout_s": 900, "threads_per_worker": 1,
           "save_vectors": ["v(out)", "i(lind)", "v(sw_d)", "v(vsrc)", "i(vsrc)"]}


# ONE unit per batch job. Measured on the fleet: a lone unit takes ~180 s (any thread count), but units
# sharing an instance each run >3.4x slower (3 units: all killed at 600 s; at 3600 s the whole job hit the
# ceiling), so sharing is slower than serial. 900 s is 5x the lone-unit time; a stuck unit is a timeout
# of its own. 12 jobs in flight.
BATCH = {"max_units_per_job": 1, "max_concurrent_jobs": 12}


def base(corners, exclude=None):
    req = {"netlist": "bench.spice", "engine": "ngspice",
           "models": {"pdk": "gf180mcuD", "lib": "libs.tech/ngspice/sm141064.ngspice"},
           "analysis": {"kind": "tran", "args": TRAN},
           "corners": corners,
           "measurements": [{"name": "vout_last", "spice": ".meas tran vout_last FIND v(out) AT=599u", "unit": "V"}],
           "batch": BATCH, "options": OPTIONS}
    if exclude:
        req["exclude"] = exclude
    return req


def dump(name, obj):
    with open(os.path.join(HERE, name), "w") as fh:
        json.dump(obj, fh, indent=1)
        fh.write("\n")


grid = {"process": PROCESS, "supply_v": {"vsrc": VIN}, "supply_waveforms": ["vsrc"],
        "temperature_c": TEMP, "params": {"iload": LOADS}}
dump("request_grid.json", base(grid))
dump("matrix_grid.json", {k: grid[k] for k in ("process", "supply_v", "temperature_c", "params")})

# R8 (C-ex): Vin 4.5 V with L +20 %, Vin 5.5 V with L -20 %, Vin 5.0 V with L nominal;
# typical process, 27 C, 250 mA (forced PWM: CCM at every load, so ripple does not depend on it).
r8 = {"process": [PROCESS[0]], "supply_v": {"vsrc": VIN}, "supply_waveforms": ["vsrc"],
      "temperature_c": [27], "params": {"iload": [0.25, 0.25, 0.25], "lfac": [0.8, 1.0, 1.2]}}
r8_exclude = [{"supply_v": {"vsrc": 4.5}, "params": {"lfac": 0.8}}, {"supply_v": {"vsrc": 4.5}, "params": {"lfac": 1.0}},
              {"supply_v": {"vsrc": 5.0}, "params": {"lfac": 0.8}}, {"supply_v": {"vsrc": 5.0}, "params": {"lfac": 1.2}},
              {"supply_v": {"vsrc": 5.5}, "params": {"lfac": 1.0}}, {"supply_v": {"vsrc": 5.5}, "params": {"lfac": 1.2}}]
dump("request_r8.json", base(r8, r8_exclude))
dump("matrix_r8.json", {**{k: r8[k] for k in ("process", "supply_v", "temperature_c", "params")}, "exclude": r8_exclude})
