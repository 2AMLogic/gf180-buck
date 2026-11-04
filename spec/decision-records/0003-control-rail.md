# 0003 — The 3.3 V control rail

- **Status**: Ratified on merge of the pull request that carries this record
  (issue #32, part of #21).
- **Date**: 2026-10-27
- **Resolves**: residual 3 of [`0001-ratify-target-spec.md`](0001-ratify-target-spec.md)
  §8 (the common supply-domain delta of its §7).
- **Amends**: nothing. **No ratified row changed**: no row of
  [`../target-spec.md`](../target-spec.md) is edited, and R9 is not relaxed
  (§4). Three `delta` strings in [`../../reuse.lock.json`](../../reuse.lock.json)
  are extended to point here (§5); no `sha`, `status` or `covers` field moves.
- **Claims made**: none. This record fixes an interface and does arithmetic on
  numbers already in the spec and in record 0001. No schematic, simulation or
  layout was run. `gf180-ldo` was read (its README spec table, `main` at
  `e95c13292b5b08e0c53672cd33bd6a5dd2f9608c`, 2026-10-27) to decide §3; nothing
  in it was copied or run.

## 1. Decision

The controller runs from a **dedicated linear regulator, 3.3 V nominal, fed
from VIN**. 5 V-class (thick-oxide) devices appear only where a node is VIN- or
SW-referenced (the high-side level shifter, the current-limit sense input, the
regulator's VIN-fed pass device, which drops 1.87 V at the 3.63 V ceiling, §2.2;
the drop is larger at lower rail voltages, see Errata E4), which is
where record 0001 §7 already puts the first two (pass device: see Errata E2). The power-gate drivers are
not loads on this rail (§2.3).

This record fixes the rail's **interface** only. The regulator is a separate
block, not designed or sized here.

## 2. The interface

### 2.1 What the regulator provides

| Item | Value | Source |
|---|---|---|
| Input | VIN pad, source side of the bond-wire model: 4.5 – 5.5 V (target), 2.97 – 3.63 V (fallback) | spec R1 (both tiers) |
| Output, target tier (Vin 4.5 – 5.5 V) | **2.97 – 3.63 V** at every sibling's supply pin, i.e. 3.3 V ±10 %. **Not guaranteed in the fallback tier**, see §2.2 | `gf180-bandgap` README, `gf180-opamp` / `gf180-comparator` scopes (record 0001 §7); `gf180-rcosc` is not a source, see Errata E1 |
| Output current | the sum of the adopted siblings' supply currents plus the buck's own digital and level-shifter control current. **Not yet known in full**: when written, only `gf180-rcosc`'s Iq (< 500 µA, at 48 MHz, not adopted) had been read. The three adopted siblings' rows were read afterward, see Errata E3 | record 0001 §7 |
| Source of the current | VIN only. A linear regulator draws its load current from VIN, so every mA on the rail is a mA at the VIN pad | linear-regulator topology |

The regulator's own accuracy, transient and noise contribution must fit
**inside** the siblings' ±10 %: the whole 2.97 – 3.63 V window is the budget
for regulator error, load regulation, line regulation and any switching
noise coupled onto the rail. This record does not split that window; the
regulator block's spec does. It must not assume the siblings tolerate more
than ±10 %: the bandgap's 3.3 V +10 % ceiling (3.63 V) is also the
3.3 V-flavor device limit that spec R2 (fallback) cites from DRM §14.1.2.

### 2.2 Headroom (arithmetic)

| Vin | Rail ceiling | Headroom for the pass device |
|---|---|---|
| 4.5 V (target min) | 3.63 V | 0.87 V above the ceiling, 1.20 V above 3.3 V nominal |
| 5.5 V (target max) | 3.63 V | 1.87 V dropped across the pass device at the ceiling; 2.20 V at nominal |

The low-end headroom (≥ 0.87 V) is the dropout the regulator must fit inside.
For scale, the sibling LDO's ratified dropout is < 300 mV at 50 mA (spec table,
Dropout row, `gf180-ldo`); this is an observation about feasibility, not an
adoption (§3).

**Fallback tier (Vin 2.97 – 3.63 V).** The rail window is the VIN window, so
the regulator has no headroom to regulate and the rail follows VIN with the
pass device fully on. **The siblings' 2.97 V floor cannot be guaranteed in this
tier.** At Vin 2.97 V the rail would need a 0 V drop across the pass device,
and any series device (an on-state Ron times the control current, plus its own
Iq path) drops a non-zero voltage at non-zero current, so the rail sits
strictly below 2.97 V at the bottom of the fallback VIN window. No series
regulator can meet that requirement, so this record does not pass it to the
regulator block as one. The 2.97 – 3.63 V interface of §2.1 is therefore fixed
for the target tier only; the fallback tier is **unresolved** and is carried as
open item 5 of §6. No ratified row changes: R1's fallback window and the
siblings' ranges are both as ratified, and the shortfall between them is named,
not closed, here.

