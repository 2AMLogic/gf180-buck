# 0007 — Gate-level dead-time detector uses a fixed 0.5 V; R14 grades at the corner's Vth

- **Status**: Recorded 2026-11-07. **No ratified row changed.** R14 of [`../target-spec.md`](../target-spec.md) is read as written, not relaxed.
- **Date**: 2026-11-07
- **Raised by**: issue #123 (sf/125 C flag in `sim/dead-time/records/20261107T215643Z-8b54bed5d40d-corners.json`).
- **Claims made**: simulated, pre-layout, gate-drive level, one unit (sf, 125 C), never measured.

## 1. Finding

`sim/dead-time/deadtime.spice` detects overlap with fixed, deliberately low thresholds (`vtn = vtp = 0.5 V`). R14 does not use a fixed number:
overlap is graded at |Vgs| = the device's Vth for the corner. At sf / 125 C, a Vth-replica probe (constant-current, 100 nA x W/L; same method
as `sim/device-stress/`) reads Vthn = 0.671 V and Vthp = 0.670 V. GL bounces to 0.505 V for one 20 ps sample per period while VIN-GH = 2.64 V.
That is 5 mV over the testbench detector and 166 mV under the R14 threshold. Re-graded at the corner's Vth the probe gives `overlap_max` = 0
(`sim/dead-time/records/20261107T223518Z-a48bd644c3f3-sf125-vth.json`).

## 2. Decision

- The 0.5 V detector stays as a conservative **screen**; a screen hit is not an R14 fail, and a screen hit gets re-graded at the corner's own Vth.
- R14 is graded at the corner Vth in the top-level `device-stress` run (`vthn` / `vthp` replicas), which is the number of record for R14.
- No design change, no spec change. The nf 420 -> 15 change raised the GL bounce by about 20 mV (0.4845 -> 0.505 V); the margin to Vthn at sf/125 C
  stays 166 mV.

## 3. Not established

The top-level (`-top`) dead-time record and the 135-unit `device-stress` grid have not been re-run on the nf = 15 netlist; both remain open on #123.
