# 0008 — Error-amplifier input common mode: move it into the op-amp's 1.20–2.70 V range

- **Status**: Proposed 2026-11-11. The common-mode choice (§3) is made; **R4 and start-up closure are conditional on
  three open items (§7) that go back to the operator**. No netlist, schematic, spec row or earlier record is edited.
- **Date**: 2026-11-11
- **Raised by**: issue #131, from operator ruling 2026-11-11 (`fleet:decide` round 20261111-r14, q31, recorded on
  `2AMLogic/gf180-opamp#295`): the buck raises the error amplifier's input common mode into the op-amp's input range;
  the op-amp is not re-sized and opens no row. Candidate cause for #82 (closed-loop non-regulation).
- **Cross-reference**: [`0004-error-amplifier-gbw.md`](0004-error-amplifier-gbw.md) §4 (option A) is **unchanged**;
  this record is the place its op-amp side points at. DR-0004 holds the netlists and the settled-test gate until the
  re-pin, and so does this record.
- **Amends**: nothing. **No ratified row changed**: R4, R9, R12, R13, R15, R16 are not relaxed.
- **Claims made**: arithmetic and closed-form AC only (§5 states exactly which). Nothing here is simulated at the
  system level and nothing is measured. The op-amp-side figures (1.20–2.70 V range, 0.16 µA vs 5 µA P-pair at 0.6 V)
  are quoted from `gf180-opamp` (DR-0005; `sim/buck-load-gbw-pm/records/20261110-084324-e8a2a7b.md`, PR #312) and were
  **not re-derived here**.

## 1. Where the common mode is today (read at `e50e208`)

The error amplifier is in an inverting type-III network (`design/netlists/compensator.spice`): the reference drives
the non-inverting input and the feedback node `FBN` is the inverting input, held at the reference by the loop.
Both inputs therefore sit at `Vref`. Today `Vref = 0.6 V` (`design/compensator.md`: `Rtop/Rbot = 2`, `Rtop` 10 kΩ,
`Rbot` 5 kΩ), made by a 1 MΩ/1 MΩ divider on `VREF_SS` (0 → 1.18 V). That is 0.6 V below the op-amp's 1.20 V floor.

## 2. What constrains the choice

- **Floor**: op-amp range 1.20 V (not acceptable *on* the edge, per the issue).
- **Ceiling**: the node is `Vout` through a resistive divider, so `Vref < Vout` = 1.80 V; with Vout at its R4 minimum
  (1.728 V) the node is still below that. The op-amp's 2.70 V is never the binding upper limit: the usable window is
  about **1.20–1.73 V**, and the upper margin is taken against `Vout`, not 2.70 V. (Margin to 2.70 V is stated too.)
- **Source**: the adopted bandgap is 1.20 V, ±2 % untrimmed 3σ (`reuse.lock.json`, `gf180-bandgap` @ `c68ccc6`) —
  itself *on* the floor. Any in-range reference is a **scaled** reference, so it needs a gain of `Vref/1.20`.
- **R4** (`spec/target-spec.md`, linear sum, ±4 %): reference ±2 % + divider ±1 % + amplifier offset and finite
  gain ±1 %.

## 3. Decision: `Vref` (= error-amplifier common mode) = **1.50 V** nominal

Candidates, margin to the floor at the *low* corner, taking the node as `Vref·(1 − 2 %)` less a 0.10 V allowance for
the soft-start follower's offset and its unmeasured PVT drift (the follower sits 17 mV low at typical, §4):

| `Vref` | Scale vs 1.20 V | Low-corner node | Margin to 1.20 V | Margin to `Vout`,min 1.728 V | `Rtop/Rbot` | Verdict |
|---|---|---|---|---|---|---|
| 1.25 V | 1.04 | 1.125 V | **−0.075 V (inside the dead zone)** | +0.353 V (node-high 1.375 V) | 0.44 | rejected: fails floor |
| **1.50 V** | **1.25** | **1.370 V** | **+0.170 V** | **+0.098 V** (node-high 1.630 V) | **0.20** | **chosen** |
| 1.62 V | 1.35 | 1.488 V | +0.288 V | **−0.025 V** (node-high 1.753 V) | 0.11 | rejected: ceiling collides with Vout |
| 1.20 V | 1.00 | — | edge | — | — | rejected (issue: edge not acceptable) |

(Node-high = `Vref·(1 + 2 %) + 0.10 V`: 1.50 V → 1.630 V, 1.728 − 1.630 = 0.098 V; 1.62 V → 1.753 V, over 1.728 V.)
Margin to 2.70 V at 1.50 V: **1.07 V** at node-high. The 0.10 V allowance is an assumption of this record, not a
characterised spread; §7 item 2 closes it.

*Erratum (2026-11-11, #133):* the 1.25 V row originally read "+0.603 V (node-high 1.125 V)", which repeated the
low-corner node. By the definition above, node-high = 1.25 V·1.02 + 0.10 V = 1.375 V, so the margin to `Vout`,min
1.728 V is +0.353 V. Only that cell changed; the verdict (rejected: fails the 1.20 V floor) and the 1.50 V choice are
unchanged.

## 4. What 1.50 V does to R4

Because `Vout = Vref·(1 + Rtop/Rbot)`, a fixed error `ΔV` on the reference path or at the amplifier input reaches
`Vout` as `ΔV·(1 + Rtop/Rbot)`. Relative to 1.80 V:

| Source of error | At `Vref` 0.6 V (`Rtop/Rbot` 2) | At `Vref` 1.50 V (`Rtop/Rbot` 0.2) |
|---|---|---|
| 1 mV of reference or input offset | 0.167 % of Vout | **0.067 %** of Vout (2.5× less) |
| Sensitivity of Vout to a divider *ratio* error `ε` | 0.667·ε | **0.167·ε** (4× less) |
| `soft_start` follower, 17 mV low at typical (`design/README.md`) | 1.5 % (0.591 V vs 0.6 V) | **1.13 % of Vref**, i.e. 20 mV at Vout |

Line by line, R4 target (±4 %, linear sum):

| Line | Budget | At 1.50 V | Status |
|---|---|---|---|
| Reference | ±2 % | ±2 % **only if** the 1.25× scaling stays inside the bandgap's own ±2 % | **open (§7.1)** |
| Divider ratio | ±1 % | ±1 % resistor ratio costs ±0.17 %; budget holds with 6× slack | closes |
| Amplifier offset + finite DC gain | ±1 % | 1 % of Vout is 15 mV input-referred (was 6 mV) | closes if offset ≤ 15 mV; the op-amp's offset row was not read here (§7.3) |
| `soft_start` follower offset | not in the budget | 1.13 % of Vref typical, spread uncharacterised | **open (§7.2)**; a systematic part can be removed by targeting the tap at 1.517 V, the spread cannot |

So the arithmetic **does not by itself prove** R4: it shows the 1.50 V choice is strictly easier than 0.6 V on every
line, and names the two terms that decide it. R4 is not relaxed to make it fit.

Removing `RREF1`/`RREF2` (1 MΩ each, §1) removes a ratio line and a 1 MΩ load; `Rbot` rises to 50 kΩ and its bias
current falls from `0.6 V/5 kΩ` = 120 µA to `1.5 V/50 kΩ` = **30 µA**, carried by `Vout` through `Rtop`
(`(1.8 − 1.5)/10 kΩ`), i.e. by the load side, not the R9 control-rail quiescent (the reference-scaling stage and the
follower's quiescent are the R9 terms, **not yet sized**: §7.1).

## 5. Type-III network for the new ratio (load definition for `gf180-opamp#295`)

At AC the inverting node is a virtual ground, so `Rbot` is in parallel with nothing the loop gain sees:

    Gc = Zf/Zi,  Zi = Rtop || (R3 + 1/(s·C3)),  Zf = (R2 + 1/(s·C1)) || 1/(s·C2)

is independent of `Rbot` (`design/compensator.md`). **Changing `Rtop/Rbot` from 2 to 0.2 by moving `Rbot` from 5 kΩ
to 50 kΩ with `Rtop` held at 10 kΩ leaves every compensator value unchanged**:

| Quantity | Value (unchanged) |
|---|---|
| `Rtop` / `Rbot` | 10 kΩ / **50 kΩ** (was 5 kΩ) |
| R2, R3 | 4.55 kΩ, 204 Ω |
| C1, C2, C3 | 1.75 nF, 35.7 pF, 780 pF |
| fz1, fz2 | 20.0 kHz, 20.0 kHz |
| fp1, fp2 | 1.00 MHz, 1.00 MHz |
| Reference / bias point (both inputs) | **1.50 V** (was 0.6 V); `FBN` at DC = 1.50 V; EA output `VC` bias point unchanged by this record |

What *does* move for the op-amp is the noise gain `NG = 1 + Zf/(Zi || Rbot)` it must close the loop against.
Closed-form, ideal passives, computed here (not simulated):

| f | `NG`, `Rbot` 5 kΩ | `NG`, `Rbot` 50 kΩ |
|---|---|---|
| 1 kHz | 26.86 | 10.85 |
| 20 kHz | 2.92 | 1.98 |
| 150 kHz (fc) | 4.45 | 4.00 |
| 1 MHz | 12.61 | 12.20 |
| 8 MHz | 3.24 | 3.15 |

At and above crossover the load is within 10 % of today's and slightly lighter, so the ~8 MHz GBW target of DR-0004
is not made harder by this change. The "instability near 1.1 MHz GBW" in DR-0004 §1 is not shown to be this
operating-point problem or a bandwidth one; that separation needs the re-run at the new common mode (§8).

## 6. Start-up through the amplifier's dead zone

`soft_start` ramps `VREF_SS` at about 6 V/ms (from its 0 → 90 % time of 197 µs for 1.2 V at the existing
divider-less node, `design/README.md`; ~125 nA into 20 pF). With the 1:1 divider gone, `Vref` follows `VREF_SS`:

| Event | `Vref` | Time | `Vout` (= 1.2·`Vref`) |
|---|---|---|---|
| Ramp start (EN) | 0 | 0 | 0 |
| Enters amplifier range | 1.20 V | ~200 µs | 1.44 V (**80 % of target**) |
| 90 % of target (R15 measure) | 1.35 V | ~225 µs | 1.62 V |
| Ramp end | 1.50 V | ~250 µs | 1.80 V |

(arithmetic from the stated slope; slope itself is simulated typical-corner pre-layout.) R15 window 100–500 µs:
~225 µs fits. Capacitor charge current on `Ceff` 6 µF is `6 µF × 7.2 V/ms` ≈ 43 mA (was ≈ 54 mA at 9 V/ms), so
peak current stays far under the R16 minimum trip of 0.70 A for the no-load case; the 500 mA-load case is
load-dominated and unchanged in kind.

**Finding: the amplifier input is outside its range for the first ~80 % of the ramp (0 → 1.2 V of `Vref`, 0 → 1.44 V
of `Vout`).** Today (0.6 V final) it is outside for the *whole* ramp. What the amplifier's output does there is not
known from this repo: the op-amp netlist is not vendored (`XEA … opamp_two_stage` is the sibling's), so no
simulated start-up record is claimed. The two bounding failures:

- `VC` low → duty ≈ 0, `Vout` does not follow the ramp; when `Vref` crosses 1.20 V the loop closes against a large error and the
  integrator (C1) drives `VC` up at its own rate: a step instead of a soft start. R15 (monotonic, overshoot ≤ 5 %) and
  the R16 limit are then at risk.
- `VC` high → full duty, overshoot to current limit.

Either fails R15 through the soft-start the spec fixes as an "analog ramp on the reference input". A duty clamp would
meet start-up but is **not** that mechanism (spec R15 / record 0001 §6) and is not proposed here.

## 7. Open items — back to the operator, none solved by relaxing a row

1. **Source of 1.50 V (scaling 1.25× from 1.20 V).** Two ways: a 1.5 V tap inside `gf180-bandgap` (a sibling change; its
   ±2 % then carries over unscaled only if the tap is a ratio inside its own loop), or a ×1.25 gain stage after it.
   The gain stage cannot be the adopted `error_amplifier` (its input would be 1.20 V, on the edge, and a second
   amplifier must not be sized by accident). Neither is decided here; R4's reference line and the R9 quiescent
   depend on it.
2. **`soft_start` follower at 1.50 V in / out**: it is a PMOS-input unity-gain OTA characterised only to 1.2 V with
   17 mV droop; its range at 1.5 V and its PVT offset spread are unmeasured.
3. **Amplifier behaviour below 1.20 V** (§6) and its offset row against the 15 mV input-referred allowance. This is
   a request to the op-amp side: defined, non-railing output (and no inversion) when both inputs are below 1.20 V,
   or an explicit statement that it is not defined, in which case the start-up mechanism needs a further decision here.

If items 1–3 cannot be met, this consumer cannot close R4 or R15 inside the op-amp's range, and the alternatives the
operator named stand: a re-sized input stage, or this consumer out of scope for that amplifier.

## 8. What follows (not done here)

- Post §5 on `2AMLogic/gf180-opamp#295` so Stage A can be re-run at 1.50 V.
- After the op-amp re-pin: `design/netlists/compensator.spice` `Rbot` 5 kΩ → 50 kΩ, remove `RREF1`/`RREF2` from
  `buck_top`, re-check `soft_start` at 1.5 V, then a single-corner start-up run from Vin = 0 (spec §0.4 timing) as a
  **new** `sim/` record, and the R4/R13 grids. Cross-check against #82 and #59/#60/#69 only then.
- `design/compensator.md`, DR-0004 and every existing `sim/` record stay as they are.
