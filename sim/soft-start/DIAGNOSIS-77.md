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

## Update 6 — the OCP trip chain ends the on-time at 0.565 A (simulated, pre-layout; not measured)
Evidence: `records/20261103-issue77-probe6-ocp-trip-chain.json`; `bench_ss77_dense.spice`, `probe_ss77_latch.json`,
`probe_ss77_dense.json`, `probe_ss77_ff.json`, `analyze_ss77_trip.py` (probe-only; `design/` and `bench.spice` untouched).
Typical, 5.0 V, 27 C, 3.6 ohm, kelvin return + 100 MHz EA stand-in, local backend, 1 unit per run, step_max 2.5 ns.
Start-up transient only; spec 0.4 settled test not run.

- **Why Update 5 saw no trip.** In a 225-255 us run the PWM falls with `rst` 0 V, `cmp` 3.3 V, `ocpb` 3.3 V and `trip` max
  0.021 V at the saved points, 1.3 ns apart. The trip pulse is shorter than that. A second run adds an unconnected PWL source
  whose 100 ps breakpoints force timepoints (max step 0.053 ns over 226.50-226.70 us).
- **The chain, at the first PWM fall in that run (226.6237 us, I(L) 0.5659 A).** 1.65 V crossings relative to the PWM fall:
  `ocp_sense` `raw` rises -0.714 ns (I(L) 0.5652 A), `trn` falls -0.638, `trip` rises -0.572, `ocpb` falls -0.514, `rst` rises
  -0.395, `q` falls -0.238, `pwm` falls -0.037 ns. `trip` falls again at +0.185 ns, a pulse about 0.76 ns wide that clears when the
  high side turns off. `bld` is already high, so the trip is not blanked.
- **Diagnosis: design defect against R16, at this corner.** The Ron-sense comparator trips at an inductor current of about
  0.565 A. R16's target minimum is 0.70 A (no trip at the 0.635 A peak of a 500 mA load). This is the mechanism Update 5
  inferred: the on-time ends at the current limit, the loop asks for more duty and is overridden, `vc` winds up, and Vout holds
  6 % low. Decision record `spec/decision-records/0005-ocp-trip-below-r16-minimum.md` is raised; R15/R16 are unchanged.
- **Second corner (ff / 5.0 V / 27 C / 3.6 ohm).** Regulates: Vout 1.777 V (280-300 us mean); I(L) at the PWM falls is 0.612-0.613 A
  in steady cycles, `vc` 1.50 V against ramp 1.45 V. Whether the trip or the loop ends the on-time there was not determined (trip
  nets not saved), so the trip point at ff is **not** established. This corner is not a sign-off of anything.
