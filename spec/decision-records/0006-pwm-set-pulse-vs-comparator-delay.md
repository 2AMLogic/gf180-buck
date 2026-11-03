# 0006 — PWM latch set pulse is as short as the comparator delay

- **Status**: Proposed 2026-11-03. No option chosen; needs an operator ruling.
- **Date**: 2026-11-03
- **Raised by**: issue #77 (`sim/soft-start/DIAGNOSIS-77.md`, Update 8;
  `sim/soft-start/records/20261103-issue77-probe9-clock-set-race.json`).
- **Amends**: nothing. **No ratified row changed**: R15 of [`../target-spec.md`](../target-spec.md) is not edited or relaxed, and no
  settled-test gate moves.
- **Claims made**: simulated, pre-layout, one corner (typical, 5.0 V, 27 C, 3.6 ohm load, start-up transient, ideal bias ports), never measured.

## 1. Finding

In `pwm_comp` the latch is `Q = NOR(RST, QB)`, `QB = NOR(CLK, Q)`, so Q sets only while CLK is high and RST is low. After each clock edge the ramp
resets and the comparator must clear RST before CLK falls. CLK is high 8.0-9.3 ns; RST clears 6.1-10.4 ns after the edge. Over 17 clock edges
(133-143 us), Q set on 8: every edge with `vc` minus the ramp valley >= 0.293 V, and none at <= 0.285 V. PWM then runs near half the clock rate, and two
consecutive missed edges (138.957 and 139.481 us) give a 1.32 us gap and the 20 mV Vout drawdown that fails R15's `monotonic` clause.

Not established: the margin at other corners; the effect of real (non-ideal) bias on either delay; whether the set race also appears in settled regulation.

## 2. Options (none chosen)

| # | Option | What it costs | Spec effect |
|---|---|---|---|
| A | Lengthen the CLK pulse in `osc_ramp` (more delay stages) so it exceeds the worst comparator delay with margin | Netlist change in `osc_ramp`; the maximum duty and the minimum off-time at 2 MHz must be re-checked | none |
| B | Make the set sticky: latch a comparator-high event during the clock window (set-dominant latch or a set-pending flop) so a late RST clear still sets Q | Netlist change in `pwm_comp`; the set must still be defeated by the OCP reset | none |
| C | Adopt the `gf180-comparator` PWM comparator by pinned reference if it covers this | Pin and fit check; not looked at here | none |

## 3. Decision requested

The operator picks A, B or C (or a new option). Until then: spec rows, `design/netlists/` and the settled-test gate are unchanged, and the grids
(#59, #60, #69) must not be re-run on this netlist as evidence for R15.
