# gf180-buck

A synchronous inductive buck converter on the
[gf180mcu](https://github.com/google/gf180mcu-pdk) open PDK — on-die power
switches, gate drive, and a PWM controller, with an external inductor and
output capacitor — designed by AI agents driving
[klayout-tools](https://github.com/2AMLogic/klayout-tools) and the
open-source xschem + ngspice flow.

**Status: specification ratified on merge of issue #2; nothing is designed yet.**

**T1 status:** tier verdict of record is `null` — 0 of 11 T1 evidence items
met, graded by `klt signoff` from [`manifests/gf180-buck.json`](manifests/gf180-buck.json)
and committed as [`manifests/gf180-buck.signoff.json`](manifests/gf180-buck.signoff.json);
CI re-grades and fails on drift (see [`manifests/README.md`](manifests/README.md)).

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
never a result: nothing here is simulated yet. Summary at the target tier, with
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
position: spec ratified.**

## Repo layout

```
spec/          ratified spec + decision records
design/        schematics / netlists (xschem)
sim/           testbenches + PVT corner results (ngspice)
layout/        GDS + DRC/LVS/EM reports (klayout-tools driven)
measurements/  silicon characterization (empty until tape-out)
```

## License

Apache License 2.0 — see [LICENSE](LICENSE).
