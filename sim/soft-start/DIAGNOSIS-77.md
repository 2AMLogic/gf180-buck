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
