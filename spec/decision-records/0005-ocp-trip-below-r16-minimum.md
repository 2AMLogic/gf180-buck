# 0005 — Ron-sense current limit trips below the R16 minimum

- **Status**: Proposed 2026-11-03. No option chosen; needs an operator ruling.
- **Date**: 2026-11-03
- **Raised by**: issue #77 (`sim/soft-start/DIAGNOSIS-77.md`, Update 6;
  `sim/soft-start/records/20261103-issue77-probe6-ocp-trip-chain.json`).
- **Amends**: nothing. **No ratified row changed**: R15 and R16 of [`../target-spec.md`](../target-spec.md) are not edited
  or relaxed, and no settled-test gate moves.
- **Claims made**: simulated, pre-layout, one corner (typical, 5.0 V, 27 C, 3.6 ohm load, start-up transient), never measured.

## 1. Finding

With the netlists as adopted, the `ocp_sense` comparator ends the high-side on-time at an inductor current of about 0.565 A.
Traced at 0.05 ns resolution: `raw` -> `trn` -> `trip` -> `ocpb` -> `rst` -> `q` -> `pwm` within 0.7 ns, I(L) 0.5652 A at `raw`,
`bld` already high (not blanked). R16 (target) requires a trip minimum of 0.70 A and no trip at a 500 mA load with a 0.635 A peak.
At this corner the converter therefore cannot supply 500 mA: Vout holds 1.692 V into 3.6 ohm (average I(L) about 0.46 A) and the
integrator winds `vc` to the 3.3 V rail. The same start is clean when the current stays below the threshold (no-load probe).

Not established: the trip point at the other corners and temperatures (an ff probe regulated at I(L) peaks of 0.613 A, with the
cause of its on-time end undetermined), the 0-load behaviour, and the R16 ramped-load trip test.

## 2. Options (none chosen)

| # | Option | What it costs | Spec effect |
|---|---|---|---|
| A | Raise the `ocp_sense` threshold (the `IBIAS_OCP` current or the `RT` reference divider) so the 3 : 1 `Ron`-sense window sits at 0.70-2.1 A | A netlist change in `ocp_sense`; the max bound (2.1 A) and R9 supply current must be re-checked | none |
| B | Move the sense to a ratioed sense FET (R16 notes this tightens the window) | New sensing structure and layout area | needs its own decision record per R16 |
| C | Adopt the `gf180-gate-driver` current-limit work by pinned reference if it covers this | Pin and fit check; not looked at here | none |

## 3. Decision requested

The operator picks A, B or C (or a new option). Until then: spec rows, `design/netlists/` and the settled-test gate are unchanged,
and the grids (#59, #60, #69) must not be re-run on this netlist as evidence for R15 or R16.
