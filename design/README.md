# design

Design sources that are not layout. Everything here is simulated, never measured.

## `averaged/` — R13 evidence part (a): averaged-model loop gain

PDK-free. An averaged CCM voltage-mode buck power stage, the type-III
compensator of [`compensator.md`](compensator.md) (derivation, design-to
values, assumptions), and a Middlebrook-injection `.ac` bench, swept over the
P-T tolerance box:

| Axis | Values |
|---|---|
| Vin | 4.5, 5.0, 5.5 V |
| L (3.3 uH) | -20 %, 0, +20 % |
| C_eff | 4.7, 6, 12 uF |
| ESR | 5, 10 mOhm |
| Load (ideal current sink) | 0, 250, 500 mA |

= 162 points. Bounds graded per point: fc 100-250 kHz, PM >= 45 deg,
GM >= 10 dB. Failing points are reported as failures.

| File | Role |
|---|---|
| `averaged/buck_avg.spice` | circuit body: averaged stage, compensator, loop break |
| `averaged/gen_request.py` | writes `sweep_request.json` (the cross product, fixed order) |
| `averaged/sweep_request.json` | the `klt sim` request for the grid; untracked, written by `gen_request.py` |
| `averaged/extract.py` | fc / PM / GM from the complex loop gain, writes the record |
| `averaged/test_extract.py` | closed-form synthetic-loop unit tests |
| `averaged/run.sh` | the one command |
| `averaged/records/` | append-only JSON records |

### Run it

    design/averaged/run.sh                      # sweep -> extract -> records/<utc>-<hash>.json
    python3 -m unittest discover design/averaged   # extraction unit tests (no simulator needed)

`run.sh` regenerates the request and submits it with `klt sim`; on a dispatch
worker `KLT_SIM_BACKEND=batch` sends the grid to the Spot batch fleet, and
`run.sh` defaults to `batch` otherwise. It never loops `ngspice` locally; a
failed submit exits non-zero. The record carries fc, PM and GM for every point
with per-bound pass/fail, the ngspice version, the deck sha256, the request
sha256, the batch job id and `results_sha256` (hash of the rounded results).
Printed precision: fc 0.001 kHz, PM 0.01 deg, GM 0.01 dB; a re-run reproduces
the same `results_sha256`.

Extraction (`extract.py`): `T = -v(vo)/v(b)` from the complex AC vectors
(`options.complex_vectors`). fc is the highest-frequency downward 0 dB
crossing; PM = 180 + unwrapped phase at fc; GM is the minimum of
`-20*log10|T|` over every -180 degree crossing, `"none"` when the phase never
reaches -180 inside 100 Hz - 20 MHz.

### Status of the sweep record

