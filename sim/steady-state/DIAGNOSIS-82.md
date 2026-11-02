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
