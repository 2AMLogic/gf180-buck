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

The one cold-start command (T1 item 9) runs three of the benches the attestation
covers and their unit tests, and exits 0 only if all of those pass. It is not a
pass of every attested bench: the rest are hashed in `attest/item9.json` but not
run by the cold start (see below).

```
source sim/env.sh && sim/cold-start.sh
```

In order: the smoke bench, the ideal-buck bench, `python3 -m unittest discover sim/lib`,
the `design/averaged` unit tests, then `design/averaged/run.sh`. The last step sends
its 162-point grid to the Spot batch fleet through `klt sim`; a batch submit failure
fails the script, and there is no local-grid fallback. Needs `klt` on `PATH`, at the
version pinned in `.github/workflows/signoff.yml` (currently 0.9.0: the fleet runner
refuses a client whose version differs from its own, `batch_runner_version_mismatch`),
in a throwaway environment, not a host install.
Each bench appends a new record under its `records/`; commit only the ones a PR
intends and never delete one.

Attest it (needs the PDK, ngspice and the fleet, so this is local-only):

```
klt signoff --attest 9 --inventory attest/item9.json -o evidence/item9.json
```

CI cannot run the cold start (no PDK, no ngspice). `attest/item9.json` marks it
`local_only`, so CI's `klt signoff --attest 9 --inventory attest/item9.json --check
evidence/item9.json` skips it, lists it under `skipped_checks`, and still re-hashes
every inventoried file. That skip is not a pass of the cold start. A bench added
without being listed in the inventory is not caught: the PR adding it must edit
`attest/item9.json` and re-attest. The inventory hashes every bench file under
`sim/`, `design/averaged/` and `design/smoke/`; the cold start itself runs only
the smoke, ideal-buck and averaged benches, and the other benches' evidence is their
own append-only `records/`. The envelope assumes the pins in the inventory
(ngspice-46, as on the dispatch hosts; the smoke record of 2026-10-17 used ngspice-42).

The smoke bench alone:

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

`npm run test` (equivalently `pnpm -s test`) from the repository root runs these
unit tests together with the `design` netlist geometry check, the
`design/averaged` extraction tests and the README structure check. It needs only
`python3` — no PDK, no ngspice, no `klt` — and is the same entry point CI runs on
every pull request, so it is the quickest way to tell whether a change broke a
grader.

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

## Shared bench harness

The five closed-loop benches -- `steady-state`, `current-limit`, `device-stress`, `load-step`,
`soft-start` -- are the same circuit with different loads, so they share one copy of it:
[`lib/bench_harness.spice`](lib/bench_harness.spice), which each `bench.spice` pulls in with
`.include ../lib/bench_harness.spice`. It holds the §0.3 package (VIN / SW / GND, 2 wires per net),
the die decoupling, the control-domain sources, the `Xtop ... buck_top` instance and the external
inductor and output capacitor with their parasitics (spec §0.2 P-T parts).

Each deck keeps what is its own: the header, its `.include` lines, the request-axis and
fixed-assumption `.param` lines, the load card, and two source cards:

- **`Vsrc`** -- `klt` rescales that PWL per corner and can only do so in the top-level deck (the
  reason `sim/device-stress/README.md` recorded when that deck was a copy).
- **`Iosc`** -- the current-limit bench sweeps the oscillator bias as `osc_k`, but writing one
  shared `{12u*osc_k}` card is *not* behaviour-preserving for the other four: ngspice evaluates the
  brace expression and re-parses the printed decimal, which lands one ulp away from the literal
  `12u`. Measured on issue #151, that one-bit change moved a 30 us single-unit probe's `V(out)`
  from -45.0 mV to -125.8 mV and its peak I(L) from 523.5 mA to 467.8 mA -- the startup transient
  amplifies it. Each deck therefore writes the card it needs, and the unit test below pins the
  four non-sweeping decks to the identical literal.

The `.param` lines stay in the decks, deliberately. `c_out` and `esr` are request axes in
`load-step/request_{tol,full}.json` and `c_wind` in `soft-start/probe_single3.json`, while the same
names are fixed assumptions elsewhere, so a deck's own axis defaults belong to that deck. This is
not a tool limit: a `klt sim` `corners.params` override does reach a `.param` declared in an
included file (probed for issue #151 -- `lfac=0.8` against `.param l_ind={3.3u*lfac}` in an include
gave 2.64 uH, not 3.3).

`sim/lib/test_device_stress.py` is the guard: it fails if a deck stops including the harness,
re-declares one of its element cards, drops its own `Vsrc` or `Iosc`, lets the oscillator-bias card
drift between the four decks that do not sweep it, stops defining a parameter the harness reads, or
lets any shared P-T part / package / rail value drift between the five decks. Every record
written after this change pins `sim/lib/bench_harness.spice` in its `files_sha256`; records written
before it pin the deck hashes of the day and are not edited.

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

`bench.spice` is the shared harness with a 50 -> 450 -> 50 mA load at 1 A/us
(steps at 600 / 680 us, `.tran` to 760 us, last 280 us saved). Each edge is graded by
`buckmeas.load_step_pair` only if the spec §0.4 settled test passes on the cycles just before it;
otherwise that step has no value. Requests: `request_tol` = C-typ x all 18 P-T tolerance
combinations (18 units); `request_full` = C-full (45) x the two deviation-binding tolerance corners
(Ceff 4.7 uF, ESR 10 mohm, L x0.8 / x1.2; 90 units); `request_avg` = the averaged model
(`avg_step.spice`: `design/averaged/buck_avg.spice` unchanged plus the same step) at Vin x 18
tolerance combinations (54 units). `design/averaged/records/` hold loop-gain metrics only, so the R13(c)
prediction is a transient run of the averaged model, stated as such in the record. C-full x the full
tolerance cube (810 units) is not run; the record states the argument and its limit. Simulated, never measured.

## Soft-start and current-limit benches (rows R15, R16, R6 no-trip clause)

```
python3 -I sim/soft-start/gen_requests.py       # request_grid.json, matrix_grid.json
python3 -I sim/current-limit/gen_requests.py    # request_ramp.json, request_min.json, matrix_*.json
KLT_SIM_BACKEND=batch klt sim --batch-set sim/soft-start/request_grid.json \
    sim/current-limit/request_ramp.json sim/current-limit/request_min.json -o OUT --report-out BATCH.json
