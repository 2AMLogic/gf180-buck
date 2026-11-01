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

## `schematics/` and `netlists/` — power stage and gate drive (issue #33)

Everything here is simulated, never measured. xschem sources in
`schematics/`, committed netlists in `netlists/`, symbol search path in
[`xschemrc`](xschemrc) (it reads the PDK from `GF180_VARIANT_DIR`, so
`source sim/env.sh` first).

| Block | Schematic | Netlist | Ports |
|---|---|---|---|
| `power_stage` | `schematics/power_stage.sch` | `netlists/power_stage.spice` | `GH GL VIN SW GND` |
| `gate_drive` | `schematics/gate_drive.sch` | `netlists/gate_drive.spice` | `PWM VDD3 VIN GND GH GL` |

Regenerate and check (never raw `xschem`):

    source sim/env.sh
    klt netlist design/schematics/<block>.sch -o design/netlists/<block>.spice --rcfile design/xschemrc --block --pdk gf180mcuD
    klt netlist design/schematics/<block>.sch -o design/netlists/<block>.spice --rcfile design/xschemrc --block --pdk gf180mcuD --check --ignore-comments   # status: match

`--ignore-comments` is needed because xschem writes the absolute `** sch_path:`
of the checkout into the netlist; every non-comment line is still compared.

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
