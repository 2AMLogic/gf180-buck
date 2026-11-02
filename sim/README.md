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

- `sim/smoke/records/`, `sim/buck-ideal/records/`, `sim/steady-state/records/` and `sim/load-step/records/` are append-only evidence: add files, never edit them.
  A record carries the commit the run started from; the run may be from an
  uncommitted tree if the record's deck sha256 does not match the committed deck.
- The smoke bench is a toolchain check, not a device choice.
- Grids (corners, Monte Carlo) are not run by hand here; express them as
  `klt sim` requests so they go to the batch fleet.
- `lib/pdk_env.sh` is adopted from `2AMLogic/gf180-sram` by pinned reference;
  see [`../reuse.lock.json`](../reuse.lock.json).

## Dead-time smoke

```
sim/dead-time/run.sh     # one operating point via `klt sim --backend local` + a no-dead-time negative control
```

Real `gate_drive` into the real `power_stage` (netlists from `design/netlists/`),
typical process, 27 °C, Vin 5.0 V, 0.5 A DC sink on SW. Writes a new append-only
`sim/dead-time/records/<UTC>-<sha>.json`. Simulated, not measured; not a corner
run. See `design/README.md`.

## Steady-state bench (rows R4, R6, R7, R8, R9/R10 pre-layout, R11)

```
python3 -I sim/steady-state/gen_requests.py     # rewrites request_grid.json, request_r8.json, matrix_*.json
klt sim --batch-set sim/steady-state/request_grid.json sim/steady-state/request_r8.json --report-out ...
python3 -I sim/steady-state/collect.py --report GRID.json --report R8.json    # grade + write records/<UTC>-<sha>.json
```

`bench.spice` wraps `buck_top.spice`: C-full (45) x load {0, 50, 250, 500 mA} = 180 units
(`request_grid.json`) plus the three R8 Vin / L combinations (`request_r8.json`), `.tran` to
600 us with the last 120 us saved. Grid parameters are the request axes (`iload`, `lfac`);
there is no separate params file. `sim/lib/rawgrade.py` reads each `waveform.raw` and applies
`buckmeas` (spec §0.4). A unit that did not settle, timed out or was lost carries no value and
the row reports `not_demonstrated`; nothing is relaxed. The committed record is simulated, pre-layout
evidence; R9/R10 are not the graded post-layout value. See the record for per-unit settling windows.

## Load-step bench (rows R12, R13(b), R13(c))

```
python3 -I sim/load-step/gen_requests.py      # rewrites request_{tol,full,avg}.json, matrix_*.json
klt sim --batch-set sim/load-step/request_tol.json sim/load-step/request_full.json sim/load-step/request_avg.json --report-out ...
python3 -I sim/load-step/collect.py --tol TOL.json --full FULL.json --avg AVG.json    # grade + write records/<UTC>-<sha>.json
```

`bench.spice` is the steady-state deck with the load replaced by 50 -> 450 -> 50 mA at 1 A/us
(steps at 600 / 680 us, `.tran` to 760 us, last 280 us saved). Each edge is graded by
`buckmeas.load_step_pair` only if the spec §0.4 settled test passes on the cycles just before it;
otherwise that step has no value. Requests: `request_tol` = C-typ x all 18 P-T tolerance
combinations (18 units); `request_full` = C-full (45) x the two deviation-binding tolerance corners
(Ceff 4.7 uF, ESR 10 mohm, L x0.8 / x1.2; 90 units); `request_avg` = the averaged model
(`avg_step.spice`: `design/averaged/buck_avg.spice` unchanged plus the same step) at Vin x 18
tolerance combinations (54 units). `design/averaged/records/` hold loop-gain metrics only, so the R13(c)
prediction is a transient run of the averaged model, stated as such in the record. C-full x the full
tolerance cube (810 units) is not run; the record states the argument and its limit. Simulated, never measured.
