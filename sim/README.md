# sim

Simulation environment and benches. Results are **simulated**, never measured.

## Prerequisites

- `ngspice` on `PATH` (the smoke record was produced with ngspice-42; the
  `buck-ideal` records with ngspice-46, which is what the dispatch hosts have),
  `jq`, `sha256sum`, `git`, `python3` (stdlib only).
- The gf180mcu PDK, variant `gf180mcuD`, at the revision pinned in
  [`pdk.json`](pdk.json), installed with volare in your home directory
  (nothing host-wide):
  `pip install volare` (in a venv) then
  `volare enable --pdk gf180mcu c6d73a35f524070e85faff4a6a9eef49553ebc2b`.
  Why this is `gf180mcuD` while the spec's metal/EM/DRC facts are `gf180mcuA`:
  [decision record 0002](../spec/decision-records/0002-pdk-variant-pins.md).
  `env.sh` finds it via `GF180_PDK_PATH`, `PDK_ROOT`+`PDK`, or `~/.volare` / `~/.ciel`.

## Cold start

```
sim/smoke/run.sh
```

This sources `sim/env.sh` (resolves the PDK, refuses with `PDK_MISMATCH` /
`PDK_NOT_FOUND` / `MISSING_TOOL` if the install is not the pinned one, prints
the resolved paths), runs `sim/smoke/inverter.spice` (one `.op` + a 60 ns
`.tran`, typical corner, 5 V) in a single local ngspice process, and writes a
new `sim/smoke/records/<UTC-timestamp>-<sha>.md`.

`env.sh` checks the install's revision (taken from the resolved
`.../versions/<hash>/` path) and the sha256 of `sm141064.ngspice` and
`design.ngspice`. Two installs with the same layout but different hashes exist
in practice; only the pinned one passes.

## Switching-converter bench and measurement module

```
python3 -m unittest discover sim/lib     # unit tests on synthetic waveforms
sim/buck-ideal/run.sh                    # one local ngspice run + module + JSON record
```

`sim/lib/buckmeas.py` (PDK-free, stdlib only) grades a switching-converter
`.tran` the way spec §0.4 says: the settled-window test (two consecutive
20-cycle windows, < 0.1 % in mean Vout and < 1 % in peak I(L)), then on the
last 20 settled cycles mean Vout (R4), I(L) p-p (R8), ripple after a 20 MHz
first-order low-pass (R11), efficiency over whole cycles ending on a cycle
boundary (R9/R10), switching frequency from V(sw) crossings over >= 100 cycles
(R7), and load-step deviation and recovery (R12). A run that is not settled
reports no values; R7 reports unavailable below 100 cycles. Each result
restates the run length, step and window.

`sim/buck-ideal/` is the module's end-to-end bench: ideal switches (no PDK
devices), external parts P-T and the §0.3 typical package at 2 wires per net,
Vin 5 V, D = 0.36, 2 MHz, 250 mA, then a 250 -> 450 mA step. It is open loop
and is **not** a claim against any spec row. `params.json` is the single
source for the deck and the module; `run.sh` writes
`records/<UTC>-<sha>.json` naming the ngspice version, the deck and params
sha256, the stop time and the step. Bench assumptions the spec does not name
(die-side decoupling, a damping resistor in series with the winding
capacitance, omitted pad capacitance, 3 ns dead time with body diodes) are
commented in `buck.spice`.

## Rules

- `sim/smoke/records/` and `sim/buck-ideal/records/` are append-only evidence: add files, never edit them.
  A record carries the commit the run started from; the run may be from an
  uncommitted tree if the record's deck sha256 does not match the committed deck.
- The smoke bench is a toolchain check, not a device choice.
- Grids (corners, Monte Carlo) are not run by hand here; express them as
  `klt sim` requests so they go to the batch fleet.
- `lib/pdk_env.sh` is adopted from `2AMLogic/gf180-sram` by pinned reference;
  see [`../reuse.lock.json`](../reuse.lock.json).