### 2.3 What is not on this rail

The high-side and low-side **power-gate drivers** (and the VIN-referenced level
shifter's high side) run from VIN, not from the 3.3 V rail. Reasons, in
numbers already in the repo:

- A linear rail draws its current from VIN, so a mA of gate-drive current costs
  the same Vin × 1 mA at the VIN pad whether it is taken from the rail or from
  VIN directly. Routing it through the rail saves nothing at the pad; it adds
  the pass device's drop as loss and loads the regulator with gate-charge
  current pulses it would otherwise not have to supply.
- The low-side `Ron·W` baseline is measured at |Vgs| 3.6 – 5.0 V
  (`reuse.lock.json`, `low_side_power_switch`); 2.97 – 3.6 V is listed as not
  measured. Driving the gates from a 3.3 V rail would leave the adopted
  baseline.
- The high-side switch is VIN-referenced by construction (spec R3, no bootstrap).

Which supply each gate driver and the level shifter use, and its detailed
design, belongs to the schematic issues #33 and #34. This record only states
that this rail is **not** the gate-drive supply, so they do not size the
regulator for gate charge.

## 3. Rejected alternatives

1. **5 V-class devices throughout the controller (no regulator).** Rejected:
   the four adopted controller blocks are 3.3 V designs; their 5 V flavors are
   a stretch row in `gf180-bandgap` and an unopened row in `gf180-opamp`
   (record 0001 §7). Re-targeting them is sizing a second copy of each, which
   `CLAUDE.md` forbids.
2. **Siblings powered straight from VIN.** Rejected: VIN is 4.5 – 5.5 V against
   a 3.63 V ceiling, 0.87 – 1.87 V over it at the device limit.
3. **Adopting `gf180-ldo` as the rail.** Rejected as it stands: its ratified
   spec is a **3.3 V ±10 % input**, **1.8 V ±2 % fixed output**, 0 – 50 mA part
   (its README spec table). Its 5 V-input flavor is named there as a separate
   follow-on variant, not part of that design. It is the wrong input range and
   the wrong output voltage. Its topology and the lessons in its decision
   records are references for the rail regulator block, not a pin.
4. **A rail derived from Vout (1.8 V).** Rejected: 1.8 V is below the siblings'
   2.97 V minimum (Vout 1.8 V, spec §1 header; siblings' range, record 0001 §7).
5. **A switching or charge-pump auxiliary rail.** Rejected for now: it adds a
   second switching converter whose noise lands on the analog rail the
   bandgap and error amplifier use, for a control load not yet known to be
   large enough to justify it (§4). Re-open if the load turns out to be.

## 4. Quiescent-current accounting against R9

R9 (spec §1) already **includes** "controller and reference quiescent" in
Pin, graded at C-typ (Vin 5.0 V), at the VIN pad. Record 0001 §4.3 leaves
**≈ 100 mW** for the on-die power path, gate drive and controller at 500 mA
(Pout 0.90 W, total loss allowed 158.8 mW).

Because the rail is linear, every control-rail mA is drawn from VIN:

| Rail current (incl. regulator Iq) | Pin cost at Vin 5.0 V (R9 grading point) | Share of the ≈ 100 mW | Of which dropped in the regulator's pass device (5.0 − 3.3 V) |
|---|---|---|---|
| 1 mA | 5.0 mW | 5 % | 1.7 mW |
| 2 mA | 10.0 mW | 10 % | 3.4 mW |
| 5 mA | 25.0 mW | 25 % | 8.5 mW |

At Vin 5.5 V the cost is 5.5 mW per mA. Three consequences:

- The linear rail is more expensive than the rail's own power: a 3.3 V load of
  1 mA is 3.3 mW at the rail but 5.0 mW at the VIN pad, 1.7 mW of it lost in the
  pass device.
- **R9 headroom is not changed by this decision** and no row is relaxed. The
  existing ≈ 100 mW already includes controller quiescent; this record adds the
  conversion factor (Vin per mA) that the allocation must be read with.
- **Whether the rail load fits is not established.** The siblings' quiescent
  currents were not read here (see Errata E3; record 0001 §7 notes the bandgap load row is
  `TBD` and the op-amp GBW check is outstanding). The follow-up is to read each
  adopted sibling's supply current at 3.3 V and fill the first column; if the
  total pushes R9 out of reach, the response is a new record that changes R9
  with its reason (record 0001 §8 item 1), not a silent allocation here.

This is not a PO-level choice: it does not change any ratified row or R9's
headroom, so it is not routed through `loom-daemon operator-decision apply`.
If the accounting above is later found to force an R9 change, that change
is.

## 5. `reuse.lock.json` deltas

The `delta` text of the three siblings whose delta was "supply domain" is
extended to say the rail is decided here and what remains. No `sha`, `status`
or `covers` changes. `oscillator` (delta is frequency / temperature / spread,
not the rail) and the two power-switch entries (gate drive, not controller rail;
see §2.3) are not touched.

## 6. Open items this record leaves, by name

1. **The regulator block** (output current, accuracy split inside ±10 %,
   transient on a switching die, start-up). Not designed here; it needs its own
   issue. Interface in §2.1 – §2.2. Carry from Errata E4: its Iq and the
   comparator instance count can move the controller draw from sub-mA to mA,
   about 5 mW per mA at Vin 5.0 V.
2. **Start-up ordering.** The adopted bandgap is a 3.3 V part and the regulator
   needs a reference, so the rail and the reference have a mutual dependency
   at power-up. Not resolved here; it is a requirement on the regulator block.
3. **Sibling supply currents** (§4), needed to close the quiescent accounting.
   Partly closed by Errata E3: the three adopted siblings' rows are read.
   Still open: instance counts, the comparator's dynamic current (clock rate
   TBD in the sibling), the buck's own digital and level-shifter current, the
   regulator's Iq, and the oscillator (`gf180-rcosc` is `kept`, not adopted).
4. **Gate-driver and level-shifter supply** (§2.3): issues #33, #34.
5. **Fallback-tier control rail** (§2.2). A series regulator cannot hold the
   siblings' 2.97 V floor at Vin 2.97 V. Resolving it needs one of: a sibling
   derate or characterization below 2.97 V, or a product-owner call on the
   fallback tier. If that forces a ratified-row change, it is routed per the
   issue's AC4, not made here.

## Errata (2026-11-01, issue #45)

Text and citation corrections only. The 3.3 V decision (§1), every ratified
row of [`../target-spec.md`](../target-spec.md), and R9 are unchanged. In-place
edits are limited to §1, the two §2.1 cells and §6 item 3, each pointing here.
Sibling values below were read from each file at the commit pinned in
[`../../reuse.lock.json`](../../reuse.lock.json).

**E1. §2.1 cited `gf180-rcosc` for the 2.97 – 3.63 V window.** Its ratified
Supply row reads "3.3 V core (3.0–3.6 V)" (`README.md` at
`6e4c395198d28df57ecc1265f73ff8044e5c32ba`), which is narrower than 2.97 – 3.63 V.
It is `kept`, not adopted, so it does not set the interface the adopted
siblings do. It is removed from the source cell. The window rests on:
`gf180-bandgap` Supply "3.3 V ±10%" and line regulation "2.97–3.63 V"
(`README.md` @ `c68ccc6b0423344568df9506423ba2695f8b1b9b`); `gf180-opamp`
"3.3 V ±10% → 2.97–3.63 V" (`spec/target-spec.md` @
`cda7ff5ac3232049588e9315a0e5224433e18bc2`); `gf180-comparator` Supply "3.3 V
±10%" (`README.md` @ `80402c061b639ed64289f8806f73456fe1abc1ea`). If an
oscillator is later taken from rcosc, its 3.0 – 3.6 V row needs a derate or
re-characterization against this rail; that is not decided here.

**E2. §1 omitted the regulator pass device from the thick-oxide list.** The
pass device is VIN-fed and drops up to 1.87 V at the 3.63 V ceiling (§2.2), so
it is a VIN-referenced node like the others. §1 now lists it. It is a device
class consequence of §2.2 (record 0001's DRM-based device-class verification);
no device is sized here.

**E3. §4 / open item 3 treated the sibling supply currents as unread.** Read
at the pinned commits (values are the siblings' own, not measured here):

| Sibling | Value | Conditions / status | Source |
|---|---|---|---|
| `gf180-bandgap` | Iq < 50 µA (stretch < 20 µA) | ratified target row; binds at FF / 125 °C / 3.63 V | `README.md` @ `c68ccc6` |
| `gf180-opamp` | ≤ 350 µW worst case; 80.70 µA nominal at 3.3 V; worst measured 310.98 µW at FF / −40 °C / 3.63 V (≈ 85.7 µA) | ratified target, measured PASS at 45/45 PVT points, typical passives | `spec/target-spec.md` @ `cda7ff5`, Quiescent power row |
| `gf180-comparator` | 29.7 µA worst-corner static current (27.7 – 29.7 µA across the grid; 28.5 µA mean, ≈ 93.9 µW nominal) | static power only; average power is not fully scored, clock rate TBD in the sibling; the sibling's ratified Supply / power row is a ≤ 1 mW average-power ceiling at a clock rate still TBD (DR-0006 proposed, not ratified, at `80402c0`), so it cannot yet be scored; the worst measured static corner is used instead, and the ceiling-based figure is given alongside (Errata E4) | `README.md` @ `80402c0`, Supply / power row (mean, and the ≤ 1 mW ceiling); `spec/evidence-ledger.md` @ `80402c0`, Supply / power (range) |

Arithmetic at one instance each, taking the opamp ceiling 350 µW / 3.63 V ≈
96.4 µA: 50 + 96.4 + 29.7 ≈ 176 µA with the comparator at its worst measured static corner (E4: was 28.5 µA mean, ≈ 175 µA), i.e. ≈ 0.88 mW at the VIN pad at Vin 5.0 V
(5.0 mW per mA, §4), ≈ 0.9 % of the ≈ 100 mW allowance. With the comparator's ratified ≤ 1 mW ceiling converted the way the
opamp's is (1 mW / 3.63 V ≈ 275.5 µA), the conservative sum is 50 + 96.4 + 275.5 ≈ 422 µA, ≈ 2.1 mW, ≈ 2.1 % of the allowance (E4). Adding the rcosc bound of 500 µA, if its topology were used, gives
≈ 0.7 mA, ≈ 3.4 mW (≈ 0.9 mA, ≈ 4.6 mW on the conservative comparator figure). These are bounds from sibling rows, not a closed
accounting: instance counts (PWM and current-limit may need separate
comparators), the comparator's dynamic current, the buck's digital and
level-shifter current, and the regulator's own Iq are not in them, so open item 3
stays open with those named (see also E4 for the carry to the regulator block). The §4 first-column rows (1, 2, 5 mA) remain
valid as a scale; the sibling subtotal sits below the 1 mA row.

## Errata (2026-11-04, issue #103)

Text and accounting corrections from the EE and market key reviews of #46
(`ratify:key` comments). The 3.3 V decision (§1), every ratified row of
[`../target-spec.md`](../target-spec.md), and R9 are unchanged. In-place edits
are limited to §1, the §4 third bullet, §6 item 1, and the E3 comparator row, sum and
closing sentence, each pointing here.

**E4. Pass-device drop, bound convention, carry.**

1. *§1 pass-device wording.* "Drops up to 1.87 V" was not a maximum. §2.2 gives
   1.87 V only at the 3.63 V ceiling (5.5 − 3.63). At 3.3 V nominal it is 2.20 V
   (5.5 − 3.3) and at the 2.97 V rail floor ≈ 2.53 V (5.5 − 2.97), all at Vin
   5.5 V. §1 now states the "at the 3.63 V ceiling" condition, as E2 does. The
   thick-oxide reason is that the pass device is VIN-referenced (its terminal
   potentials reach Vin), not the size of the drop.
2. *Bound convention.* E3 mixed conventions: the bandgap and opamp terms are
   ratified ceilings, the comparator term was the measured mean (28.5 µA). The
   comparator does have a ratified ceiling, but it is a power row: ≤ 1 mW
   average (stretch ≤ 500 µW) at a clock rate still TBD (`README.md` of
   `gf180-comparator` at the pinned `80402c0`, ratified via its DR-0002; DR-0006,
   which would set the clock, is proposed, not ratified). It cannot be scored
   until the clock is set, and 29.7 µA is a static-only figure (clock-low
   window), not a bound on the comparator's supply current. E3 therefore keeps
   the worst measured grid corner, 29.7 µA (range 27.7 – 29.7 µA,
   `spec/evidence-ledger.md` at `80402c0`), as the measured static value, and
   says so: the sum is two ratified ceilings plus one measured static worst
   case, not one convention, and dynamic current is excluded. Sum: 50 + 96.4 +
   29.7 ≈ 176 µA, ≈ 0.88 mW at Vin 5.0 V (5.0 mW per mA). Conservative figure,
   converting the comparator's 1 mW ceiling as E3 does the opamp's (1 mW /
   3.63 V ≈ 275.5 µA): ≈ 422 µA, ≈ 2.1 mW, ≈ 2.1 % of the ≈ 100 mW allowance.
   Both sit below the §4 1 mA row. They are bounds from sibling rows, not a
   closed accounting.
3. *§4 pointer.* The third bullet now says "see Errata E3".
4. *Carry to the regulator-block issue (§6 item 1).* The regulator's own Iq and
   the comparator instance count (PWM and current-limit may need separate
   comparators) could move the controller draw from sub-mA to mA. At that scale
   R9 accounting matters: ≈ 5 mW per mA at Vin 5.0 V (5.5 mW at 5.5 V), each mA
   being ≈ 5 % of the ≈ 100 mW allowance. The regulator-block issue must carry
   this; it is not opened here.
