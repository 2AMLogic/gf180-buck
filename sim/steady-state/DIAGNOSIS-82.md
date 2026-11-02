# Issue #82 - closed-loop non-regulation diagnosis (partial; simulated, pre-layout, not measured)

Evidence: `records/20261102-issue82-probe-typ-5V-27C-250mA.json`, requests `probe82_*.json`,
windowed summary `analyze_probe82.py`. Corner typical, 5.0 V, 27 C, 250 mA (ramps in at 260 us),
`--backend local`, 1 unit per run, `.tran 2.5n 450u` saved from 20 us (step_max 2.5 ns).
**No run settled** (spec 0.4 test not met); nothing here is a spec-graded number.

- **First departing node: the die ground `gnd_d`.** It rings -2.49 / +2.07 V against ideal 0 for ~1 ns at
  each SW falling edge (spec 0.3 package: 2 wires x 2 nH). `vref`, `fbn`, `vc` and the oscillator are
  all referenced to it and move with it.
- Refuted: error-amp input common mode (DC: 1.25 mV offset, ~76 dB gain at Vcm = 0.6 V); winding
  capacitance (c_wind = 0 gives the same result); the oscillator netlist alone.
- Correction to #77's notes: `vc` is inside its rail (0.78-2.02 V) and `out - gnd_d` is 1.14-1.97 V
  when taken against `gnd_d`; the "out of rail" and "+/-2 V out spikes" were measured against ideal 0.
- Clock measured against `gnd_d`: ~3 MHz in the baseline, 1.84 MHz with l_wire = 0.2 nH.
- With l_wire = 0.2 nH (diagnostic, not a spec value) `fbn` meets `vref` but Vout swings 0.98-1.66 V
  window to window: a second behaviour, untraced.

**Verdict: partial.** Design defect (unisolated control ground, no local decoupling) versus bench
artifact (die-ground model) is undecided, so no decision record and no bench change. Suggested next
steps: (1) separate the control-domain return in the bench (kelvin to the pad) and repeat; (2) trace
the slow Vout swing at low bounce; (3) only then re-run #59/#60/#69. Cross-link #77: same root cause
is likely. No spec row or settled-test gate is changed.

## Addendum 2026-11-02 (second increment): kelvin control return, spec package value

Record `records/20261102-issue82-kelvin-typ-5V-27C-250mA.json`; probe `probe82_kelvin.json`,
`bench_kelvin82.spice`, `probe82/buck_top_kelvin.spice` (probe-only copies; `bench.spice` and
`design/netlists/` unchanged). Typical, 5.0 V, 27 C, 250 mA, `--backend local`, 1 unit,
`.tran 2.5n 450u` saved from 20 us (about 840 cycles), l_wire = 2 nH (spec value). **Not settled.**

- Control domain on its own return wire: `gnd_d` stays within about -0.08/+0.10 V while `gnd_p` rings
  -2.2/+1.6 V. Clock 1.80-1.88 MHz (was ~3 MHz, wandering); `vref` reaches 0.591 V and holds.
  The oscillator wander and the vref/fbn corruption of the original symptom are ground bounce.
- Vout still does not regulate: 25 us window means swing -0.04..2.52 V with a ~50-100 us period.
  At 110-150 us duty is 0 with `vc` 0.96-1.26 V below the 1.18 V ramp valley and Vout at -0.88 V
  (forced-CCM sink); `vc` recovers slowly. This second, slow large-signal behaviour is untraced.
- Verdict: **partial**. Bench-artifact part confirmed, but a real package needs a separate control
  return (package/pinout decision, not made), so the design-defect vs artifact call is still open,
  and the slow oscillation is a separate, unresolved loop issue. No decision record, no spec row or
  settled-test gate changed. Next: trace the slow oscillation (ideal-vref / ideal-opamp substitution,
  open-loop `vc` step, averaged-model comparison #17), then settle at 0/50/500 mA before any grid.

## Addendum 2026-11-02 (third increment): the slow oscillation is a small-signal unstable loop (error-amp GBW)

Record `records/20261102-issue82-ea-gbw-typ-5V-27C-250mA.json`; probes under `probe82/`, `bench_gbw82.spice`,
`probe82_gbw.json`, `settled82.py`. Simulated, pre-layout, typical, 5 V, 27 C, 250 mA, one unit / one ngspice run each.

- **The ramp is not the averaged model's ramp.** `osc_ramp` alone (12 uA bias) gives 1.183-1.796 V, 0.613 V p-p, not
  the 0..1.0 V that `design/averaged/buck_avg.spice` assumes. Modulator gain is 1.63x higher: ideal-EA fc moves
  148 -> 224 kHz (PM 62.5 -> 59.0 deg).
- **With the adopted error amplifier in the loop the averaged loop is unstable.** Opamp alone: 93 dB DC gain,
  single pole, unity-gain frequency about 1.1 MHz at 10 uA. Loop gain at the regulated point (Middlebrook,
  `probe82/run_ac_realea.sh`): ideal EA PM +59.0 deg; adopted EA PM **-51.6 deg**, phase -180 deg at 123 kHz with
  +8.7 dB gain (at the 1.0 V ramp of the averaged record: -30.0 deg). `design/compensator.md` already lists the finite
  GBW as not included, and `reuse.lock.json` lists "GBW into the type-III compensation load not yet checked".
- **GBW is the cause, and the bias is not a cheap lever.** A single-pole EA with the same DC gain: 1.1 MHz -> PM
  -15.6 deg, 8 MHz -> +47.8 deg, 100 MHz -> +58.4 deg. The adopted opamp stays unstable when its bias is raised
  (20 uA: -44.0 deg; 80 uA: -34.3 deg), so its output stage / loading also costs margin; not traced further.
- **Switched confirmation.** `bench_gbw82.spice` is the kelvin bench with only the EA replaced by a 100 MHz
  single-pole stand-in. Vout regulates: 25 us window means 1.770-1.775 V from 270 us to 450 us (the earlier runs
  swung -0.9..2.5 V), clock 1.80-1.88 MHz. The slow 50-100 us oscillation and the vc-below-valley lockout were this
  unstable loop hitting the rails, with ground bounce as the separate, earlier effect.
- **Not settled.** `settled82.py` (spec 0.4: consecutive 20-cycle windows, <0.1 % mean Vout, <1 % peak iL): 5 of 15
  consecutive pairs pass, the last three pass, earlier ones show 0.1-0.45 % and 1-11 %. Not claimed as settled.
  Vout sits at 3 x vref = 1.773 V (vref 0.591 V in this bench), 1.5 % under 1.8 V; not examined here.
- **Verdict: design defect in the loop (EA GBW against the type-III compensator), plus the confirmed ground-return
  bench artifact.** The fix is a design decision (resize/replace the adopted EA, or re-tune the compensator against
  a measured EA), so it is **not made here**: see `spec/decision-records/0004-error-amplifier-gbw.md` (proposed).
  No spec row or settled-test gate is changed. The averaged-model R13 evidence (#17) uses an ideal EA and a 1.0 V ramp
  and must not be read as covering this netlist.
- Not done: 0 and 500 mA; other corners; the fix; the settled test; the real-opamp averaged transient waveform
  (the run did not finish in 580 s). Cross-link #77 (R15/R16): the same unstable loop is the likely common cause.
