# 0001 — Ratify the target specification

- **Status**: Ratified on merge of the pull request that carries this record
  (issue #2). Before that merge it is a proposal.
- **Date**: 2026-10-17
- **Ratifies**: [`../target-spec.md`](../target-spec.md)
- **Supersedes**: the README's DRAFT target table. No number in that table is
  changed (§2).
- **Claims made**: none. This record sets targets, a method, and a set of
  adopt-or-keep decisions. It runs no schematic, simulation or layout; the only
  tool runs behind it are the PDK-document reads and the one `klt drc` probe in
  §5.2, each described where it is used.

## 1. Decision

The target spec is ratified as written, with these load-bearing choices, each
argued below:

1. **Power devices**: high-side `pfet_06v0`, low-side `nfet_06v0` (§3).
2. **Control**: voltage-mode PWM, type-III compensation, forced PWM at all
   loads, fixed frequency; stability shown by an averaged-model loop gain **and**
   a switched load step, cross-checked (§6).
3. **External parts**: three fixed sets P-T / P-F / P-S (spec §0.2), and every
   efficiency number excludes inductor core loss (§4.3).
4. **Electromigration**: budgeted at 125 °C, unidirectional column, from DRM
   Tables 14.3 / 14.4, with a 0.8 design factor, **before any layout** (§5).
5. **Reuse**: only the low-side switch work is adopted as it stands. The
   controller blocks are adopted *at the interface* with a named supply-domain
   delta; the oscillator is kept as a re-target, not adopted (§7).

## 2. Departures from the README draft

No number in the README's table moved. What this record adds, each as a row the
draft did not have:

| Added row | Why it was needed |
|---|---|
| R2 absolute maximum, R3 device flavor | The issue asks for "absolute-maximum margin including switch-node overshoot" and the flavor of each switch |
| R4 output accuracy | The issue asks for accuracy over line, load and temperature |
| R6 light-load mode | The issue asks for forced PWM or pulse skipping |
| R7 frequency tolerance (±15 %) | "2 MHz" needs a min/typ/max; ±15 % is what a single-point trimmed relaxation oscillator can hold (§7) |
| R8 inductor ripple | Derived; it is the number the current limit and the EM budget need |
| R10 efficiency at full load, all corners | Peak efficiency is graded at one point (the README's wording); the corner behaviour is `rep` until sizing evidence sets a floor (§8) |
| R13 stability margins, R14 dead time, R16 current-limit trip window | The issue asks for them with trip points |
| R15 soft-start time | Protection "with trip points" |
| R18 EM, R19 package | Required by the issue and `CLAUDE.md` |

The README's fallback column (3.3 V, 200 mA, 1 MHz) and stretch column
(1.0 – 3.3 V programmable, 1 A, 4 MHz) are taken as the fallback and stretch
tiers; each is specified row by row rather than by reference to the target.

## 3. Switch devices

**High-side: `pfet_06v0`. Low-side: `nfet_06v0`.**

The alternative, an NMOS high-side switch, was rejected: its gate must be driven
above VIN to stay on, and VIN + 5 V = 10 V at nominal is above the 6.0 V
thick-oxide ceiling `gf180-gate-driver` records (its `gate-driver.md` §2.3), so
it needs either a stacked-device bootstrap or a separate boosted rail. A PMOS
high-side switch is driven by pulling its gate between ground and VIN, inside
the rating, with no bootstrap and no extra rail.

The price is area. The sibling's recorded `Ron·W` at `tt`, 27 °C, 5.0 V gate
drive is **2.22 Ω·mm** for `nfet_06v0` and **7.14 Ω·mm** for `pfet_06v0`
(`gf180-gate-driver` `spec/low-side-power-switch.md` §2.1, record
`sim/low-side-power-switch/records/20260818-011754-03afe04.md` in that repo):
a 3.2× penalty for the PMOS. This is the largest single driver of the
efficiency risk in §4.3 and the reason R9 is the row most likely to be revisited.

**Fallback tier** keeps the 6 V flavors. The 3.3 V flavors (`*_03v3`) would have
lower `Ron·W` at a 3.3 V gate drive, but Vin max in that tier is 3.63 V, which
is already 3.3 V + 10 %, the limit DRM §14.1.2 gives for the 3.3 V devices; the
switch node rings above VIN, so there would be no overshoot margin. The cost is
that the sibling's `Ron·W` table stops at |Vgs| = 3.6 V, so the 2.97 – 3.6 V
part of the fallback tier is **not covered** by the adopted baseline (§7).

**Supply-limit statement.** DRM §14.1.2: the nominal supply for the 6 V devices
is 5 V or 6 V depending on process option, with a 10 % overshoot tolerance.
This spec takes 5.0 V ±10 % as VIN and treats **6.0 V** as the ceiling for every
terminal-to-terminal voltage of a thick-oxide device, the convention the
sibling records. R2 therefore requires SW and every Vgs / Vds to stay ≤ 6.0 V
with the edge resolved, including bond-wire ringing. That leaves 0.5 V (9 %) at
Vin max for overshoot, which is thin, and is called out as a residual (§8).

## 4. Accuracy, efficiency, ripple and transient arithmetic

All of this is arithmetic on the spec's own numbers. It is an expectation,
labelled `exp` in the spec, never a result.

### 4.1 Output voltage accuracy (R4)

Untrimmed ±4 % at target: reference ±2 % + divider ratio ±1 % + error-amp input
offset and finite DC gain ±1 %, summed linearly (a root-sum-square would give
2.4 %; the linear sum is used because the three terms are not shown to be
independent). The ±2 % reference term is the sibling `gf180-bandgap`'s untrimmed
target (3σ, mismatch Monte Carlo N ≥ 300 + process corners, −40…125 °C). The
divider and amplifier terms are allocations, not measured values. A ±2 %
output needs the reference trim (bandgap stretch ±0.5 % trimmed), which this
spec does not open. Fallback is ±5 % (one extra percent for lower DC loop gain
at 1 MHz); stretch is ±4 % untrimmed or ±2 % trimmed.

### 4.2 Inductor ripple and the current limit (R8, R16)

ΔIL = Vout(1 − Vout/Vin) / (L·f). Target tier, P-T:

| Case | Vin | L | f | ΔIL |
|---|---|---|---|---|
| min | 4.5 V | 3.96 µH | 2.3 MHz | 0.119 A |
| typ | 5.0 V | 3.3 µH | 2.0 MHz | 0.175 A |
| max | 5.5 V | 2.64 µH | 1.7 MHz | **0.270 A** |

Peak inductor current at 500 mA and the max ripple is 0.5 + 0.135 = **0.635 A**.
R16's minimum trip is 0.70 A (10 % above it). `Ron`-sense current limits inherit
`Ron`'s PVT window; the sibling's `low-side-power-switch.md` §4.1 (ratified by its DR-0010) records a 3 : 1 window for the
same structure, so R16's maximum is 2.1 A. The trip is a **die-protection
threshold, not a precision limit**, and a precision limit would need a ratioed
sense FET and its own record.

### 4.3 Efficiency (R9, R10)

At 500 mA and 1.8 V, Pout = 0.90 W; the 85 % target allows total loss
Pout/0.85 − Pout = **158.8 mW**. Fixed charges taken out of it before any
silicon is drawn:

| Item | Arithmetic | Loss |
|---|---|---|
| Inductor DCR | 0.5² × 0.100 Ω | 25 mW |
| Bond wires, VIN (2 wires, 0.05 Ω) | 0.5² × D(0.36) × 0.05 | 4.5 mW |
| Bond wires, SW (2 wires, 0.05 Ω) | 0.5² × 0.05 | 12.5 mW |
| Bond wires, GND (2 wires, 0.05 Ω) | 0.5² × (1−D)(0.64) × 0.05 | 8.0 mW |
| Dead-time diode conduction, max (R14) | 0.7 V × 0.5 A × 2 × 6 ns × 2 MHz | 8.4 mW |
| **Subtotal outside the die's switches** | | **≈ 58.4 mW** |
| **Left for the on-die power path, gate drive and controller** | 158.8 − 58.4 | **≈ 100 mW** |

The package model (§0.3 of the spec) alone is ~25 mW, 2.8 % of Pout: it is a
first-order term and not a rounding error, which is why the bond-wire model is
pinned in the spec rather than left to the layout.

Whether ≈ 100 mW is enough is **not** established. As feasibility arithmetic
only (this is not sizing): at a total on-die switch resistance budget of
0.15 Ω the conduction loss at 500 mA is 0.5² × 0.15 = 37.5 mW, which would need
about 2.22/0.15 = 15 mm of `nfet_06v0` and 7.14/0.15 = 48 mm of `pfet_06v0`
at `tt`/27 °C (sibling `Ron·W`), before metal resistance, and `Ron·W` at 125 °C
is 1.4× the 27 °C figure (`tt`, 5.0 V gate drive: 3.09 vs 2.22 Ω·mm, 1.4×; 2.4× across the sibling's full 15-point grid). Gate
charge for that much width at 2 MHz is the other large term and the sibling
lists it as unmeasured (its §6 item 5). **R9 is therefore the row most likely
to need a new decision record**; the spec does not hide that, it states the
85 % as the target and records the loss allocation behind it.

R10 (efficiency at full load across all corners) is `rep` with no floor because
setting one needs the sizing the issue puts out of scope. §8 names it.

### 4.4 Ripple and transient (R11, R12)

Output ripple p-p ≈ ΔIL/(8·f·Ceff) + ΔIL·ESR (ESL term: 0.5 nH × 1.4 A/µs
= 0.7 mV, negligible). At the worst P-T case (ΔIL 0.270 A, f 1.7 MHz, Ceff
4.7 µF, ESR 10 mΩ) that is 4.2 + 2.7 = **6.9 mV**, a factor 2.6 under the 18 mV
bound: ripple is not the hard row. The 20 MHz first-order filter in R11 removes
switching-edge spikes while keeping both terms. The load-step first-order
expectation ΔV ≈ ΔI/(2π·fc·Ceff) = 0.40/(2π × 200 kHz × 6 µF) = 53 mV against a
90 mV bound; the energy-limited overshoot on unloading is
√(1.8² + 3.3 µH × (0.45² − 0.05²)/6 µF) − 1.8 ≈ 30 mV. These are expectations
that the cross-check in §6 will test; they are not evidence.

## 5. Electromigration budget and the thick-metal rules

### 5.1 Method (recorded before any layout)

Source: PDK Design Manual, `gf180mcu-pdk.readthedocs.io`
[§14.2 Electro-migration](https://gf180mcu-pdk.readthedocs.io/en/latest/physical_verification/design_manual/drm_14_2.html),
re-read 2026-10-17. The rules aim at T₀.₁ > 100 000 h at 85 °C junction
temperature. **Unidirectional** current is "the steady value of direct current
or the time average value of current always pulsed in the same direction",
which is what an inductor-fed switch carries, so the unidirectional column is
used. §14.1.1 gives −40…125 °C as the design range, and Tables 14.3 and 14.4
stop at 125 °C; §14.2.2's temperature formula is stated only below 110 °C, so
there is **no published allowance above 125 °C**. The budget is therefore taken
at 125 °C.

| Quantity (DRM) | Limit at 125 °C, unidirectional | × 0.8 design factor |
|---|---|---|
| Table 14.3, Metal1 – Metal(top−1) | 0.67 mA/µm | 0.536 mA/µm |
| Table 14.3, MetalTop 30 kÅ | **5.37 mA/µm** | **4.296 mA/µm** |
| Table 14.3, MetalTop 11 kÅ | 1.50 mA/µm | 1.20 mA/µm |
| Table 14.4, Via1…Via5 (0.26 µm) | 0.18 mA | 0.144 mA |
| Table 14.4, COMP contact | 0.18 mA | 0.144 mA |

The 0.8 factor is this record's choice, not the manual's. It absorbs slot
width (§5.3), edge crowding at via arrays, and the fact that the limits are
for a drawn width. It is stricter than the manual; it is not a relaxation.

**Which current.** The time-average current per net, with duty bounds taken from
the tier's own envelope (a loss allowance on top of the ideal D = Vout/Vin):

| Net | Current | Basis |
|---|---|---|
| VOUT, SW and the inductor path | Iout | carries the whole inductor current |
| VIN → high-side switch | D_max × Iout | target: D = 1.8/4.5 = 0.40, bounded at **0.45** |
| Low-side switch → GND | (1 − D_min) × Iout | target: 1 − 1.8/5.5 = 0.673, bounded at **0.70** |

(Fallback: 0.65 and 0.55; stretch, with Vout up to 3.3 V: 0.80 and 0.85.) Forced
PWM lets the inductor current reverse at light load; the average still does not
exceed Iout, so the unidirectional budget at Iout is the conservative choice.

**Required metal per net.** Width = current / (limit × 0.8), **net of slot
width**; cuts = ceil(current / (0.144 mA)) per via level.

| Net | Iout | MetalTop 30 kÅ | Metal1 or Metal2 | Cuts per via or contact level |
|---|---|---|---|---|
| **Target, 500 mA** | | | | |
| SW, VOUT | 0.500 A | 116.4 µm | 932.8 µm | 3 473 |
| VIN → HS | 0.225 A | 52.4 µm | 419.8 µm | 1 563 |
| LS → GND | 0.350 A | 81.5 µm | 653.0 µm | 2 431 |
| **Fallback, 200 mA** | | | | |
| SW, VOUT | 0.200 A | 46.6 µm | 373.1 µm | 1 389 |
| VIN → HS | 0.130 A | 30.3 µm | 242.5 µm | 903 |
| LS → GND | 0.110 A | 25.6 µm | 205.2 µm | 764 |
| **Stretch, 1 A** | | | | |
| SW, VOUT | 1.000 A | 232.8 µm | 1 865.7 µm | 6 945 |
| VIN → HS | 0.800 A | 186.2 µm | 1 492.5 µm | 5 556 |
| LS → GND | 0.850 A | 197.9 µm | 1 585.8 µm | 5 903 |

For the fallback tier on the 11 kÅ option: 0.2 A / (1.2 mA/µm) = 167 µm at SW.

**What this means for the layout** (stated now so the layout does not
rediscover it):

1. The 30 kÅ stack is the PDK's variant `gf180mcuA`, which the PDK deck defines
   as **3LM** (`options.rb`: `gf180mcuA => metal_top 30K, metal_level 3LM`): two
   ordinary metals (Metal1, Metal2) under a thick top. In the deck the top
   metal is the Metal3 layer (42/0) and the top via is Via2. The intermediate
   metals are the per-layer worst case (0.67 mA/µm): at 500 mA a single
   intermediate layer needs ~933 µm of width, so current must be collected as a
   distributed strap over the device array and taken to MetalTop, not routed as
   one wire.
2. Every power strap on MetalTop at target is ≥ 52 µm wide, and the SW / VOUT
   strap is ≥ 116 µm. All are wider than the **30 µm** slotting threshold
   (§5.3), so the thick top metal **will be slotted** and the EM width is the
   metal between slots.
3. Via arrays must be drawn over the whole device array, not concentrated at one
   tap, or the per-cut limit is violated locally though the global count passes.
   MT30.8 requires at least 2 × 2 top vias wherever a via lands on 3 µm metal.
4. `klt pdk em-limits --pdk gf180mcuA` reports **Metal3 = 0.67 mA/µm (DISAGREE:
   0.67, 5.37)**: the shipped tech LEFs disagree and the tool returns the
   conservative value. Used blindly it would size the thick top metal 8× too
   wide. The authoritative number for this repo is DRM Table 14.3's 5.37; the
   tool's output is not an input to R18. (The disagreement is the subject of the
   closed `klayout-tools` issue #1215; nothing new is filed for it.)
5. **Power-path extraction and checking in `klt`**: `klt power <gds> <spec>`
   extracts named power nets into a resistive network, solves static IR drop
   from pads and a current model, and emits a per-net EM verdict "citing each
   stackup / vias role's own declared limit" (`klt power --help`). The limits
   are supplied by the spec file the caller writes, so R18 above is what goes
   in it, not the tool's tech-LEF data; `klt pex --distributed-rc` gives the
   extracted netlist for post-layout efficiency. Neither has been run: there
   is no layout.

### 5.2 Thick-MetalTop rules and what `klt` enforces

Rules come from DRM §7.15 (MetalTop), §7.16 (3.0 µm Thick MetalTop Option),
§13.3 (dummy metal), §14.6 (stress relief / slotting), re-read 2026-10-17, and
from the PDK's own KLayout deck (`libs.tech/klayout/tech/drc/rule_decks/`
`metaltop_30k.rb`, `mslot.rb`, `density.rb`, open_pdks
`f6eeac7dad085ffcc829ccfd721f7b4ce39edcf7`).

**How the verdict was established.** Two ways, stated per rule:
*(deck)* by reading the deck, and *(probe)* by running it on a scratch GDS. The
probe is a 4-shape GDS on the 30K variant's top metal (42/0): a 1.0 µm wide
line; two 5 µm lines 1.0 µm apart; a 40 × 200 µm unslotted plate; and a single
Via2 under a 3 µm square of metal. It was written to `/tmp` (scratch, not
committed). It ran on this host's KLayout 0.28.16, one single-unit run each:
`klt drc --deck gf180mcu --pdk gf180mcuA` (the curated engine) and the PDK's own
`gf180mcu.drc` with `-rd variant=gf180mcuA -rd run_mode=flat`.

| Rule | Requirement | `klt drc` curated engine | PDK-native deck run through `klayout -b` |
|---|---|---|---|
| MT30.1a | min width 1.8 µm | **not enforced** (probe: 0 violations; deck rules list: only MT.1) | enforced (probe: flagged) |
| MT30.1b | 2.2 µm min width for a line > 1 000 µm | **not enforced** (deck rules list) | coded (deck); not exercised by the probe |
| MT30.2 | min space 1.8 µm | **not enforced** (probe: 0 violations) | enforced (probe: flagged) |
| MT30.3, MT30.4 | corner and single-line separation 1.8 µm | **not enforced** | enforced (probe: flagged; the deck codes both as the same check as MT30.2) |
| MT30.5, MT30.6 | via enclosure 0.12 µm; end-of-line 0.25 µm | **not enforced** | coded (deck); not exercised |
| MT30.7 | MetalTop coverage over the **entire die** > 30 % | **not enforced** | coded in `density.rb` (deck); die-level, so it cannot be satisfied or judged on a block alone |
| MT30.8 (a, b) | no single top via on thick metal; at least 2 × 2 via array | **not enforced** | coded (deck); the single-via shape in the probe was **not** flagged, but the probe had no lower-metal shape under it, so this is inconclusive, not a pass |
| MT.2b, MT.4 | wide-metal spacing; min area (**6 kÅ / 9 kÅ / 11 kÅ options only**, not 30 kÅ) | **not enforced** (deck rules list: MT.1, MT.2a only) | n/a for the 30 kÅ variant |
| Wide-metal spacing for 30 kÅ | none separate: MT30.2's 1.8 µm applies to all widths | see MT30.2 | see MT30.2 |
| MSLOT.1 | metal wider than 30 µm must be slotted | **not enforced** (probe: unslotted 40 µm plate, 0 violations) | **cannot run on this variant**: `mslot.rb` references `metal4_drawn`, which does not exist in the 3LM variant (`NameError`, deck aborts) |
| MSLOT.2 – .8, .10 | slot width ≥ 2 µm, length 10 – 250 µm, space 10 – 30 µm, slot-to-edge ≥ 10 µm, via-to-slot ≥ 0.2 µm, no slot mark on a hole | **not enforced** | coded (deck) but not runnable, as above |
| MSLOT.6 | multiple slots spanning the width are staggered | **not enforced** | **not coded anywhere**: DRM Appendix B lists it ("14.7.3.6") as a rule not coded |
| DRM §14.6.2 | no active circuitry within 400 µm of a die corner; 45° turns for metal and slots within 400 µm; metal to die corner ≥ 300 µm | **not enforced** | not searched for in the native deck (not in the Appendix B list) |
| DM.* (§13.3) | dummy metal fill (2 × 2 µm, 2.0 µm spacing for the thick top metal) | **not enforced** | DM.2a, DM.9, DM.10 are listed in DRM Appendix B as not coded; the rest of DM.* was not checked in the native deck |
| `klt` EM check | per-net current density vs. a limit | `klt power` exists and consumes a caller-supplied limit (§5.1); there is no deck-supplied thick-metal EM rule | n/a |

Two further observations, both from the probe runs, not interpretations:

- With the PDK-native deck on KLayout 0.28.16, the full deck aborts at
  `undefined method evaluate_nets`, and the `metaltop_30k` rule family produces
  its findings and then aborts at report finalisation (`Cannot call non-const
  method on a const reference in RdbCategory::each_sub_category`). The rule
  results above are from that partial output; the run exited non-zero. A newer
  KLayout was not available on this host (host tools are not changed here).
- `klt drc --engine klayout --pdk gf180mcuA` reports "no PDK-native klayout DRC
  deck script found" without `--deck-file`; with `--deck-file` it ended
  `coverage_unknown` with 0 violations.

**Conclusion for the spec.** DRC signoff for this block cannot be "`klt drc`
with the curated deck, zero violations": that deck does not check MT30.* at all
and reports clean. R21 therefore requires the PDK-native 30 kÅ rule family
(`metaltop_30k`, `density`, and a working `mslot`) as the signoff deck, run on
a KLayout that supports it, with a negative control. Until that exists the
signoff row is unmet by construction.

**Issues filed (friction protocol).** Both are generic tool gaps, with no design
detail:

- [`2AMLogic/klayout-tools#3796`](https://github.com/2AMLogic/klayout-tools/issues/3796)
  — the curated gf180mcu deck enforces no thick-MetalTop, wide-metal or slotting
  rule and reports clean.
- Comment on the existing, open
  [`2AMLogic/klayout-tools#2351`](https://github.com/2AMLogic/klayout-tools/issues/2351#issuecomment-6241701714)
  — `--engine klayout` cannot resolve the gf180mcu runset; and the three
  native-deck failures above. A comment, not a new issue, because that tracker
  item already covers the resolution gap.

### 5.3 Slotting and the EM width

DRM §14.6.1: metal lines wider than 30 µm should be slotted, with slots parallel
to the current flow; §14.6.3 MSLOT.1 – .10 give the geometry (slot width ≥ 2 µm,
length 10 – 250 µm, slot space 10 – 30 µm, slot-to-edge ≥ 10 µm, no slot within
0.2 µm of a via, slot mark layers `Metal*_Slot` / `MetalTop_Slot`, no physical
holes drawn). The manual does not say whether Table 14.3's "drawn width" counts
the slot area. This record takes the conservative reading: **EM width is the
metal remaining between slots** (worst case, 2 µm slots at 10 µm spacing remove
2/12 = 17 % of the width, which is inside the 0.8 factor's 25 % allowance). That
is an interpretation; it should be confirmed with the foundry before tape-out
and is a residual (§8).

### 5.4 Metal option

30 kÅ MetalTop is the target. The thinner option is the fallback tier's
alternative, argued only on availability: 11 kÅ at 125 °C is 1.50 mA/µm against
5.37 mA/µm, so the same current needs 3.6× the width. Per the PDK deck, 11 kÅ is
variants B (4LM) and D (5LM). The choice is shuttle-level, not per-block.

## 6. Control architecture and stability method

**Voltage-mode PWM, type-III compensation, forced PWM, fixed frequency.**

- *Why not current mode.* Peak-current-mode control needs a current sense on the
  power switch, and the sibling's ratioed sense FET is explicitly **not
  ratified** (its `low-side-power-switch.md` §4.1, ratified by its DR-0010). The only ratified structure is `Ron`-sense, a
  3 : 1 PVT-dependent threshold, which is a fine over-current trip and a poor
  control signal. Voltage mode needs no current sense in the loop.
- *Why not pulse skipping.* A pulse-skipping or burst mode adds a mode boundary
  and a second stability regime to show. The headline row (R9) is a peak
  efficiency, not a light-load one. It is not rejected for ever; adding it is a
  new decision record.
- *Compensation.* Type III (two poles, two zeros) places the zero pair near the
  LC resonance. For P-T: f₀ = 1/(2π√(L·C)) = 1/(2π√(3.3 µH × 6 µF)) = 35.8 kHz;
  crossover is bounded to 100 – 250 kHz (R13), i.e. f/20 – f/8 at 2 MHz, with
  f/6.8 at the low end of the frequency tolerance.
- *No digital partition.* This design adds no synthesized digital block: the PWM
  latch, dead-time non-overlap and gate-drive stages are analog-style cells, and
  soft start is an **analog reference ramp, not a counter**. The manifest `kind`
  that issue #3 sets therefore stays `analog`; nothing here makes it
  `mixed-signal`. If a later decision record introduces a counter or divider, it
  must say so and #3's manifest changes with it.

**Stability evidence, all three required (spec R13):** (a) AC loop gain from an
**averaged** model; (b) a switched `.tran` load step (R12); (c) a cross-check:
the switched step's peak deviation and recovery time within **±30 %** of the
averaged model's prediction. ±30 % is a chosen tolerance: tight enough that a
wrong averaged model fails it, loose enough to survive the switching-ripple
content a small-signal model omits. Margins (PM ≥ 45°, GM ≥ 10 dB) are held at
the external-part tolerance corners, not only at nominal.

**Run length, step, steady state** are fixed once in the spec §0.4 and restated
in every result record.

## 7. Adopt-or-keep: same-PDK siblings

Each sibling was read on its `main` on 2026-10-17 (commit pinned in
[`reuse.lock.json`](../../reuse.lock.json)). What was read is stated per row;
none is modified by this issue. "Adopted" here means **taken by pinned
reference** and not re-designed here; where a delta remains, it is named and
becomes the input to a later record rather than being resolved by sizing a
second copy.

**The common delta — supply domain.** The target tier has Vin 4.5 – 5.5 V. The
controller siblings are **3.3 V ±10 %** designs (`gf180-bandgap` README; the
comparator and op-amp scopes; `gf180-rcosc` README). The fallback tier's Vin,
2.97 – 3.63 V, is exactly their range. So at target a **3.3 V control rail
derived from VIN** is required, and the high-side gate drive and the
current-limit sense see up to 5.5 V and up to 6.0 V respectively. No sibling in
the issue's list provides that rail; a `gf180-ldo` repo exists in the same
organisation and was **not read** here. Choosing and sizing the rail is a
follow-up decision, not made here (§8), and it is the reason three of the four
controller blocks are "adopted at the interface" rather than plain "adopted".

| Sibling (pin) | What it provides | Decision | What it covers | What it does **not** cover / delta |
|---|---|---|---|---|
| `gf180-gate-driver` (`98ca4a85`) | `spec/low-side-power-switch.md` (ratified 2026-08-18): on-die `nfet_06v0` low-side switch, `Ron·W` table, DRM §14.2 EM budget, `Ron`-sense OCP and `pnp` thermal-sense reference structures | **Adopted by pinned reference** for the low-side switch: `nfet_06v0`, the `Ron·W` baseline (§2.1 there), the EM method (§3 there, which this record re-derives and extends to the repo's 0.8 factor), and the OCP / thermal-sense reference structures (its §4) | LS device flavor and its `Ron·W` at |Vgs| 3.6 – 5.0 V, all 15 PVT points; the per-ampere width/via budget | **Gate drive 5.5 V** (beyond the measured 5.0 V); **|Vgs| 2.97 – 3.6 V** of the fallback tier; switching loss and gate charge for the width (its §6 item 5, unmeasured); self-heating; the LS in a *synchronous* role (it is a sink for a load there, a freewheel path here); its flyback diode (DR-0011 option b) is **not adopted** — the synchronous LS plus dead-time body-diode conduction replaces it |
| `gf180-gate-driver` — **the high-side switch** | the sibling measured `pfet_06v0` `Ron·W` at the same gate drive (its §2.1, 5.53 / 7.14 / 9.27 Ω·mm at −40 / 27 / 125 °C, 5.0 V), as "not the switch" | **Not adopted: nothing ratified.** The data are evidence for §3 and §4.3 only | PMOS `Ron·W` at |Vgs| 3.6 – 5.0 V | Everything a high-side switch needs that the low-side work does not: a **gate drive referenced to VIN** (a level shift from the 3.3 V control rail at target), turn-on / turn-off timing against the LS (R14), the PMOS body diode (drain-to-nwell, nwell at VIN) during dead time, a width roughly 3× the LS for equal resistance, and its own EM budget on the VIN → HS strap (§5.1) |
| `gf180-bandgap` (`c68ccc6b`) | 1.20 V reference; ±2 % untrimmed (3σ, MC + corners), < 50 ppm/°C, 3.3 V ±10 % supply, "also 5 V flavor" as stretch (README target table; its `reuse.lock.json` also shows it evaluating `gf180-opamp`) | **Adopted at the interface** | the reference, and the R4 ±2 % term | **Supply domain** (needs the 3.3 V control rail at target; its 5 V flavor is a stretch row there, not ratified); its load row is `TBD` (unbuffered, high-Z), so the error-amp input loading must be shown against it; area and quiescent current accounted in R9 |
| `gf180-opamp` (`cda7ff5a`) | `spec/target-spec.md`: ratified (partial) 3.3 V two-stage Miller op-amp, gain / GBW / PM into a stated CL, CMRR / PSRR, input common-mode range row; 5 V stretch row named, **not opened** | **Adopted at the interface** as the error amplifier | the topology and its ratified target rows | **Supply domain** (3.3 V only); the numerical GBW into the type-III compensation load (the loop needs GBW well above the 250 kHz crossover bound, to be shown against the sibling's recorded value — **not read** here); output swing against the PWM ramp |
| `gf180-comparator` (`80402c06`) | ratified table: offset σ ≤ 15 mV (3σ), decision time ≤ 1.5 ns at 50 mV overdrive and 3.3 V, 3.3 V ±10 % supply | **Adopted at the interface** as the PWM comparator and the current-limit comparator | decision time and offset against R16's 0.70 A minimum trip window (a 15 mV offset is small against `Ron`-sense's 3 : 1 window) | **Supply domain** and, specific to the current limit, its **input common-mode**: the sense input is the switch node, which swings to 5.5 V (6.0 V peak) against a 3.3 V part, so an input divider or level-shifting stage is needed. Not sized here |
| `gf180-rcosc` (`6e4c3951`) | ratified relaxation oscillator: **48 MHz**, 8-bit trim ±40 %, −40…+85 °C, 3.3 V, Iq < 500 µA | **Kept — not adopted as an instance.** The topology is the starting point for the buck oscillator by reference, and a re-target is a separate record | the topology and its trim math | **Frequency** (48 MHz vs. 2 MHz: a ÷24 divider would add a digital partition and the 2 MHz row already tolerates ±15 %); **temperature range** (+85 °C vs. the +125 °C top this spec grades); **accuracy** (post-trim −10.8 % / +8.8 % over its range vs. R7's ±15 % over a wider range); **untrimmed spread ±35 %** (R7 needs a single-point trim). The oscillator is also the only block whose ratified numbers do not reach this spec's, so it is the one deliberately not adopted |

Nothing in any sibling repo is modified by this issue. The pinned SHAs are in
`reuse.lock.json`; adoption is **by reference and gated on the common delta**,
so the lock file records the status of each, not an import of any file.

## 8. Residual register (what this record leaves open, by name)

Nothing below is a soft target: each is an open question with the evidence that
closes it.

1. **R9 may not close.** Needs: switch sizing (`Ron·W` → width), gate charge at
   2 MHz for that width, metal and via resistance from the extracted power path.
   If the ≈ 100 mW left in §4.3 is not enough, the response is a new record that
   changes R9 *with its reason*, never a silent relaxation.
2. **R10, efficiency at full load across all corners, has no floor.** Needs the
   sizing above and the 125 °C `Ron` rise.
3. **The 3.3 V control rail** (§7 common delta): choose between a dedicated
   regulator (a candidate `gf180-ldo` was not read), supplying the controller
   from VIN with 5 V-class devices (the siblings are 3.3 V designs), or both.
4. **R2's 0.5 V overshoot margin** at Vin max. Needs the pad-to-switch
   inductance and the dead-time / edge-rate choices before it can be called
   achievable, and may force a snubber or a lower Vin max.
5. **Slot area in the EM width** (§5.3): confirm with the foundry whether
   Table 14.3's drawn width counts slots; until then the conservative reading
   stands.
6. **A working signoff DRC for 30 kÅ**: needs the `klayout-tools` items above
   and a KLayout new enough to run the PDK-native deck, then a negative
   control. Until then R21's DRC leg is unmet by construction.
7. **MT30.7 (die-level 30 % MetalTop coverage)** is a chip-assembly rule, not a
   block rule; it cannot be judged on this block's GDS.
8. **Dead-time tolerance of the 3.3 V-class controller against the 5 V power
   gates**: R14's 1 – 6 ns window sits on gate nodes charged by drivers that are
   not designed.
9. **Package model** (§0.3) is an assumption; it moves ~25 mW in §4.3.
10. **Stretch tier not opened**: the 1 A stage may not drive the layout until
    500 mA closes (`CLAUDE.md`).

## 9. Acceptance cross-check

| Issue #2 acceptance item | Where |
|---|---|
| `spec/` carries the target spec and a decision record ratifying it | `spec/target-spec.md`, this record |
| Every row has its condition and corner set; every efficiency or ripple row names its external parts | spec §1 – §3, columns *Grading condition*, *Corner set*, *External parts* |
| The EM budget method is recorded, citing the design manual | §5.1: DRM §14.2, Tables 14.3 / 14.4, with the 125 °C limits and per-net current / width / cut counts at 500 mA, 200 mA and 1 A |
| Adopt-or-keep decisions on the siblings are recorded | §7 and `reuse.lock.json` |
| README DRAFT marker dropped and the table matches the spec | `README.md` |
| Each thick-MetalTop rule listed with a `klt` verdict and evidence; every "not enforced" links an issue | §5.2; klayout-tools#3796 and comment on #2351 |
| No simulated number called measured; no result claimed | the spec header and §0 conventions: `exp` and `rep` cells, §4 |
| The spec is not relaxed later to make results pass | status line; any change needs a new record |
