# sim

Simulation environment and benches. Results are **simulated**, never measured.

## Prerequisites

- `ngspice` on `PATH` (record below was produced with ngspice-42), `jq`, `sha256sum`, `git`.
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

## Rules

- `sim/smoke/records/` is append-only evidence: add files, never edit them.
  A record carries the commit the run started from; the run may be from an
  uncommitted tree if the record's deck sha256 does not match the committed deck.
- The smoke bench is a toolchain check, not a device choice.
- Grids (corners, Monte Carlo) are not run by hand here; express them as
  `klt sim` requests so they go to the batch fleet.
- `lib/pdk_env.sh` is adopted from `2AMLogic/gf180-sram` by pinned reference;
  see [`../reuse.lock.json`](../reuse.lock.json).
