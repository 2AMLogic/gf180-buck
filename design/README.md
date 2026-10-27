# design

Design sources that are not layout. Everything here is simulated, never measured.

## `averaged/` — R13 evidence part (a): averaged-model loop gain

PDK-free. An averaged CCM voltage-mode buck power stage, the type-III
compensator of [`compensator.md`](compensator.md) (derivation, design-to
values, assumptions), and a Middlebrook-injection `.ac` bench, swept over the
P-T tolerance box:

| Axis | Values |
|---|---|
| Vin | 4.5, 5.0, 5.5 V |
| L (3.3 uH) | -20 %, 0, +20 % |
| C_eff | 4.7, 6, 12 uF |
| ESR | 5, 10 mOhm |
| Load (ideal current sink) | 0, 250, 500 mA |

= 162 points. Bounds graded per point: fc 100-250 kHz, PM >= 45 deg,
GM >= 10 dB. Failing points are reported as failures.

| File | Role |
|---|---|
| `averaged/buck_avg.spice` | circuit body: averaged stage, compensator, loop break |
| `averaged/gen_request.py` | writes `sweep_request.json` (the cross product, fixed order) |
| `averaged/sweep_request.json` | the `klt sim` request for the grid; untracked, written by `gen_request.py` |
| `averaged/extract.py` | fc / PM / GM from the complex loop gain, writes the record |
| `averaged/test_extract.py` | closed-form synthetic-loop unit tests |
| `averaged/run.sh` | the one command |
| `averaged/records/` | append-only JSON records |

### Run it

    design/averaged/run.sh                      # sweep -> extract -> records/<utc>-<hash>.json
    python3 -m unittest discover design/averaged   # extraction unit tests (no simulator needed)

`run.sh` regenerates the request and submits it with `klt sim`; on a dispatch
worker `KLT_SIM_BACKEND=batch` sends the grid to the Spot batch fleet, and
`run.sh` defaults to `batch` otherwise. It never loops `ngspice` locally; a
failed submit exits non-zero. The record carries fc, PM and GM for every point
with per-bound pass/fail, the ngspice version, the deck sha256, the request
sha256, the batch job id and `results_sha256` (hash of the rounded results).
Printed precision: fc 0.001 kHz, PM 0.01 deg, GM 0.01 dB; a re-run reproduces
the same `results_sha256`.

Extraction (`extract.py`): `T = -v(vo)/v(b)` from the complex AC vectors
(`options.complex_vectors`). fc is the highest-frequency downward 0 dB
crossing; PM = 180 + unwrapped phase at fc; GM is the minimum of
`-20*log10|T|` over every -180 degree crossing, `"none"` when the phase never
reaches -180 inside 100 Hz - 20 MHz.

### Status of the sweep record

**No 162-point record is committed yet.** The batch fleet runner image runs
`klt 0.7.0`, which lacks `corners.params`, `measurements[].transfer` and
`options.complex_vectors` (job `klt-sim-6014a677233b` exited 87,
`batch_runner_feature_unsupported`; tracked at 2AMLogic/klayout-tools#3676).
The grid was not run locally. Local single-point debug probe at the nominal
point (Vin 5 V, L 3.3 uH, C_eff 6 uF, ESR 5 mOhm, 250 mA; ngspice 42):
fc 149.924 kHz, PM 62.41 deg, GM 30.00 dB from `extract.py`, against
fc 149.9237 kHz, PM 62.4101 deg from klt's own `transfer` metrics on the same
run. That is one point, not the sweep.
