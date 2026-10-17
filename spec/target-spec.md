# Target specification — gf180-buck

- **Status**: **Ratified on merge** of the pull request that carries
  [`decision-records/0001-ratify-target-spec.md`](decision-records/0001-ratify-target-spec.md)
  (issue #2). Until that merge every row below is a proposal. Ratifying a row
  sets it as a **design-to target**, never as "met": this repo has no schematic,
  no simulation and no layout yet, and no row below is supported by a result.
- **Date**: 2026-10-17
- **PDK pin used for every PDK fact here**: `gf180mcuA` (the 30 kÅ MetalTop
  variant), open_pdks `f6eeac7dad085ffcc829ccfd721f7b4ce39edcf7`; `klt`
  `0.7.1.dev1754+g81ac4d3915c1`, `gf180mcu` deck content hash
  `sha256:612a48b497a015b1e92d6eb93c98a4dc35e00c954dd7ba93a924d8ea6c49d1e7`.
- **Changing a number** here needs a new decision record. Agents do not relax a
  row to make a result pass (`CLAUDE.md`).

The README's DRAFT table was the starting point. Every value that differs from
it, and every row it did not have, is explained in the decision record
(§2 "Departures from the README draft").

## How to read this document

**Three tiers, each fully specified.** Target, fallback and stretch are separate
tables with every row filled in. A row that is identical across tiers says so
by repeating the value, never by "same as target".

**Cell conventions.**

| Cell | Meaning |
|---|---|
| a number | a bound or a defined value |
| `n/b` | deliberately **no bound** on that side |
| `exp: x` | a first-order analytic expectation from the arithmetic in the decision record. It is **not** a result, not graded, and not evidence |
| `rep` | reported at every grading point, no pass/fail bound ratified yet (the decision record's residual register names what sets it) |

**Directions.** For a "max-type" row the max cell is the bound; for a
"min-type" row the min cell is the bound; for a range row both are.

**Nothing is claimed.** Every value is a requirement. A simulated number is
never called measured (`CLAUDE.md`).

## 0. Grading conventions used by every row

### 0.1 Corner sets

Process corners come from the PDK's model library (`sm141064.ngspice`).
`klt pdk corners --pdk gf180mcuA` reports `typical`, `ff` and `ss` as complete
bundles (MOS, BJT, diode, resistor, MIM, MOS-cap all skewed together) and `fs`
and `sf` as **MOS-only** (every other family stays typical). Corner sets below
are therefore stated in those terms.

| Set | Process | Temperature | Input supply | Points |
|---|---|---|---|---|
| **C-full** (default) | `typical`, `ff`, `ss`, `fs`, `sf` | −40, 27, 125 °C | Vin min, nom, max (±10 %) | 5 × 3 × 3 = **45** |
| **C-typ** | `typical` | 27 °C | Vin nom | 1 |
| **C-line** | `typical` | 27 °C | Vin min, nom, max | 3 |
| **C-hot** | `typical`, `ss` | 125 °C | Vin min, nom, max | 6 |
| **C-ex** | the extremes of C-full that bind the row, named per row | | | stated in row |

C-full is the PDK-corner × ±10 % supply × −40…125 °C set that `CLAUDE.md` and
the issue ask for. The only narrower sets are C-typ (rows that grade one
operating point by definition: peak efficiency, per README), C-line, C-hot,
and rows whose own text names the corners. 125 °C is the top of the range
because DRM §14.1.1 gives −40…125 °C as the design range and Table 14.3 / 14.4
stop at 125 °C.

Every row on a **C-full** grade is also graded **with the external-part
tolerances** of §0.2 at their worst combination for that row, not at nominal.

### 0.2 External parts (the parts every efficiency, ripple, transient and
stability number assumes)

Three sets, one per tier. The inductor is modelled as L in series with DCR and
a parallel winding capacitance; the capacitor as C in series with ESR and ESL.

| Set | Used by | Inductor L (tolerance) | DCR typ / max | Isat (L −30 %) | Output capacitor C nominal / **effective at 1.8 V DC bias, derated** | ESR typ / max | ESL |
|---|---|---|---|---|---|---|---|
| **P-T** | target | 3.3 µH (±20 %) | 100 / 150 mΩ | ≥ 1.0 A | 10 µF / **≥ 4.7 µF** (typ 6 µF) | 5 / 10 mΩ | 0.5 nH |
| **P-F** | fallback | 10 µH (±20 %) | 200 / 300 mΩ | ≥ 0.5 A | 10 µF / **≥ 4.7 µF** (typ 6 µF) | 5 / 10 mΩ | 0.5 nH |
| **P-S** | stretch | 1.5 µH (±20 %) | 40 / 60 mΩ | ≥ 1.6 A | 10 µF / **≥ 4.7 µF** (typ 6 µF) | 5 / 10 mΩ | 0.5 nH |

- Winding capacitance: 3 pF (all sets). Capacitor dielectric class: X7R or
  better (rated to 125 °C); capacitance tolerance ±20 % **before** bias
  derating, which is why the effective-capacitance figure is the one the loop
  and ripple rows use.
- **Excluded from every efficiency number**: inductor core and AC (skin /
  proximity) loss, and capacitor dielectric loss beyond ESR. They are not
  modelled here, so an efficiency figure in this spec is "efficiency excluding
  inductor core loss", and is stated that way wherever it is quoted.
- The load is an ideal current sink with the edge rate named in each row. A
  resistive load is named where a row needs one (soft start).

### 0.3 Package model (all tiers)

Assumed, not taken from a package datasheet (none is chosen): each power net
(VIN, SW, GND) reaches the die through **N parallel bond wires** to a pad. One
wire is 25 µm gold, 2 mm long: R = ρL/A = 2.44·10⁻⁸ × 2·10⁻³ / 4.91·10⁻¹⁰ ≈
0.10 Ω, L ≈ 2 nH (≈ 1 nH/mm rule of thumb), pad capacitance 0.5 pF.

| Quantity | min | typ | max |
|---|---|---|---|
| R per wire | 0.075 Ω | 0.10 Ω | 0.125 Ω |
| L per wire | 1.5 nH | 2.0 nH | 2.5 nH |
| Wires per power net | target 2, fallback 2, stretch 4 | | |

Re-ground these numbers when a package is chosen; until then, every
efficiency figure carries them as an assumption.

### 0.4 How a switching-converter number is graded (run length, step, steady state)

`CLAUDE.md` requires the run length, step and steady-state method next to every
number. They are fixed here once; a result record must restate them.

| Item | Rule |
|---|---|
| Analysis | ngspice `.tran`. ngspice has no periodic steady-state analysis, so steady state is reached by running, not solved for |
| Max time step | **T/200** (2.5 ns at 2 MHz, 5 ns at 1 MHz, 1.25 ns at 4 MHz); `.tran … uic` off. Switching-edge windows (gate and SW transitions) use ≤ 100 ps, because the SW overshoot row is only meaningful if the edge is resolved |
| Start-up run | from `Vin = 0` through the soft-start time of the tier, then ≥ 200 further switching cycles |
| Steady-state test | the run is "settled" when two **consecutive 20-cycle windows** differ by **< 0.1 %** in mean Vout **and** < 1 % in peak inductor current. The record states the window start. Measurements use the **last 20 cycles of a settled run** |
| Ripple and efficiency | averaged over ≥ 20 settled cycles (efficiency: whole cycles only, ending on a cycle boundary) |
| Load step | step applied after settling; run ≥ 100 switching cycles after the step, or until Vout is back inside the recovery band for 20 consecutive cycles, whichever is longer |
| Loop gain | **both** of: (a) an AC loop-gain from an **averaged** (state-space / behavioural switch) model, and (b) a switched `.tran` load-step. They are cross-checked (§1, R13). Neither alone closes the stability row |
| Post-layout | the same rows re-run with the extracted power path (pad to switch), per `CLAUDE.md` |

## 1. Target tier

Vin 5.0 V ±10 %, Vout 1.8 V, 0–500 mA, 2 MHz, external parts **P-T**, package
§0.3 with 2 wires per power net, 30 kÅ MetalTop.

| ID | Parameter | Min | Typ | Max | Grading condition | Corner set | External parts |
|---|---|---|---|---|---|---|---|
| R1 | Input voltage (operating) | 4.5 V | 5.0 V | 5.5 V | DC at the VIN pad, source side of the bond-wire model; all other rows hold across this range | C-full (it *is* the line axis) | P-T |
| R2 | Switch-node and device terminal absolute maximum | −0.7 V (SW) | n/b | 6.0 V (any thick-oxide device terminal-to-terminal, SW, VIN) | Peak of **SW** and of every power-device Vgs / Vds in the switched `.tran` with the edge window of §0.4, including bond-wire ringing. 6.0 V is the DC ceiling the sibling `gf180-gate-driver` records for `*_06v0` devices (its `gate-driver.md` §2.3); no transient credit is taken above it. Margin at Vin max = 0.5 V (9 %) for overshoot. The −0.7 V floor is the substrate-diode clamp on the low-side drain during dead time | C-full, load 0, 50 mA, 500 mA | P-T, §0.3 |
| R3 | Power-switch device flavor | HS `pfet_06v0` | — | LS `nfet_06v0` | High-side PMOS (gate swing referenced to VIN, no bootstrap), low-side NMOS. Rationale in the decision record §3 | n/a (design choice) | n/a |
| R4 | Output voltage | 1.728 V (−4 %) | 1.800 V | 1.872 V (+4 %) | Mean Vout (settled, §0.4) over line, load and temperature, **untrimmed**. Budget: reference ±2 % + divider ratio ±1 % + error-amp offset and finite DC gain ±1 % = ±4 % (linear sum, §4 of the record) | C-full × load {0, 50, 250, 500 mA} | P-T |
| R5 | Load current | 0 | 250 mA (mid-point, for efficiency grading) | 500 mA | DC, with Vout inside R4. Load edge rate for transient rows: 1 A/µs | C-full | P-T |
| R6 | Light-load behaviour | forced PWM | — | — | Fixed-frequency PWM at **all** loads including 0: no pulse skipping, no burst mode. Inductor current goes negative at light load: ΔIL/2 reverse peak at 0 load must not trip the current limit or latch a fault (R16) | C-full at 0 and 50 mA | P-T |
| R7 | Switching frequency | 1.7 MHz | 2.0 MHz | 2.3 MHz | Fundamental of the SW node, measured over ≥ 100 settled cycles. ±15 % covers a single-point trim at test (the sibling `gf180-rcosc` post-trim spread is −10.8 % / +8.8 % over temperature; the untrimmed spread is ±35 %, so an untrimmed oscillator does **not** meet this row) | C-full | P-T |
| R8 | Inductor ripple (derived, bounds the current limit and EM) | 0.119 A p-p | 0.175 A p-p | 0.270 A p-p | **Not a design bound** — the consequence of R1, R4, R7 and the P-T tolerances: ΔIL = Vout(1−Vout/Vin)/(L·f), min at Vin 4.5 / L +20 % / f 2.3 MHz, max at Vin 5.5 / L −20 % / f 1.7 MHz. Graded as a check that the build matches the arithmetic | C-ex: the three combinations named | P-T |
| R9 | Peak efficiency | 85 % | rep | n/b | η = Pout / Pin, Pin at the VIN pad **source side** of the bond-wire model (so wire loss is included). Includes: on-die conduction (extracted power path), gate drive, controller and reference quiescent, dead-time diode loss, inductor DCR, capacitor ESR. **Excludes** inductor core/AC loss (§0.2). "Peak" = the best of the load points {50, 100, 250, 500 mA}. Post-layout, extracted | C-typ (README grades the peak at one point) | P-T, §0.3 |
| R10 | Efficiency at 500 mA, all corners | rep | rep | n/b | Same definition as R9 at 500 mA. **No floor is ratified**: the sibling `Ron·W` data are 1.4× higher at 125 °C than at 27 °C (`tt`, 5.0 V gate drive: 3.09 vs 2.22 Ω·mm) and 2.4× wide across its full grid, and a floor needs sizing evidence this issue does not have. The record's residual register names the decision that sets it | C-full | P-T, §0.3 |
| R11 | Output ripple | n/b | exp: 2.7 mV p-p | 18 mV p-p (1 % of Vout) | Peak-to-peak of Vout at the capacitor terminals, settled, after a 20 MHz first-order low-pass (removes switching-edge spikes, keeps the ΔIL/(8fC) and ESR terms). Analytic worst case with P-T at C = 4.7 µF, f = 1.7 MHz, ESR 10 mΩ, ΔIL = 0.270 A is 6.9 mV | C-full × load {50, 500 mA}; binds at Vin max, hot, ss | P-T |
| R12 | Load-step transient | n/b | exp: 53 mV | 90 mV (5 % of Vout) deviation; recovery to ±18 mV (1 %) in **25 µs** | Step 50 → 450 mA (10 % → 90 %) and back, 1 A/µs, applied after settling; deviation is the larger of the undershoot and the overshoot; recovery time is measured to the last exit from the ±1 % band. `exp` = ΔI/(2π·fc·Ceff), fc = 200 kHz, Ceff = 6 µF | C-full | P-T |
| R13 | Control architecture and stability | Phase margin ≥ 45°, gain margin ≥ 10 dB | PM 60°, GM 15 dB | crossover fc 100 – 250 kHz | **Voltage-mode PWM, type-III compensation**. Evidence required (all three): (a) loop-gain from an averaged model, (b) switched load-step R12, and (c) the **cross-check** — the switched step's peak deviation and recovery time agree with the averaged model's small-signal prediction within **±30 %**. Margins hold at the P-T tolerance corners (L ±20 %, Ceff 4.7 – 12 µF, ESR 5 – 10 mΩ) | C-full × tolerance corners | P-T |
| R14 | Dead time | 1 ns | 3 ns | 6 ns (1.2 % of T) | Between the commanded turn-off of one device and the turn-on of the other, measured at the power-device gates at |Vgs| = the device's minimum Vth over the corner. **Zero overlap**: at no time may both devices have |Vgs| above that threshold. Diode-conduction loss at the max: 0.7 V × 0.5 A × 2 × 6 ns × 2 MHz = 8.4 mW | C-full × load {0, 50, 500 mA} | P-T |
| R15 | Soft start | 100 µs | 200 µs | 500 µs | Vout from 0 to 90 % of target, monotonic, overshoot above R4 max ≤ 5 % (90 mV), into 0 load **and** a 3.6 Ω resistive load (500 mA at 1.8 V). Peak inductor current during start stays below the R16 minimum trip. Analog ramp on the reference input — no counter (§6 of the record) | C-full | P-T |
| R16 | Cycle-by-cycle current limit (peak inductor current trip) | 0.70 A | exp: 1.2 A | 2.1 A | Load current ramped in the switched `.tran` until the limit engages. **Min bound**: no trip at 500 mA load, f min, L −20 %, Vin max (peak = 0.5 + 0.135 = 0.635 A) — 10 % margin. **Max bound**: the trip inherits `Ron`'s PVT window (3 : 1, as `gf180-gate-driver`'s `low-side-power-switch.md` §4.1 records for a `Ron`-sense limit), so this is a **die-protection threshold, not a precision limit**. A tighter window needs a ratioed sense FET and a new decision record | C-full | P-T |
| R17 | Thermal shutdown | not provided (n/b) | n/b | n/b | Stretch only (see §3 R17). Target tier: no sense structure is required; the design must not preclude one | n/a | n/a |
| R18 | Top metal and electromigration budget | per DRM Tables 14.3 / 14.4 at 125 °C, unidirectional, **× 0.8 design margin** | | | **MetalTop (30 kÅ, `tm30k`) ≤ 4.30 mA/µm; Metal1 and Metal2 ≤ 0.536 mA/µm; Via1, Via2 and COMP contact ≤ 0.144 mA per cut.** Widths and via counts per net: the decision record §5 (e.g. SW and VOUT at 500 mA: ≥ 116.4 µm of MetalTop, ≥ 3 473 cuts per via level). Metal width is **net of slot width** (MSLOT, §5.3). Verified post-layout; the record fixes the method and cites the manual | n/a (a 125 °C budget) | n/a |
| R19 | Package model | R 0.075 / 0.10 / 0.125 Ω per wire; L 1.5 / 2.0 / 2.5 nH per wire | | | §0.3, 2 wires per power net | n/a | n/a |
| R20 | PVT corner set | C-full: 45 points | | | §0.1; every recorded result is graded on it unless its row names a narrower set | n/a | n/a |
| R21 | Signoff | DRC clean, LVS clean, EM-checked, post-layout re-verified | | | DRC with the PDK-native 30 kÅ rule family (the `klt` curated deck alone does **not** cover it — decision record §5.2); LVS match; EM against R18; every R-row above re-run on the extracted netlist | n/a | n/a |

