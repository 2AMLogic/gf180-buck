#!/usr/bin/env python3
"""Write sweep_request.json: the klt sim request for the 162-point grid.

Axes (outer to inner): Vin x L x C_eff x ESR x load. klt corners.params rows
zip by index, so the cross product is expanded here, in a fixed order.
"""
import itertools
import json
import os

VIN = [4.5, 5.0, 5.5]
LFAC = [0.8, 1.0, 1.2]                  # L = 3.3 uH x (1 +/- 20 %)
CEFF = [4.7e-6, 6e-6, 12e-6]            # spec section 0.2 effective C range
ESR = [5e-3, 10e-3]                     # spec R13 ESR 5-10 mOhm
ILOAD = [0.0, 0.25, 0.5]                # ideal current sink, A

rows = list(itertools.product(VIN, LFAC, CEFF, ESR, ILOAD))
request = {
    "netlist": "buck_avg.spice",
    "engine": "ngspice",
    "corners": {
        "params": {
            name: [r[i] for r in rows]
            for i, name in enumerate(("vin", "lfac", "ceff", "esr", "iload"))
        }
    },
    "analysis": {"kind": "ac", "args": "dec 100 100 20meg"},
    "measurements": [
        {"name": "fc_klt", "transfer": {"num": "v(t)", "den": "v(b)", "metric": "unity_crossing_hz"}, "unit": "Hz"},
        {"name": "pm_klt", "transfer": {"num": "v(t)", "den": "v(b)", "metric": "phase_margin_deg"}, "unit": "deg"},
    ],
    "options": {"complex_vectors": ["v(vo)", "v(b)"], "keep_artifacts": True, "timeout_s": 120},
}
assert len(rows) == 162

if __name__ == "__main__":
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sweep_request.json")
    with open(path, "w") as fh:
        json.dump(request, fh, indent=1)
        fh.write("\n")
