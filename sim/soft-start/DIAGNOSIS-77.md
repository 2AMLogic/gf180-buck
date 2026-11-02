# Issue #77 — R15 start-up diagnosis (partial, simulated, pre-layout)

Evidence: `records/20261102-issue77-probe-typ-5V-27C-noload.json`, from the two single-corner
requests `probe_single.json` (700 us) and `probe_single2.json` (450 us, adds vc/pwm/fbn).
Corner: typical, 5.0 V, 27 C, no load. `--backend local`, 1 unit each, step_max 2.5 ns.
Steady state was **not** established; these are start-up transients. Nothing here is measured.

## What was seen
- Oscillator: 1.94 MHz (300-400 us). Soft-start reference: ramps from EN, saturates ~1.18 V
  (loop target ~1.77 V). Neither deviates at this corner.
- PWM stays low (duty <= 0.04) until ~160-180 us although the reference rises from 20 us.
  `vc` sits at 1.30-1.44 V inside the ramp window 1.17-1.80 V. Cause not traced.
- After ~180 us duty is 0.31-0.36 and Vout median is 1.39-1.52 V against a 1.62 V (90 %)
  threshold: the loop does not close within the window.
- From ~180 us `vc` leaves the 3.3 V rail (-0.92 V .. +5.5 V), coincident with single-sample
  +/-2 V spikes on `v(out)` at SW edges. Physical or bench-model artifact: **not traced**.

## Verdict
Partial. First departing block at this corner: PWM/compensator path, not the oscillator or
soft-start reference. Ideal-bias ports not implicated here. Design defect vs bench artifact is
undecided, so no decision record is written. No spec row is changed. Not probed: other corners,
the 3.6 ohm load, R16. Suggested next step: re-run this corner with the `out` spike path
(Cwind/Rwind/ESL placement) varied and the `pwm_comp` comparator inputs saved.

## Update 2 — die-ground reference (simulated, pre-layout; not measured)
Evidence: `records/20261102-issue77-probe2-gnd-reference.json` (requests `probe_single3/4/5.json`,
same corner, local backend, one unit each). The record above is untouched.

- **Bench artifact found.** `v(gnd_d)` bounces about -3..+3 V (bench package ground, 1 nH + 0.05 ohm,
  at every SW edge). Referenced to `gnd_d`, `vc` is 0.74-2.16 V (in the 3.3 V rail) and `out` has no
  spikes (0.06-1.91 V over 180-260 us). The "vc out of rail" and "+/-2 V out spikes" above came from
  absolute probes. Removing Cwind (3 pF to 0.05 pF) did not change them.
- **Still unexplained.** Referenced to `gnd_d`, Vout averages ~1.55 V over 400-700 us (40 us windows
  1.52-1.62 V), against the 1.62 V threshold and 1.8 V target. Cause not traced.
- **Open question.** The bench returns Cout/ESL and Rload to `gnd_d`, not node 0, so the bounce is
  injected into the output. Whether that return is realistic is not decided.
- Same-corner Vout at 700 us varied between runs (1.557 V vs 1.672 V); cause not traced.

Verdict: still partial. No design defect established, no decision record, no spec row changed.
Suggested next step: a bench variant returning Cout/Rload to node 0, and probing `vref`, `fbn`
and PWM duty against `gnd_d` for the Vout shortfall.

## Update 3 — kelvin control return + non-limiting EA (simulated, pre-layout; not measured)
Evidence: `records/20261102-issue77-probe3-ea-gbw-kelvin.json`; `bench_ss77.spice`, `probe_ss77.json`,
`analyze_ss77.py` (probe-only; `bench.spice` and `design/` untouched). Typical, 5.0 V, 27 C, no load,
`--backend local`, 1 unit, `.tran 2.5n 700u` saved from 15 us, step_max 2.5 ns. The bench is #82's
`bench_gbw82.spice` (separate control-ground wire; 100 MHz single-pole EA stand-in) with the load removed.

- **The corner starts up.** t_90 = 175.6 us after EN (R15: 100-500 us), peak I(L) 0.405 A (< 0.70 A),
  no overshoot above 1.872 V, Vout 1.772-1.774 V from 260 us. Clock 1.86 MHz; `vc` inside the ramp
  window from 60 us. Oscillator, bias ports and soft-start reference do not deviate.
