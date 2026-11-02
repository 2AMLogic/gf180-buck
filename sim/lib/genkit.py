"""Shared pieces of the sim/*/gen_requests.py request generators.

The spec 0.1 process bundles, the supply / temperature axes, the one-unit-per-job batch block, the
klt sim request skeleton and the deterministic JSON writer. Benches keep only what is theirs (analysis,
options, measurements, loads, matrices). Imported after putting sim/lib on sys.path.
"""
import json
import os

# spec 0.1: ff / ss skew every family (MOS, mimcap, resistor sections); fs / sf skew MOS only
FAMILY = {"typical": "typical", "ff": "ff", "ss": "ss", "fs": "typical", "sf": "typical"}
PROCESS = [{"name": p, "sections": [p, "mimcap_" + f, "cap_mim", "res_" + f]} for p, f in FAMILY.items()]
VIN = [4.5, 5.0, 5.5]                       # R1: 5.0 V +/- 10 %
TEMP = [-40, 27, 125]
# One unit per batch job: measured on the fleet, units sharing an instance run slower than serial.
BATCH = {"max_units_per_job": 1, "max_concurrent_jobs": 12}
MATRIX_KEYS = ("process", "supply_v", "temperature_c", "params")


def vout_last(at_us):
    return {"name": "vout_last", "spice": ".meas tran vout_last FIND v(out) AT=%du" % at_us, "unit": "V"}


def request(corners, tran, measurements, options, exclude=None):
    """klt sim request of a bench.spice transient on the gf180mcuD models."""
    req = {"netlist": "bench.spice", "engine": "ngspice",
           "models": {"pdk": "gf180mcuD", "lib": "libs.tech/ngspice/sm141064.ngspice"},
           "analysis": {"kind": "tran", "args": tran},
           "corners": corners,
           "measurements": measurements,
           "batch": BATCH, "options": options}
    if exclude:
        req["exclude"] = exclude
    return req


def matrix(corners, exclude=None):
    """The matrix `klt corner-matrix check` diffs a request's corners against."""
    m = {k: corners[k] for k in MATRIX_KEYS}
    if exclude:
        m["exclude"] = exclude
    return m


def dump(here, name, obj):
    with open(os.path.join(here, name), "w") as fh:
        json.dump(obj, fh, indent=1)
        fh.write("\n")
