#!/usr/bin/env python3
"""Write the klt sim requests and corner matrices of the steady-state bench.

  request_grid.json   C-full (5 process x 3 T x 3 Vin = 45) x load {0, 50, 250, 500 mA} = 180 units
  request_r8.json     R8 C-ex: the three Vin / L combinations of spec R8 (3 units)
  matrix_grid.json, matrix_r8.json   the matrices `klt corner-matrix check` diffs them against

The bundles follow spec 0.1: ff / ss skew every family (their MOS, mimcap, resistor
sections); fs / sf skew MOS only, so the mimcap and resistor sections stay typical.
Run: python3 -I sim/steady-state/gen_requests.py   (rewrites the four files, deterministic)
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "lib"))
import genkit  # noqa: E402
from genkit import PROCESS, TEMP, VIN  # noqa: E402
LOADS = [0.0, 0.05, 0.25, 0.5]              # A
# .tran 2.5n (= T/200 at 2 MHz) stop 600u, saved from 480u (120 us tail)
TRAN = "2.5n 600u 480u 2.5n"
OPTIONS = {"keep_artifacts": True, "waveforms": True, "timeout_s": 900, "threads_per_worker": 1,
           "save_vectors": ["v(out)", "i(lind)", "v(sw_d)", "v(vsrc)", "i(vsrc)"]}

# One unit per batch job (genkit.BATCH). Measured on the fleet: a lone unit takes ~180 s (any thread count),
# but units sharing an instance each run >3.4x slower (3 units: all killed at 600 s; at 3600 s the whole job
# hit the ceiling), so sharing is slower than serial. 900 s is 5x the lone-unit time; a stuck unit is a
# timeout of its own. 12 jobs in flight.


def base(corners, exclude=None):
    return genkit.request(corners, TRAN, [genkit.vout_last(599)], OPTIONS, exclude)


def dump(name, obj):
    genkit.dump(HERE, name, obj)


grid = {"process": PROCESS, "supply_v": {"vsrc": VIN}, "supply_waveforms": ["vsrc"],
        "temperature_c": TEMP, "params": {"iload": LOADS}}
dump("request_grid.json", base(grid))
dump("matrix_grid.json", genkit.matrix(grid))

# R8 (C-ex): Vin 4.5 V with L +20 %, Vin 5.5 V with L -20 %, Vin 5.0 V with L nominal;
# typical process, 27 C, 250 mA (forced PWM: CCM at every load, so ripple does not depend on it).
r8 = {"process": [PROCESS[0]], "supply_v": {"vsrc": VIN}, "supply_waveforms": ["vsrc"],
      "temperature_c": [27], "params": {"iload": [0.25, 0.25, 0.25], "lfac": [0.8, 1.0, 1.2]}}
r8_exclude = [{"supply_v": {"vsrc": 4.5}, "params": {"lfac": 0.8}}, {"supply_v": {"vsrc": 4.5}, "params": {"lfac": 1.0}},
              {"supply_v": {"vsrc": 5.0}, "params": {"lfac": 0.8}}, {"supply_v": {"vsrc": 5.0}, "params": {"lfac": 1.2}},
              {"supply_v": {"vsrc": 5.5}, "params": {"lfac": 1.0}}, {"supply_v": {"vsrc": 5.5}, "params": {"lfac": 1.2}}]
dump("request_r8.json", base(r8, r8_exclude))
dump("matrix_r8.json", genkit.matrix(r8, r8_exclude))