Two 162-point records are committed in `averaged/records/` (simulated, not
measured). Both ran on the Spot batch fleet (jobs `klt-sim-a298dda7effa` and
`klt-sim-361f1a84fa74`, runner klt 0.8.0, ngspice 46, deck sha256 `1b953b6413df...`,
request sha256 `41eea10aa550...`) and carry the same `results_sha256`
`781e1a29003df405`, so a re-run reproduced the numbers to the printed precision.
The earlier batch blocker (runner image on klt 0.7.0, klayout-tools#3676) is
resolved: the runner now reports every required feature supported.

Result: 114 of 162 points pass all three bounds; **48 fail**, all on fc.
PM min 56.27 deg and GM min 22.30 dB, so PM and GM hold everywhere; fc spans
65.858..245.042 kHz. Every failing point is C_eff = 12 uF with fc below the
100 kHz floor (lowest 65.858 kHz); the failures are spread evenly over Vin, L,
ESR and load (the load axis only moves the operating point, per section 0.2).
The compensator was not retuned to hide them: the fixed design-to values put
fc near 150 kHz at C_eff = 6 uF and the 4.7-12 uF range is wider than one
fixed crossover covers. Whether R13 tolerates this, or the compensator or the
C_eff range should change, is a spec/design decision for the tracker (#5),
not made here. R13 stays open until the switched step (b) and cross-check (c).

Not included: the finite GBW of the adopted `error_amplifier`, switch Ron and
loop delay (see `compensator.md`). The batch submit warned that the serial job
bound (19560 s) exceeds the fleet ceiling of 3600 s; the job finished in 11-12 s
of compute, so no shard split was needed, but `request.remote.hosts` is the
lever if the grid grows.

## `schematics/` — controller blocks (issue #34, part of #21)

Transistor-level xschem schematics of the controller blocks that are new in
this design, on the 3.3 V control rail of
[record 0003](../spec/decision-records/0003-control-rail.md) (`VDD33`,
2.97–3.63 V). The `.sch` files are drawn by `schematics/gen_schematics.py`
(net-label connectivity, sizes next to the topology) and are the sources of
truth once committed; netlists are derived with `klt netlist` only (never raw
`xschem`) by `design/netlist.sh`, committed under `netlists/`, and
`design/netlist.sh --check` reports `match` for all four.

| Block | Schematic | Does | Spec rows |
|---|---|---|---|
| `osc_ramp` | `schematics/osc_ramp.sch` | current-charged cap relaxation oscillator; the `RAMP` node is the PWM sawtooth, `CLK` the reset pulse; 3-bit MIM trim bank for the single-point trim | R7 (2 MHz ±15 %), R6 (always runs: forced PWM) |
| `pwm_comp` | `schematics/pwm_comp.sch` | continuous-time comparator `VC > RAMP` and a set/reset latch: set by `CLK`, reset by the crossing **or** `OCP_TRIP` | R6, R16 (cycle-by-cycle reset) |
| `soft_start` | `schematics/soft_start.sch` | ~125 nA into a 20 pF cap, `EN` low holds it at 0; `VREF_SS = min(cap, VBG)` from a PMOS-input unity-gain OTA; no counter | R15 |
| `ocp_sense` | `schematics/ocp_sense.sch` | Ron-sense of `VIN − SW` on the high-side switch: thick-oxide (6 V) pair with gates at `SW` and `VTHP = VIN − Itrip·RT`, branch currents mirrored into 3.3 V resistors, PMOS-input comparator, gated by `HS_ON` and a ~50 ns leading-edge blank | R16, R6 (negative current) |

Bias: each block takes one current into its `IBIAS` pin (12 µA for
`osc_ramp`, 10 µA for the others). **The bias generator (bandgap voltage over a
resistor) and the 3.3 V regulator are not in this issue**; the smoke benches
force the current.

### Adopt-or-record outcomes (`reuse.lock.json`)

| Sibling | Outcome here | Why |
|---|---|---|
| `oscillator` (`gf180-rcosc`, `kept`) | **Kept, not adopted.** Topology idea (relaxation, trimmed) only; nothing copied or instantiated. | 48 MHz / ±35 % untrimmed against 2 MHz / ±15 %; as `reuse.lock.json` already records. |
| `pwm_and_current_limit_comparator` (`gf180-comparator`, `adopted_at_interface`) | **Not instantiated; deviation recorded.** | Its `comparator_dut` is a clocked StrongARM latch (precharge on `clk` low, DR-0001). A PWM crossing has no clock faster than the 2 MHz period it is measuring, and the current-limit input is `SW`/`VIN` (up to 6 V) against a 3.3 V part. A small continuous-time comparator is drawn in `pwm_comp`, and a VIN-domain front end in `ocp_sense`. The sibling was not re-sized. If a sampled PWM is chosen later, reconsider. |
| `low_side_power_switch` Ron-sense OCP (`gf180-gate-driver`, `adopted`) | **Method adopted, side changed.** | The adopted structure senses the low-side switch (a valley limit). R16 is a *peak* inductor current trip, so `ocp_sense` senses the high-side pFET. The high-side switch is `not_adopted`: its `Ron·W` is not ratified, so the trip current in amps (`Vtrip / Ron_HS`) is **open** until the power-stage sizing issue closes it. R16's 3 : 1 window is inherited from `Ron`, as the spec says. |
| `bandgap_reference`, `error_amplifier` | Not instantiated here. | `soft_start` takes `VBG` and drives `VREF_SS` at their interface; no sibling schematic is needed in these four blocks. |

### Single-corner smoke (simulated, not measured)

`design/smoke/run.sh` (one `ngspice -b` per bench, run in sequence; typical
corner, 27 °C, nominal rails, PDK per `sim/pdk.json`). **This is a debug-grade
smoke, not corner or Monte Carlo evidence**; the PVT grid is issue #25. Record:
[`smoke/records/`](smoke/records/) (append-only).

| Bench | Run length | Result (typical, 27 °C) | What it does *not* show |
|---|---|---|---|
| `osc_ramp` | 40 µs, 1 ns step; f from cycles 30–50 (a one-state relaxation oscillator; the first 30 cycles are discarded) | 1.93 MHz at trim code 101b; ramp 1.18–1.80 V | spread over PVT; untrimmed spread; the trim range was sized by arithmetic (0 to +3.15 pF on 4.05 pF) and only code 101b was run |
| `pwm_comp` | 80 µs, 1 ns step; duty averaged over cycles 40–58 µs | duty 0.55 at `VC` 1.5 V, 0.89 at 1.7 V; `OCP_TRIP` pulses at 70 µs cut it to 0.42 | duty linearity; delay; behaviour at the ramp ends |
| `soft_start` | 700 µs, 100 ns step | 0 → 90 % in 197 µs (R15 window 100–500 µs), final 1.198 V, no overshoot | load, `Vout` overshoot, peak inductor current (system level) |
| `ocp_fwd` | 6 µs | trips at ~134 mV of `VIN − SW` (design target 100 mV; the pair/resistor offset is not yet characterised) | trip current in amps, PVT window, offset spread |
| `ocp_rev` | 6 µs | `SW` 0.2 V above `VIN` while `HS_ON`: `TRIP` max 0.7 mV (R6 no-trip, one point) | light-load reverse current in a switched `.tran` |
| `vref_div` | 700 µs, 100 ns step (three VBG values) + 100 µs EN-low run | `VREF` 0.591 V at `VBG` 1.20 V (`VREF_SS` 1.183 V, ratio 0.5000); 0 → 90 % in 200 µs; 0.542 / 0.641 V at `VBG` 1.10 / 1.30 V; EN low: `VREF` max 21 mV (startup transient, not settled-zero proof); 2 pF stands in for the EA input | real EA input, divider resistor matching, temperature and process corners, `Vout` itself |

Known gaps for follow-up verification (#25/#26), not closed here: no
simulated edge case of ramp amplitude against the 3.3 V rail at the
2.97 V / 3.63 V rail corners (the comparator's NMOS input pair is only checked
at 1.18–1.80 V ramp); `osc_ramp` supply current is ~0.3 mA, and the 3.3 V
rail's total load is still the open item of record 0003 §4; frequency is
supply-dependent through the Schmitt window (no bandgap-referenced thresholds).

## `compensator` and `buck_top` — the whole design as one source set (issue #35, part of #21)

xschem sources, simulated never measured. Generated by `schematics/gen_schematics.py`
(same net-label style as the controller blocks); netlists by `netlist.sh`.

| Cell | Schematic | Netlist | Ports |
|---|---|---|---|
| `compensator` | `schematics/compensator.sch` | `netlists/compensator.spice` | `VOUT VREF IBIAS VC VDD33 GND` |
| `buck_top` | `schematics/buck_top.sch` | `netlists/buck_top.spice` | `VIN VDD33 GND SW VOUT EN VBG IBIAS_OSC IBIAS_PWM IBIAS_SS IBIAS_OCP IBIAS_EA TRIM0 TRIM1 TRIM2 VC PWM VREF_SS` |

`compensator` is the type-III network of [`compensator.md`](compensator.md) with
its design-to values taken from that file (Rtop 10k, Rbot 5k, R2 4.55k, R3 204,
C1 1.75n, C2 35.7p, C3 780p; not re-derived), as ideal R/C parts, around the
adopted error amplifier `opamp_two_stage` (`reuse.lock.json`, `error_amplifier`,
`adopted_at_interface`; pins `vdd vss vinp vinn vout ibias`). The amplifier is a
black-box symbol (`schematics/opamp_two_stage.sym`, `type=primitive`): no
schematic is in this repo and nothing is sized here, so the netlists reference
an undefined `opamp_two_stage` subcircuit that a simulator must be given from
the sibling pin. Its finite GBW is not in the averaged model (`compensator.md`).

`buck_top` instantiates `power_stage`, `gate_drive`, `osc_ramp`, `pwm_comp`,
`soft_start`, `ocp_sense` and `compensator` (one `.sym` per block, pin order equal
to the block's `.subckt`). `netlist.sh` now covers all eight cells and
`netlist.sh --check [block]` reports `match` for each; the older six committed
netlists are untouched (they still match; only the new two are written by this
issue). Top-level choices, not decisions of record:

- `L` and `Cout` are external: `SW` leaves the die and the filter returns on `VOUT` (sense input).
- The bias generator, bandgap (`VBG`) and 3.3 V regulator (`VDD33`) are not blocks in this design yet; they are top-level ports, as are the five `IBIAS_*` currents.
- Every block ground (`VSS`, `GND`) is the one net `GND`; `gate_drive`'s `VDD3` is `VDD33`.
- `HS_ON` for `ocp_sense` is `PWM` (the high-side command); the block's ~50 ns blank covers driver delay. A tap on the actual high-side gate would be a refinement.
- **`VREF_SS` scaling (closed, issue #53):** `soft_start` ends at `VBG` = 1.2 V but the compensator's `Vref` is 0.6 V. `buck_top` now has a 1:1 divider (`RREF1`/`RREF2` = 1 MΩ each, ideal parts) between `VREF_SS` and an internal `VREF` net that feeds the compensator, so `VREF_SS` still ramps to `VBG` (port unchanged) and the error amp sees 0 → 0.6 V. Decision and rejected alternatives: [`compensator.md`](compensator.md). Simulated findings (bench `vref_div`, typical 27 °C): the divider ratio is exact (0.5000) and 1 MΩ loading is negligible, but `soft_start`'s OTA settles 17 mV below `VBG` (1.183 V), so `VREF` = 0.591 V and `Vout` = 1.773 V (−1.5 % of R4's ±4 %) before any `VBG` tolerance; at `VBG` 1.10 / 1.30 V (illustrative ±8 %, not a characterised bandgap spread) `VREF` = 0.542 / 0.641 V (`Vout` 1.63 / 1.92 V). **Finding, R4 not relaxed:** the OTA offset consumes part of the R4 reference budget and must be carried in the #25/#26 corner and Monte Carlo evidence; the ratio error of a real (resistor-matched) divider is not yet included.

The item-1 attestation binds this whole set: [`inventory-item1.json`](inventory-item1.json)
(sources, symbols, generator, `xschemrc`, `compensator.md`, and the eight derived
netlists with a per-netlist `netlist.sh --check` freshness command) ->
`manifests/item1-attestation.json`, cited in `manifests/gf180-buck.json`. Not
covered: a simulation of `buck_top` (the averaged loop and the block smokes stand
as before) and any layout/LVS (#22-#24).

## `schematics/` and `netlists/` — power stage and gate drive (issue #33)

Everything here is simulated, never measured. xschem sources in
`schematics/`, committed netlists in `netlists/`, symbol search path in
[`schematics/xschemrc`](schematics/xschemrc) (it reads the PDK from
`GF180_VARIANT_DIR`; `netlist.sh` sources `sim/env.sh` itself).

| Block | Schematic | Netlist | Ports |
|---|---|---|---|
| `power_stage` | `schematics/power_stage.sch` | `netlists/power_stage.spice` | `GH GL VIN SW GND` |
| `gate_drive` | `schematics/gate_drive.sch` | `netlists/gate_drive.spice` | `PWM VDD3 VIN GND GH GL` |

Regenerate and check (never raw `xschem`; `netlist.sh` wraps `klt netlist`):

    design/netlist.sh [BLOCK...]           # write design/netlists/<block>.spice
    design/netlist.sh --check [BLOCK...]   # status: match, or DRIFTED (exit 1)

`netlist.sh --check` passes `--ignore-comments` because xschem writes the absolute `** sch_path:`
of the checkout into the netlist; every non-comment line is still compared.

### `check_geometry.py` — finger width and length pre-check (issue #116)

    python3 design/check_geometry.py [NETLIST...]          # default: design/netlists/*.spice
    python3 -I -m unittest discover -s design -p 'test_check_geometry.py'

Stdlib only; needs no PDK and no klt. It joins `+` continuation lines and checks every
`nfet/pfet_03v3/06v0` instance for finger width `W/nf` (`m` is a multiplier and does not
change it) and gate length `L` against the minimums in the script's header, each with its
rule id and source hash. Exit 0 = no new violation; 1 = a violation not on
`KNOWN_VIOLATIONS`, or a stale entry; 2 = an unparseable instance.

| Rule | Min | Applies to | Source |
|---|---|---|---|
| `comp.width.1` (DF.1a_LV) | 0.22 µm | `*_03v3` W/nf | klt 0.9.0 deck `sha256:cf44de63…97e1` |
| `comp.width.mv.1` (DF.1a_MV) | 0.30 µm | `*_06v0` W/nf | same deck |
| `PL.2_LV` | 0.28 µm | `*_03v3` L | PDK `rule_decks/poly2.rb` (not modelled by klt) |
| `PL.2_MV` | 0.70 µm nfet / 0.55 µm pfet | `*_06v0` L | same PDK file |

The `PL.2` file hash was read from the PDK revision installed on the writing host
(`f6eeac7d…`), not the `sim/pdk.json` pin (`c6d73a35…`, not installed there); re-check those
three numbers against the pin. The klt numbers come from the klt 0.9.0 package source, because
`klt drc --list-rules` prints no thresholds (tool gap: 2AMLogic/klayout-tools#5059).

On `main` it reports 306 instances and four known violations, all tied to #109 (not resized
here): `XMP_HG5` and `XMP_LG5` (`pfet_06v0`, W/nf = 0.1887 µm against 0.30 µm), each in
`gate_drive.spice` and in the flattened `buck_top.spice`. Not wired into CI.

### `power_stage` — sizing (R3, R9, R18)

HS `pfet_06v0` (source and body on VIN, no bootstrap) and LS `nfet_06v0`
(synchronous), L = 0.55 µm / 0.70 µm, the geometry the sibling measured.
`Ron·W` is taken from the pinned reference `low_side_power_switch`
(`reuse.lock.json`, `gf180-gate-driver` `98ca4a8`, `spec/low-side-power-switch.md`
§2.1), `tt`, 5.0 V gate drive:

| | `Ron·W` 27 °C | W | Ron 27 °C | `Ron·W` 125 °C | Ron 125 °C |
|---|---|---|---|---|---|
| LS `nfet_06v0` | 2.2246 Ω·mm | 224 × 100 µm = 22.4 mm | 99.3 mΩ | 3.0903 Ω·mm | 138.0 mΩ |
| HS `pfet_06v0` | 7.1427 Ω·mm | 300 × 100 µm = 30.0 mm | 238.1 mΩ | 9.2656 Ω·mm | 308.9 mΩ |

Method: record 0001 §4.3 leaves ≈ 100 mW for the on-die path, of which a
weighted on-die resistance of 0.15 Ω is the feasibility figure it uses
(0.5² × 0.15 = 37.5 mW). With D = Vout/Vin = 0.36, conduction is
I²·(D·R_hs + (1−D)·R_ls); for a fixed weighted resistance the total width is
smallest at W_hs/W_ls = √(D·ρ_p / ((1−D)·ρ_n)) = 1.345, which gives
W_ls = 22.2 mm and W_hs = 29.9 mm for 0.15 Ω; the instance counts round that to
the table.

- Weighted resistance, 27 °C: 0.36 × 0.2381 + 0.64 × 0.0993 = **0.1493 Ω** → 37.3 mW at 500 mA.
- Weighted resistance, 125 °C (`tt`): 0.36 × 0.3089 + 0.64 × 0.1380 = **0.1995 Ω** → 49.9 mW. R9 is graded at C-typ; R10 has no floor (record 0001 §8 item 2).
- **Not included**: metal and via resistance from pad to switch (post-layout, #22-#24), gate charge, the 2.4× full-grid `Ron·W` spread, `Ron·W` at the 5.5 V gate drive of Vin max.
- **Deviation from the adopted reference, recorded**: the LS device, L and `Ron·W` are the sibling's; its gate drive here is the 0-VIN swing (4.5-5.5 V), so 5.5 V is beyond the sibling's measured 5.0 V (`reuse.lock.json` `delta`). The sibling's flyback diode is not used; dead-time body-diode conduction replaces it. No second LS design was sized.
- The unit instance is W = 100 µm, nf = 10: the PDK model bin ends at W = 100.01 µm per instance, so a wider instance fails with "could not find a valid modelname".
- Width is a drawn gate width; layout (fingers, strap widths against R18) is #22.

### `gate_drive` — level shift, dead time, drivers

Signal path (all `06v0` devices are in the VIN domain, all `03v3` devices in the VDD3 domain):

1. `PWM` (3.3 V domain, 1 = HS on) → two `03v3` inverters → `PWMB`, `PWMT`.
2. **VIN-referenced level shift**: two `nfet_06v0` pull-downs (gates `PWMT`, `PWMB`, 3.3 V swing) and a cross-coupled `pfet_06v0` pair to VIN. Output `Q` swings 0-VIN.
3. **Non-overlap** by feedback from the actual power-gate nodes: `HD0 = NAND(A, LSOFFD)` where `LSOFFD` is `GL` through a low-threshold sense inverter and a delay pair; `LD0 = NOR(A, HSOND)` where `HSOND` is `GH` through a high-threshold sense inverter and a delay pair. The delay pairs (long-L `06v0` inverters, L = 3.5 µm) set the dead time; the turn-off paths contain no delay.
4. Two 6-stage tapered inverter chains (n widths 3, 10, 34, 115, 390, 1400 µm, p = 3×n) drive `GH` and `GL`.

The high-side gate swings 0-VIN, which is GND-referenced, so no bootstrap or boosted rail exists (R3). "VIN-referenced" means the up-shift of the control signal to the VIN domain.

**§8.8 (3.3 V-class controller against 5 V gates), stated.** The controller-side `PWM` is a 0-3.3 V (2.97-3.63 V) signal and only ever drives (a) `03v3` gates and (b) two `06v0` NMOS gates, whose 6.0 V ceiling it is far below. No VIN-domain node (up to 5.5 V, 6.0 V peak) is connected to a `03v3` terminal: the sense inverters read `GH`/`GL` with `06v0` devices and their outputs stay in the VIN domain. The gate drivers and the level shifter's high side run from VIN, not from the 3.3 V rail (record 0003 §2.3). What this does **not** establish: the `nfet_06v0` pull-down strength at Vgs = 2.97 V in `ss` at -40 °C (corner run, #25), and dead-time tolerance of the controller (the window R14 asks for) across corners.

### Dead-time smoke — `sim/dead-time/`

`sim/dead-time/run.sh` runs the real `gate_drive` into the real `power_stage` (0.5 A DC sink on SW, Vin 5.0 V, VDD3 3.3 V, 500 ns period, D = 0.36) through `klt sim --backend local`: **one** operating point, typical process, 27 °C, 20 ps step, stop 2.6 µs. The overlap detector flags any time GL > 0.5 V and VIN − GH > 0.5 V; a negative control with simultaneous complementary gate commands must read 1. Record: `sim/dead-time/records/`.

Result of the committed record (simulated, not measured): overlap 0 (control 1), dead time LS-off → HS-on 2.96 ns and HS-off → LS-on 3.17 ns at the 0.5 V thresholds. **Not established**: 0.5 V is a conservative stand-in, not the extracted minimum Vth over the corners (R14 asks for that), and 1-6 ns across C-full is untested. Observation, not a claim: SW undershoots to -0.885 V in this bench (no package model), past R2's -0.7 V floor; that row is graded in #25.
