# spec

The ratified specification and its decision records.

| File | What it is |
|---|---|
| [`target-spec.md`](target-spec.md) | The target specification: target, fallback and stretch tiers, one row per parameter, each with min / typ / max, grading condition, corner set and external parts |
| [`decision-records/0001-ratify-target-spec.md`](decision-records/0001-ratify-target-spec.md) | Ratifies the spec; records the electromigration budget method, the thick-MetalTop rule coverage in `klt`, the control and stability method, and the adopt-or-keep decisions on the same-PDK siblings |
| [`decision-records/0002-pdk-variant-pins.md`](decision-records/0002-pdk-variant-pins.md) | Relates the spec's `gf180mcuA` PDK pin to the simulation pin `gf180mcuD`: which results depend on which variant |
| [`decision-records/0003-control-rail.md`](decision-records/0003-control-rail.md) | Fixes the 3.3 V control rail: a dedicated VIN-fed linear regulator, the supply range every adopted sibling sees, and the quiescent accounting against R9 |
| [`decision-records/0004-error-amplifier-gbw.md`](decision-records/0004-error-amplifier-gbw.md) | Proposed (not ratified): error-amplifier GBW against the type-III compensator, options and the decision requested (issue #82) |
| [`decision-records/0005-ocp-trip-below-r16-minimum.md`](decision-records/0005-ocp-trip-below-r16-minimum.md) | Proposed (not ratified): the Ron-sense current limit trips below the R16 minimum, options and the decision requested (issue #77) |
| [`decision-records/0006-pwm-set-pulse-vs-comparator-delay.md`](decision-records/0006-pwm-set-pulse-vs-comparator-delay.md) | Proposed (not ratified): PWM latch set pulse as short as the comparator delay, options and the decision requested (issue #77) |
| [`decision-records/0007-deadtime-detector-vs-corner-vth.md`](decision-records/0007-deadtime-detector-vs-corner-vth.md) | Recorded (no ratified row changed): the gate-level dead-time detector is a 0.5 V screen; R14 grades at the corner's Vth (issue #123, sf/125 C) |
| [`decision-records/0008-ea-input-common-mode.md`](decision-records/0008-ea-input-common-mode.md) | Proposed (not ratified): move the error-amplifier input common mode into the op-amp's 1.20 - 2.70 V range; R4 and start-up closure stay conditional on three open items (issue #131) |
| [`decision-records/0009-max-step-gates-graded-rows.md`](decision-records/0009-max-step-gates-graded-rows.md) | Recorded (no ratified row changed): the §0.4 max-step rule gates every graded row — a step violation is no value, not a pass; soft-start's R15 `fail` and R13(c)'s withheld count (issue #161) |
| [`../reuse.lock.json`](../reuse.lock.json) | The pinned sibling references behind the adopt-or-keep table |

A change to a ratified number needs a new decision record in
`decision-records/`; agents do not relax a row to make a result pass.