## 2. Fallback tier

Vin 3.3 V ±10 % (2.97 – 3.63 V), Vout 1.8 V, 0–200 mA, 1 MHz, external parts
**P-F**, 2 wires per power net, 30 kÅ MetalTop (11 kÅ argued in §5.4 of the
record).

| ID | Parameter | Min | Typ | Max | Grading condition | Corner set | External parts |
|---|---|---|---|---|---|---|---|
| R1 | Input voltage (operating) | 2.97 V | 3.3 V | 3.63 V | As target R1 | C-full | P-F |
| R2 | Switch-node and device terminal absolute maximum | −0.7 V (SW) | n/b | 6.0 V | As target R2. Margin at Vin max = 2.37 V. The 3.3 V device flavor is rejected: Vin max 3.63 V already equals its 3.3 V + 10 % limit (DRM §14.1.2), leaving no overshoot margin | C-full, load 0, 20, 200 mA | P-F, §0.3 |
| R3 | Power-switch device flavor | HS `pfet_06v0` | — | LS `nfet_06v0` | As target (same layout; Ron·W is **worse** at |Vgs| = 2.97 V and is **not covered** by the sibling's measured 3.6 – 5.0 V range) | n/a | n/a |
| R4 | Output voltage | 1.710 V (−5 %) | 1.800 V | 1.890 V (+5 %) | As target R4, ±5 % untrimmed (reference ±2 % + divider ±1 % + amp ±2 %, the extra 1 % absorbs the lower loop gain at 1 MHz) | C-full × load {0, 20, 100, 200 mA} | P-F |
| R5 | Load current | 0 | 100 mA | 200 mA | DC; load edge rate for transient rows 0.5 A/µs | C-full | P-F |
| R6 | Light-load behaviour | forced PWM | — | — | As target R6 | C-full at 0 and 20 mA | P-F |
| R7 | Switching frequency | 0.85 MHz | 1.0 MHz | 1.15 MHz | As target R7 (±15 %) | C-full | P-F |
| R8 | Inductor ripple (derived) | 0.051 A p-p | 0.082 A p-p | 0.133 A p-p | As target R8 with P-F: min at Vin 2.97 / L +20 % / f 1.15 MHz, max at Vin 3.63 / L −20 % / f 0.85 MHz | C-ex | P-F |
| R9 | Peak efficiency | 80 % | rep | n/b | As target R9; load points {20, 50, 100, 200 mA}; Pin at VIN source side of the bond-wire model; excludes inductor core loss | C-typ with Vin = 3.3 V | P-F, §0.3 |
| R10 | Efficiency at 200 mA, all corners | rep | rep | n/b | As target R10 | C-full | P-F, §0.3 |
| R11 | Output ripple | n/b | exp: 2.1 mV p-p | 36 mV p-p (2 % of Vout) | As target R11. Analytic worst case: ΔIL = 0.133 A, f = 0.85 MHz, Ceff 4.7 µF, ESR 10 mΩ → 5.5 mV | C-full × load {20, 200 mA} | P-F |
| R12 | Load-step transient | n/b | exp: 42 mV | 180 mV (10 % of Vout) deviation; recovery to ±36 mV (2 %) in **50 µs** | Step 20 → 180 mA (10 % → 90 %) and back, 0.5 A/µs. `exp` = ΔI/(2π·fc·Ceff) = 0.16/(2π × 100 kHz × 6 µF), Ceff = 6 µF | C-full | P-F |
| R13 | Control architecture and stability | PM ≥ 45°, GM ≥ 10 dB | PM 60°, GM 15 dB | crossover fc 50 – 125 kHz | As target R13 (voltage mode, type III, averaged model + switched step + ±30 % cross-check), P-F tolerance corners (L ±20 %, Ceff 4.7 – 12 µF) | C-full × tolerance corners | P-F |
| R14 | Dead time | 1 ns | 4 ns | 10 ns (1 % of T) | As target R14. Diode-conduction loss at max: 0.7 V × 0.2 A × 2 × 10 ns × 1 MHz = 2.8 mW | C-full × load {0, 20, 200 mA} | P-F |
| R15 | Soft start | 200 µs | 400 µs | 1 000 µs | As target R15; resistive load 9 Ω (200 mA at 1.8 V) and 0 load; overshoot ≤ 5 % | C-full | P-F |
| R16 | Cycle-by-cycle current limit | 0.35 A | exp: 0.6 A | 1.05 A | As target R16 (3 : 1 window). Min bound: no trip at 200 mA, f min, L −20 %, Vin max (peak = 0.2 + 0.067 = 0.267 A) | C-full | P-F |
| R17 | Thermal shutdown | n/b | n/b | n/b | Not provided (stretch only) | n/a | n/a |
| R18 | Top metal and electromigration budget | as target R18 limits (× 0.8) | | | Same per-µm and per-cut limits as target R18. Widths and cut counts at 200 mA in the decision record §5.1 (SW: ≥ 46.6 µm of MetalTop, ≥ 1 389 cuts per via level). **Thinner option**, argued: a `tm11k` variant (gf180mcuB / D) is the fallback metal: 1.5 mA/µm at 125 °C × 0.8 → 167 µm per 200 mA. It is acceptable for this tier only if the 30 kÅ option is not available on the chosen shuttle | n/a | n/a |
| R19 | Package model | as target R19 | | | §0.3, 2 wires per net | n/a | n/a |
| R20 | PVT corner set | C-full: 45 points | | | §0.1 with Vin 2.97 – 3.63 V | n/a | n/a |
| R21 | Signoff | as target R21 | | | As target R21 | n/a | n/a |

## 3. Stretch tier

Vin 5.0 V ±10 %, Vout programmable 1.0 – 3.3 V (graded at 1.8 V unless a row
says otherwise), 0 – 1 A, 4 MHz, external parts **P-S**, 4 wires per power net,
30 kÅ MetalTop. Stretch rows are not opened until the target tier closes
(`CLAUDE.md`: "Do not let the 1 A power stage drive the layout before 500 mA
closes").

| ID | Parameter | Min | Typ | Max | Grading condition | Corner set | External parts |
|---|---|---|---|---|---|---|---|
| R1 | Input voltage (operating) | 4.5 V | 5.0 V | 5.5 V | As target R1 | C-full | P-S |
| R2 | Switch-node and device terminal absolute maximum | −0.7 V (SW) | n/b | 6.0 V | As target R2. Margin at Vin max 0.5 V; at Vout = 3.3 V, Vin min 4.5 V the duty is 0.73 and the LS conducts only 27 % of the cycle | C-full, loads 0, 100 mA, 1 A | P-S, §0.3 |
| R3 | Power-switch device flavor | HS `pfet_06v0` | — | LS `nfet_06v0` | As target | n/a | n/a |
| R4 | Output voltage | −4 % of the programmed value | programmed (1.0 – 3.3 V) | +4 % | As target R4 at the programmed value; **±2 % requires a reference trim** (bandgap stretch ±0.5 % trimmed), a trim interface this spec does not open | C-full × load {0, 100, 500, 1 000 mA} | P-S |
| R5 | Load current | 0 | 500 mA | 1 A | DC; edge rate 2 A/µs for transient rows | C-full | P-S |
| R6 | Light-load behaviour | forced PWM | — | — | As target R6 | C-full at 0 and 100 mA | P-S |
| R7 | Switching frequency | 3.4 MHz | 4.0 MHz | 4.6 MHz | As target R7 (±15 %) | C-full | P-S |
| R8 | Inductor ripple (derived) | 0.130 A p-p | 0.192 A p-p | 0.297 A p-p | At Vout = 1.8 V: min Vin 4.5 / L +20 % / f 4.6 MHz, max Vin 5.5 / L −20 % / f 3.4 MHz. At Vout = 1.0 V, Vin 5.5 V: 0.201 A p-p; Vout = 3.3 V, Vin 4.5 V: 0.216 A p-p (both inside the 0.297 A bound) | C-ex | P-S |
| R9 | Peak efficiency | 90 % | rep | n/b | As target R9 at Vout 1.8 V; load points {100, 250, 500, 1 000 mA}; excludes inductor core loss | C-typ | P-S, §0.3 |
| R10 | Efficiency at 1 A, all corners | rep | rep | n/b | As target R10 at 1 A | C-full | P-S, §0.3 |
| R11 | Output ripple | n/b | exp: 2.0 mV p-p | 0.5 % of Vout (9 mV at 1.8 V) | As target R11, 20 MHz low-pass. Analytic worst case: ΔIL = 0.297 A, f = 3.4 MHz, Ceff 4.7 µF, ESR 10 mΩ → 2.3 + 3.0 = 5.3 mV | C-full × load {100 mA, 1 A} | P-S |
| R12 | Load-step transient | n/b | exp: 42 mV | 54 mV (3 % of Vout at 1.8 V); recovery to ±9 mV (0.5 %) in **12.5 µs** | Step 100 → 900 mA, 2 A/µs. `exp` = 0.8/(2π × 500 kHz × 6 µF) at the top of the R13 crossover band; at fc = 400 kHz it is 53 mV, i.e. **at** the bound, so the stretch row needs the upper half of the band | C-full | P-S |
| R13 | Control architecture and stability | PM ≥ 45°, GM ≥ 10 dB | PM 60°, GM 15 dB | crossover fc 200 – 500 kHz | As target R13 with P-S | C-full × tolerance corners | P-S |
| R14 | Dead time | 1 ns | 2 ns | 3 ns (1.2 % of T) | As target R14. Diode loss at max: 0.7 V × 1 A × 2 × 3 ns × 4 MHz = 16.8 mW | C-full × load {0, 100 mA, 1 A} | P-S |
| R15 | Soft start | 50 µs | 100 µs | 250 µs | As target R15; resistive load 1.8 Ω (1 A at 1.8 V) and 0 load | C-full | P-S |
| R16 | Cycle-by-cycle current limit | 1.30 A | exp: 2.2 A | 3.9 A | As target R16 (3 : 1). Min bound: no trip at 1 A, f min, L −20 %, Vin max (peak = 1.0 + 0.149 = 1.149 A, +13 % margin) | C-full | P-S |
| R17 | Thermal shutdown | 140 °C trip | 150 °C trip, 135 °C release | 160 °C trip; hysteresis 10 – 25 °C | Junction temperature at the power array, sensed by a diode-connected `pnp` biased at fixed current (the structure `gf180-gate-driver`'s `low-side-power-switch.md` §4.2 records). The trip sits above 125 °C so it cannot false-trip, and no higher because DRM Tables 14.3 / 14.4 give no EM allowance above 125 °C | BJT bundles `typical`, `ff`, `ss` × Vin; T swept −40 … 150 °C | P-S |
| R18 | Top metal and electromigration budget | as target R18 limits (× 0.8) | | | Same per-µm and per-cut limits. Widths and cut counts at 1 A in the decision record §5.1 (SW: ≥ 232.8 µm of MetalTop, ≥ 6 945 cuts per via level) | n/a | n/a |
| R19 | Package model | as target R19 | | | §0.3, 4 wires per net | n/a | n/a |
| R20 | PVT corner set | C-full: 45 points | | | §0.1 | n/a | n/a |
| R21 | Signoff | as target R21 | | | As target R21 | n/a | n/a |

## 4. Rows that have no evidence and must not be read as met

Every `exp` cell, every `rep` cell, and every "Min/Max" cell above is a
requirement or an arithmetic expectation. The only data this spec cites are PDK
documents and the sibling repos' own recorded numbers, each named where used.
The decision record's §8 residual register lists what is still open.