- **Not done:** R16 ramped-load trip test, the trip point over the other corners and temperature, the 0-load case, the
  monotonic drawdown node (the skipped cycle at 139.5-140 us), the grid (#60). Issue stays open.

## Update 7 — R16 ramped-load trip probe, typical corner: trip at 0.554 A (simulated, pre-layout; not measured)
Evidence: `sim/current-limit/records/20261103-issue77-probe8-ramp-trip.json`, `sim/current-limit/probe_ramp77.json` (request only;
`bench.spice`, `design/` untouched). Typical, 5.0 V, 27 C, original R16 bench (ideal bias/rails, current-sink load), local backend,
1 unit, 258 s. `tran 2.5n 420u` saved from 280 us, step_max 2.5 ns verified. The load ramp is shortened to 0 -> 1.5 A over 100 us
starting at 300 us (the grid uses 300 us / 3 A starting at 600 us) so it fits one local job. Steady state **not** established
(Vout 1.665 V at 280 us, I(L) still ringing to -1.07 A at 295 us): a start-up transient, not a settled test.

- I(L) peaks are capped at 0.565-0.573 A from 285 us on, while the load is below that; as the ramp passes the cap Vout falls
  (1.71 V at 330 us, 0.77 V at 360 us, about -0.1 V from 380 us because the bench load is an ideal current sink) and I(L) runs to 1.4-1.6 A.
- The collect.py trip method (first rising 1.65 V crossing of `xtop.trip` after the ramp starts) gives t = 358.9 us, I(L) **0.554 A**,
  load 0.88 A then. R16 requires 0.70-2.1 A. This **fails** the R16 minimum at this corner, matching the 0.5652 A comparator trip traced in Update 6.
- Not done: the other corners and temperatures, the 0-load case, the monotonic drawdown node, a second originally failing corner
  (the ff probe in Update 6 covers an ff regulation case but not the trip), the grid (#60). Decision 0005 still awaits an operator ruling.

## Update 8 — the drawdown node, and a hot, low-supply corner (simulated, pre-layout; not measured)
Evidence: `records/20261103-issue77-probe9-clock-set-race.json`; `probe_ss77_dd.json`, `probe_ss77_dd2.json`, `analyze_ss77_race.py`
(probe-only; `bench_ss77_load.spice`, `bench.spice` and `design/` untouched). Same bench as Update 4 (kelvin return, 100 MHz EA stand-in,
3.6 ohm from t=0), local backend, 1 unit per run, step_max 2.5 ns. Probe 9 typical / 5.0 V / 27 C, `tran 2.5n 143u` saved from 133 us (104 s).
Probe 10 typical / 4.5 V / 125 C (an originally failing unit), `tran 2.5n 260u` saved from 130 us (169 s). Start-up transients; steady state not established.

- **Drawdown node found (R15 `monotonic`).** The 20 mV drawdown at 139.5-140.0 us is two consecutive clock edges (138.957 and 139.481 us) at which the
  `pwm_comp` latch did not set: the PWM falls at 138.689 us and next rises at 140.006 us, a 1.32 us gap against a 0.54 us clock period.
  Vout (vs `gnd_d`) goes 1.111 V to 1.091 V across the gap.
- **Why the set is lost.** `Q = NOR(RST, QB)`, `QB = NOR(CLK, Q)`: Q sets only while CLK is high and RST is low. RST clears when the comparator
  output goes high after the ramp resets. CLK stays high 8.0-9.3 ns; RST clears 6.1-10.4 ns after the clock edge. So the set is won or lost
  inside a 1-2 ns window. Over the 17 edges in 133-143 us, Q set on 8: every edge with vc minus ramp valley >= 0.293 V set it (to 0.493 V), every edge
  <= 0.285 V missed it (from 0.210 V). Alternate edges miss in the settled stretch, so PWM runs near half the clock rate before the two misses in a row.
- **Diagnosis: design defect (R15).** The set pulse is as long as the comparator delay. Decision record
  `spec/decision-records/0006-pwm-set-pulse-vs-comparator-delay.md` is raised (proposed; R15 unchanged). Not checked: real (non-ideal) bias, which
  could move both delays; other corners.
- **Hot corner (typical / 4.5 V / 125 C / 3.6 ohm).** Never reaches 90 %: Vout holds 1.20 V from 180 to 260 us, `vc` at the rail. I(L) is 0.404-0.409 A at
  each of the 117 PWM falls after 200 us. `trip` crossed 1.65 V once in the saved window, at 171.18 us with I(L) 0.407 A. At the later falls
  the trip pulse (sub-ns) falls between saved points, so the chain there is **not traced**. The identical peak current and the one resolved
  trip are consistent with the Update 6 mechanism (`ocp_sense` ends the on-time) at about 0.407 A, below the R16 0.70 A minimum: the same defect
  as decision 0005 at a second corner, with a lower trip point than at typical / 5.0 V / 27 C (0.565 A). Inferred.
- **Not done:** trip point over the other process corners and the cold end; the 0-load case; the grid (#60). With decision 0005 (R16) and 0006 (R15) each
  R15 and R16 now have a diagnosis (design defect plus decision record); the fixes are for the operator rulings and separate issues. No spec row relaxed.
