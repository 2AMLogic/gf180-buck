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

## `schematics/` — controller blocks (issue #34, part of #21)

Transistor-level xschem schematics of the controller blocks that are new in
this design, on the 3.3 V control rail of
[record 0003](../spec/decision-records/0003-control-rail.md) (`VDD33`,
2.97–3.63 V). The `.sch` files are drawn by `schematics/gen_schematics.py`
(net-label connectivity, sizes next to the topology) and are the sources of
truth once committed; netlists are derived with `klt netlist` only (never raw
`xschem`) by `design/netlist.sh`, committed under `netlists/`, and
`design/netlist.sh --check` reports `match` for all four.

| Block | Schematic | Does | Spec rows |
|---|---|---|---|
| `osc_ramp` | `schematics/osc_ramp.sch` | current-charged cap relaxation oscillator; the `RAMP` node is the PWM sawtooth, `CLK` the reset pulse; 3-bit MIM trim bank for the single-point trim | R7 (2 MHz ±15 %), R6 (always runs: forced PWM) |
| `pwm_comp` | `schematics/pwm_comp.sch` | continuous-time comparator `VC > RAMP` and a set/reset latch: set by `CLK`, reset by the crossing **or** `OCP_TRIP` | R6, R16 (cycle-by-cycle reset) |
| `soft_start` | `schematics/soft_start.sch` | ~125 nA into a 20 pF cap, `EN` low holds it at 0; `VREF_SS = min(cap, VBG)` from a PMOS-input unity-gain OTA; no counter | R15 |
| `ocp_sense` | `schematics/ocp_sense.sch` | Ron-sense of `VIN − SW` on the high-side switch: thick-oxide (6 V) pair with gates at `SW` and `VTHP = VIN − Itrip·RT`, branch currents mirrored into 3.3 V resistors, PMOS-input comparator, gated by `HS_ON` and a ~50 ns leading-edge blank | R16, R6 (negative current) |

Bias: each block takes one current into its `IBIAS` pin (12 µA for
`osc_ramp`, 10 µA for the others). **The bias generator (bandgap voltage over a
resistor) and the 3.3 V regulator are not in this issue**; the smoke benches
force the current.

### Adopt-or-record outcomes (`reuse.lock.json`)

| Sibling | Outcome here | Why |
|---|---|---|
| `oscillator` (`gf180-rcosc`, `kept`) | **Kept, not adopted.** Topology idea (relaxation, trimmed) only; nothing copied or instantiated. | 48 MHz / ±35 % untrimmed against 2 MHz / ±15 %; as `reuse.lock.json` already records. |
| `pwm_and_current_limit_comparator` (`gf180-comparator`, `adopted_at_interface`) | **Not instantiated; deviation recorded.** | Its `comparator_dut` is a clocked StrongARM latch (precharge on `clk` low, DR-0001). A PWM crossing has no clock faster than the 2 MHz period it is measuring, and the current-limit input is `SW`/`VIN` (up to 6 V) against a 3.3 V part. A small continuous-time comparator is drawn in `pwm_comp`, and a VIN-domain front end in `ocp_sense`. The sibling was not re-sized. If a sampled PWM is chosen later, reconsider. |
| `low_side_power_switch` Ron-sense OCP (`gf180-gate-driver`, `adopted`) | **Method adopted, side changed.** | The adopted structure senses the low-side switch (a valley limit). R16 is a *peak* inductor current trip, so `ocp_sense` senses the high-side pFET. The high-side switch is `not_adopted`: its `Ron·W` is not ratified, so the trip current in amps (`Vtrip / Ron_HS`) is **open** until the power-stage sizing issue closes it. R16's 3 : 1 window is inherited from `Ron`, as the spec says. |
| `bandgap_reference`, `error_amplifier` | Not instantiated here. | `soft_start` takes `VBG` and drives `VREF_SS` at their interface; no sibling schematic is needed in these four blocks. |

### Single-corner smoke (simulated, not measured)

`design/smoke/run.sh` (one `ngspice -b` per bench, run in sequence; typical
corner, 27 °C, nominal rails, PDK per `sim/pdk.json`). **This is a debug-grade
smoke, not corner or Monte Carlo evidence**; the PVT grid is issue #25. Record:
[`smoke/records/`](smoke/records/) (append-only).

| Bench | Run length | Result (typical, 27 °C) | What it does *not* show |
|---|---|---|---|
| `osc_ramp` | 40 µs, 1 ns step; f from cycles 30–50 (a one-state relaxation oscillator; the first 30 cycles are discarded) | 1.93 MHz at trim code 101b; ramp 1.18–1.80 V | spread over PVT; untrimmed spread; the trim range was sized by arithmetic (0 to +3.15 pF on 4.05 pF) and only code 101b was run |
| `pwm_comp` | 80 µs, 1 ns step; duty averaged over cycles 40–58 µs | duty 0.55 at `VC` 1.5 V, 0.89 at 1.7 V; `OCP_TRIP` pulses at 70 µs cut it to 0.42 | duty linearity; delay; behaviour at the ramp ends |
| `soft_start` | 700 µs, 100 ns step | 0 → 90 % in 197 µs (R15 window 100–500 µs), final 1.198 V, no overshoot | load, `Vout` overshoot, peak inductor current (system level) |
| `ocp_fwd` | 6 µs | trips at ~134 mV of `VIN − SW` (design target 100 mV; the pair/resistor offset is not yet characterised) | trip current in amps, PVT window, offset spread |
| `ocp_rev` | 6 µs | `SW` 0.2 V above `VIN` while `HS_ON`: `TRIP` max 0.7 mV (R6 no-trip, one point) | light-load reverse current in a switched `.tran` |

Known gaps for follow-up verification (#25/#26), not closed here: no
simulated edge case of ramp amplitude against the 3.3 V rail at the
2.97 V / 3.63 V rail corners (the comparator's NMOS input pair is only checked
at 1.18–1.80 V ramp); `osc_ramp` supply current is ~0.3 mA, and the 3.3 V
rail's total load is still the open item of record 0003 §4; frequency is
supply-dependent through the Schmitt window (no bandgap-referenced thresholds).
