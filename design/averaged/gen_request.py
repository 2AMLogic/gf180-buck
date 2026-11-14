#!/usr/bin/env python3
"""Write sweep_request.json: the klt sim request for the 162-point grid.

Axes (outer to inner): Vin x L x C_eff x ESR x load. klt corners.params rows
zip by index, so the cross product is expanded here, in a fixed order.
"""
import itertools
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "sim", "lib"))
import genkit  # noqa: E402
from genkit import CEFF, ESR, LFAC, VIN  # noqa: E402

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
    genkit.dump(HERE, "sweep_request.json", request)
