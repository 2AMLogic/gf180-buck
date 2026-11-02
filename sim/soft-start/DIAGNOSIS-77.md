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
