# gf180-buck

A synchronous inductive buck converter on the
[gf180mcu](https://github.com/google/gf180mcu-pdk) open PDK — on-die power
switches, gate drive, and a PWM controller, with an external inductor and
output capacitor — designed by AI agents driving
[klayout-tools](https://github.com/2AMLogic/klayout-tools) and the
open-source xschem + ngspice flow.

**Status: specification ratified on merge of issue #2; design and simulation
under way.** Schematics, netlists, a generated power-stage layout and 67
committed simulation records are on `main` (counts read at `64535b7`,
2026-11-15); no post-layout or measured result exists, and the switched closed
loop does not yet regulate in simulation (issue #82).

**T1 status:** tier verdict of record is `null` — 4 of 11 T1 evidence items met
(items 1 design sources, 2 layout, 9 testbenches shipped, 10 repo hygiene; the
other seven — DRC clean, LVS clean, corner verification, Monte Carlo evidence,
post-layout verification, characterization report, power delivery — are
`unmet`/no-evidence), graded by `klt signoff` from [`manifests/gf180-buck.json`](manifests/gf180-buck.json)
and committed as [`manifests/gf180-buck.signoff.json`](manifests/gf180-buck.signoff.json);
CI re-grades and fails on drift (see [`manifests/README.md`](manifests/README.md)).
Counts read at `64535b7`, 2026-11-15.

**Built agent-native.** Every specification, decision record, testbench, and
line of documentation here is produced by AI agents working from a ratified
spec and an append-only evidence trail — not human-authored work that agents
merely assisted with. Verification is the product: every claim traces to a
recorded result under PVT corners. Where the agents hit friction with the
open-source tooling — most often
[klayout-tools](https://github.com/2AMLogic/klayout-tools) — that friction is
filed as a public issue against the tool itself, so the fix benefits everyone
using gf180mcu, not just this repo.

## Why this block, on this node

A buck converter is where a chip's layout has to carry amperes. The power
switches are large, the switch node swings the full input rail at every
cycle, and every milliohm of metal between the pads and the switches costs
efficiency. That makes the metal stack the design: wide straps, distributed
current collection from the device array, via arrays sized against
electromigration limits, and wide-metal rules on the top layer.

The gf180mcu design manual documents several MetalTop thicknesses, up to
30 kÅ, with electromigration allowances that scale with thickness. This
block is drawn for the thick option, so it exercises the thick-metal rule
set — wide-metal spacing, density, and slotting where the manual requires
it — that a core block rarely reaches. gf180mcu's 5 V / 6 V devices make a 5 V input converter native to
the process rather than a stacked-device workaround.

## Scope

- **In scope**: the high-side and low-side power switches, their gate
  drivers and dead-time control, the PWM controller (error amplifier,
  compensation, modulator, oscillator), soft start, cycle-by-cycle current
  limit, and the power-metal layout to the pads.
- **Not in scope**: the inductor and output capacitor, which are external
  and modelled at the boundary with their parasitics; the package, which is
  modelled as bond-wire and pad parasitics.
- **Same-PDK siblings**: `gf180-gate-driver` has ratified a low-side on-die
  power switch, its `Ron·W` baseline, and an electromigration budget for
  thick MetalTop; `gf180-bandgap` builds a reference, `gf180-opamp` an
  amplifier, `gf180-comparator` a comparator, and `gf180-rcosc` an
  oscillator. Each is a candidate to adopt rather than redesign; the
  decision for each is recorded.

## Target specification

Ratified by [decision record 0001](spec/decision-records/0001-ratify-target-spec.md)
on merge of the pull request that carries it; the full table (min / typ / max,
grading condition, corner set, external parts, for all three tiers) is
[`spec/target-spec.md`](spec/target-spec.md). A row is a design-to target,
never a result. Pre-layout simulated results exist for several rows (see
[Reproduce](#reproduce)); no switched bench row is graded passing (issue #82)
and no post-layout result exists, so no target-tier row has a passing record
yet. Summary at the target tier, with
the external parts every number assumes (inductor 3.3 µH ±20 %, DCR 100 mΩ typ,
Isat ≥ 1.0 A; output capacitor 10 µF nominal, ≥ 4.7 µF effective, ESR ≤ 10 mΩ):

| Parameter | Target | Fallback | Stretch |
|---|---|---|---|
| Input voltage | 5.0 V ±10% | 3.3 V ±10% | — |
| Output voltage | 1.8 V fixed, ±4% untrimmed | 1.8 V fixed, ±5% | 1.0–3.3 V programmable |
| Load current | 0–500 mA | 0–200 mA | 0–1 A |
| Light-load mode | forced PWM | forced PWM | forced PWM |
| Switching frequency | 2 MHz ±15% | 1 MHz ±15% | 4 MHz ±15% |
| Peak efficiency (simulated, post-layout, excludes inductor core loss) | ≥ 85% | ≥ 80% | ≥ 90% |
| Output ripple | ≤ 1% of Vout | ≤ 2% | ≤ 0.5% |
| Load-step transient | ≤ 5% of Vout, 10%–90% load step | ≤ 10% | ≤ 3% |
| Control | voltage mode, PM ≥ 45°, GM ≥ 10 dB | same | same |
| Dead time | 1–6 ns, zero overlap | 1–10 ns | 1–3 ns |
| Protection | soft start, cycle-by-cycle current limit (0.70–2.1 A trip window) | soft start, current limit | + thermal shutdown |
| Top metal | 30 kÅ MetalTop | thinner MetalTop option, argued | — |
| Signoff | DRC + LVS clean, EM-checked, post-layout re-verified | — | — |

Maturity ladder: spec ratified → power stage sized and EM budget recorded →
controller and closed loop simulated across PVT → layout DRC/LVS-clean →
post-layout re-verification → shuttle seat → measured silicon. **Current
position: rung two** — the power stage is sized and an 18-row power-path EM
budget, all `pass`, is recorded in [`layout/record.md`](layout/record.md)
(read at `64535b7`, 2026-11-15; T1 item 11 is not yet attested). The switched
closed loop does not yet regulate in simulation (issue #82), so rung three is
not reached.

## Reproduce

Every result on `main` is simulated, never measured. Run from the repository
root; prerequisites (ngspice, jq, the pinned gf180mcuD PDK install) are in
[`sim/README.md`](sim/README.md). Each command appends a new record under its
`records/` directory; records are append-only evidence.

| Result | Cold-start command | Record |
|---|---|---|
| Cold start (T1 item 9): smoke bench, ideal-switch buck bench, `sim/lib` and `design/averaged` unit tests, averaged-model grid (batch fleet) | `source sim/env.sh && sim/cold-start.sh` | `sim/smoke/records/`, `sim/buck-ideal/records/`, `design/averaged/records/` |
| Toolchain smoke (one `.op` + short `.tran`, typical corner) | `sim/smoke/run.sh` | `sim/smoke/records/` |
| Ideal-switch buck bench (open loop, not a spec claim) | `sim/buck-ideal/run.sh` | `sim/buck-ideal/records/` |
| Dead-time smoke (real gate drive into the power stage, one operating point + no-dead-time control) | `sim/dead-time/run.sh` | `sim/dead-time/records/` |
| Controller-block smoke (six benches, single corner) | `design/smoke/run.sh --record` | `design/smoke/records/` |
| Averaged-model loop gain (162-point `klt sim` grid, batch fleet) | `design/averaged/run.sh` | `design/averaged/records/` |
| Steady-state, load-step, soft-start, current-limit and device-stress benches | batch-fleet pipeline (`gen_requests.py` → `klt sim --batch-set` → `collect.py` per bench) — see the per-bench sections of [`sim/README.md`](sim/README.md) | `sim/steady-state/records/`, `sim/load-step/records/`, `sim/soft-start/records/`, `sim/current-limit/records/`, `sim/device-stress/records/` |

Every bench above has committed records on `main` — 67 records across the ten
`records/` directories at `64535b7`, 2026-11-15 — but none grades a spec row
as passing. The newest averaged-model record
([`design/averaged/records/20261114T233325Z-781e1a29003d.json`](design/averaged/records/20261114T233325Z-781e1a29003d.json))
reports `pass_all: 114` / `fail_any: 48` over the 162-point grid: no grid
point fails phase or gain margin (min PM 56.27°, min GM 22.3 dB) and all 48
failures are frequency-error. The newest switched steady-state record
([`sim/steady-state/records/20261102T014053Z-4a850294020b.json`](sim/steady-state/records/20261102T014053Z-4a850294020b.json))
grades R4, R6 and R11 `fail` and R7–R10 `not_demonstrated`: the closed loop
does not regulate in simulation yet (issue #82). No post-layout, power-metal,
efficiency, or silicon result exists yet: those rows of the spec table are not
reproducible and nothing in this repository claims them.

The tier verdict itself is re-graded, not hand-read:

```
uvx --from "klayout-tools==0.9.0" klt signoff \
    --manifest manifests/gf180-buck.json \
    --tiers-doc manifests/design-evidence-tiers.md --format json
```

## Repo layout

```
spec/          ratified spec + decision records
design/        schematics / netlists (xschem)
sim/           testbenches + PVT corner results (ngspice)
layout/        GDS + DRC/LVS/EM reports (klayout-tools driven)
manifests/     klt signoff manifest, tier doc and item attestations
measurements/  silicon characterization (empty until tape-out)
```

## License

Apache License 2.0 — see [LICENSE](LICENSE).