- **Not a pass of R15.** `monotonic` fails against the 1 mV tolerance: a 20.7 mV drawdown of the cycle
  mean at 187 us (Vout about 1.52 V), cause not traced. Vout ends 1.5 % under 1.8 V (as in #82).
  Steady state was not tested against spec 0.4.
- **Diagnosis.** The R15 failures seen at the first probes are the two causes found under #82: die-ground
  bounce (bench artifact, fixed in the kelvin variant) and the unstable loop with the adopted error
  amplifier (design defect, `spec/decision-records/0004-error-amplifier-gbw.md`, proposed, unchosen).
  Neither the oscillator, the bias ports nor the soft-start reference is at fault at this corner. The
  stand-in EA and the control-return pinout are open decisions, so the adopted netlist is **not** shown
  to pass.
- **Not done:** other corners, the 3.6 ohm load, R16 trip behaviour (not probed), the drawdown, the
  grid. No decision record is added (0004 covers the defect); no spec row changed.

## Update 4 — 3.6 ohm load (simulated, pre-layout; not measured)
Evidence: `records/20261102-issue77-probe4-load-3p6.json`; `bench_ss77_load.spice`, `probe_ss77_load.json`
(probe-only; analysed with `analyze_ss77.py`). Typical, 5.0 V, 27 C, 3.6 ohm from t=0, kelvin control
return + 100 MHz EA stand-in, local backend, 1 unit, `.tran 2.5n 700u`, step_max 2.5 ns. Start-up
transient only; the spec 0.4 settled test was not run.

- Starts up: t_90 181.8 us after EN, peak I(L) 0.571 A (< 0.70 A), no overshoot. Clock 1.84 MHz.
- Not a pass: monotonic fails (18.9 mV drawdown, cause not traced), and Vout holds 1.692 V (6 % low)
  while `vc` climbs to the 3.3 V rail by ~580 us and stays there. Cause not traced; a possible
  design defect (control authority) is untested, so no decision record.
- Not done: monotonic drawdown trace, a second failing corner, R16 trip probe. Issue stays open.

## Update 5 — what ends the on-time at the 3.6 ohm load (simulated, pre-layout; not measured)
Evidence: `records/20261102-issue77-probe5-ontime-termination.json`. Same bench and corner as Update 4
(`bench_ss77_load.spice`: typical, 5.0 V, 27 C, 3.6 ohm from t=0, kelvin return, 100 MHz EA stand-in), local
backend, 1 unit per run, step_max 2.5 ns. Two new short runs (`probe_ss77_trip.json`: 0-300 us, saves `xtop.trip`;
`probe_ss77_cmp.json`: 0-250 us saved from 200 us, saves the `pwm_comp` and `ocp_sense` internals), plus
re-analysis of the Update 4 waveform. Start-up transient only; spec 0.4 settled test not run.

- **The PWM on-time ends at a fixed inductor current.** From ~100 us every cycle's I(L) peak is 0.565 A
  (0.562-0.564 A at the PWM falling edge, 280 us and 240 us windows), while the PWM-high fraction (0.49-0.53) is
  well above the SW-high fraction (0.34-0.37) over 260-300 us. The loop is not setting the duty: `vc` is 1.75 V
  against a ramp that is still at 1.43 V when PWM falls.
- **It is not the `pwm_comp` comparator, reset or OCP-trip net.** At the falling edge `xpwm.cmp` stays 3.3 V,
  `xpwm.rst` 0 V, `xpwm.ocpb` 3.3 V, and `xtop.trip` never exceeds 0.41 V (never above 1.65 V, 0-300 us).
  `ocp_sense` internals do move: `v2` exceeds `v1` from ~240.23 us (I(L) ~0.51 A) and both jump at the PWM edge.
  The path from there to the PWM pin is **not traced** (no nets saved between the latch and the PWM output).
- **So the 6 % Vout shortfall and the `vc` windup are consistent with a peak-current termination below the R16
  minimum.** Average I(L) is 0.455-0.461 A at 1.692 V into 3.6 ohm; with the peak pinned at 0.565 A the on-time
  cannot grow, and the integrator walks `vc` to the 3.3 V rail (Update 4). This is an inference from timing and
  current, not a traced mechanism.
- **R16 consequence.** Spec R16 (target) requires no trip at 500 mA load up to a peak of 0.635 A and a trip
  minimum of 0.70 A. A termination at 0.563 A, with the load at 0.47 A average, is below both. If it is the
  current-limit path, R16's minimum is violated at this corner; the unit at no load never reaches the current.
- **Drawdown (R15 `monotonic`, 18.9 mV by `buckmeas`, 17.8 mV by per-clock-cycle means).** It sits at 139.5-140.0 us,
  Vout ~1.09 V on the ramp: one cycle has peak 0.223 A (valley 0.045 A) between cycles of 0.41/0.51 A, then the
  first 0.570 A peak follows at 140.55 us. A short or skipped on-time cycle as the loop hands over to the 0.565 A
  termination. Not a bench-ground effect (kelvin variant); node cause of the skipped cycle not traced.

Verdict: still partial, but narrowed. The unit starts in range; the remaining R15 failures (monotonic, 6 % low)
and the R16 early trips share one unexplained mechanism: a fixed ~0.563 A peak termination not visible on
`trip`/`ocpb`. No decision record is written because the mechanism is untraced; no spec row, design netlist or
earlier record changed. #82 (EA/loop) is not the cause of this: the loop asks for more duty and is overridden.
Next: save `pwm_comp` nets between the latch (`q`) and `pwm`, and the `ocp_sense` output stage (`raw`, `trn`), at
one cycle near 240 us (a 30 us window is enough), then either file the decision record (R16 minimum violated)
or mark it a bench artifact. Not done: a second failing corner, the R16 ramped-load trip test, the grid (#60).