python3 -I sim/soft-start/collect.py --report <soft-start report>.json
python3 -I sim/current-limit/collect.py --ramp <ramp report>.json --min <min report>.json
```

Both benches include the same shared harness as `sim/steady-state/bench.spice`, so the external parts and
package are the same file, not a copy of it (see "Shared bench harness" below).
`TRIP` is internal to `buck_top`; it is saved hierarchically as `v(xtop.trip)`. Measurement code is
`buckmeas.soft_start` (0 -> 90 % of 1.8 V from EN on per-cycle means, monotonicity with a 1 mV floor,
overshoot above R4 max after the 20 MHz low-pass, peak I(L)) and `buckmeas.trip_event` (I(L) at the first
TRIP assertion). A run that never reaches 90 % has no soft-start time; a run whose TRIP never asserts
has no trip value, and the row is `not_demonstrated`, never a pass.

- `sim/soft-start/`: C-full x load {none, 3.6 ohm} = 90 units, `.tran 2.5n 700u`, saved from EN (20 us);
  rows R15 and the R6 clause (no TRIP in the last 100 us at 0 load).
- `sim/current-limit/`: C-full ramp 0 -> 3 A over 300 us from 600 us (45 units, trip current vs 0.70 - 2.1 A),
  and the R16 min-bound case (L -20 %, Vin 5.5 V, 500 mA held 160 us, 15 units). The oscillator free-runs,
  so "f min" is not forced: each unit's measured f is recorded and the min-bound row is `pass` only if
  every unit ran at or below 1.7 MHz.

Records are append-only under `records/`, simulated and pre-layout.

## Device stress and top-level dead time (rows R2, R14)

```
python3 -I sim/device-stress/gen_requests.py     # rewrites request_grid.json (135), request_ctyp.json (3), matrix_*.json
klt sim sim/device-stress/request_ctyp.json --backend batch -o OUT --report-out ctyp.json   # or request_grid.json
python3 -I sim/device-stress/collect.py --report ctyp.json --set ctyp   # writes the R2 and the R14 record
```

One closed-loop `buck_top` run per (corner, load) serves both rows; `collect.py` writes
`sim/device-stress/records/<UTC>-<sha>.json` (R2) and `sim/dead-time/records/<UTC>-<sha>-top.json` (R14).
Details, the 100 ps step, the Vth definition and what has and has not run: [`device-stress/README.md`](device-stress/README.md).
