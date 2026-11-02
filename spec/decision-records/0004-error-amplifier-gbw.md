# 0004 — Error-amplifier GBW against the type-III compensator

- **Status**: Proposed. Not ratified: the path in §3 is a PO-level choice and is **not made by this record**.
- **Date**: 2026-11-02
- **Raised by**: issue #82 (`sim/steady-state/DIAGNOSIS-82.md`, third addendum;
  `sim/steady-state/records/20261102-issue82-ea-gbw-typ-5V-27C-250mA.json`).
- **Amends**: nothing. **No ratified row changed**: no row of [`../target-spec.md`](../target-spec.md) is edited,
  R13 (PM >= 45 deg, GM >= 10 dB, fc 100-250 kHz) is not relaxed, and no settled-test gate moves.
- **Claims made**: simulated, pre-layout, typical corner only, never measured.

## 1. Finding

With the adopted `error_amplifier` (`reuse.lock.json`, `gf180-opamp` at `cda7ff5`, 10 uA bias) in the type-III
compensator and the real ramp window (0.613 V p-p), the averaged loop gain at 5 V / 250 mA has PM -51.6 deg (phase
-180 deg at 123 kHz, +8.7 dB). The averaged R13 evidence (#17) used an ideal EA and a 1.0 V ramp (PM 62.5 deg) and does
not cover this netlist. Replacing only the EA by a single-pole stand-in of 8 MHz GBW gives PM +47.8 deg; at 1.1 MHz,
-15.6 deg. The switched bench regulates once the EA's GBW is not limiting and does not otherwise.

## 2. Options (none chosen)

| # | Option | What it costs | Spec effect |
|---|---|---|---|
| A | Obtain an EA with >= about 8 MHz GBW into the type-III load (change at `gf180-opamp`, adopt the new sha, or size one here) | A sibling change or a second EA: `CLAUDE.md` says do not size a second one by accident | none |
| B | Re-tune the compensator against the measured EA (lower fc, move fp1/fp2) | fc falls out of the R13 100-250 kHz band, so R13 or R12 would need a ratified change | R13/R12 |
| C | Raise the EA bias | Measured not to fix it (PM -34 deg at 80 uA); also a supply-current (R9) cost | none, ineffective |

## 3. Decision requested

The operator picks A or B (or a new option). Until then: spec rows, `design/netlists/` and the settled-test gate are
unchanged, and the grids (#59, #60, #69) must not be re-run on this netlist.
A second, separate call is open from #87: whether the package has a separate control-ground return (pinout).
