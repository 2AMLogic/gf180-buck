# device-stress: R2 and top-level R14 on `buck_top`

Simulated, pre-layout, never measured. Target tier (spec `target-spec.md` §1).

| Row | Limit | Corners x loads | Where graded |
|---|---|---|---|
| R2 | SW >= -0.7 V; every power-device terminal-to-terminal voltage (Vgs, Vds, Vgd of both devices) <= 6.0 V; peaks over the saved window, no transient credit | C-full (45) x {0, 50, 500 mA} = 135 units | `records/` here |
| R14 | dead time 1..6 ns (typ 3 ns) at the gates, at \|Vgs\| = the device's Vth for that corner; **zero overlap** | same 135 units | `../dead-time/records/*-top.json` |

## What is new versus `sim/dead-time/` (gate-drive level, #33)

`sim/dead-time/deadtime.spice` drives `gate_drive` + `power_stage` open loop with a DC sink on SW, typical
corner, 0.5 V conservative overlap thresholds, no package. This bench is the closed-loop `buck_top`
(oscillator, PWM comparator, compensator, OCP, soft start) with the external P-T parts, the spec §0.3
package (2 wires per net, typical R and L), C-full x loads, and each corner's **own** Vth. It does not
replace the gate-drive bench; the two answer different questions.

## Bench

`bench.spice` is the shared closed-loop harness `sim/lib/bench_harness.spice` -- the package, die
decoupling, control-domain sources, `buck_top` instance and external L/C that all five closed-loop benches
include, kept in one file (issue #151; a unit test fails if a deck stops including it or re-declares one of
its cards) -- with the steady-state load card and two **Vth replicas** at the end: a 10 um copy of each
power device (`nfet_06v0` L 0.7 u, `pfet_06v0` L 0.55 u) diode-connected at 100 nA x W/L. The node level
is that corner's constant-current Vth (typical, 27 C, 5 V: Vthn 0.686 V, Vthp 0.889 V in the probe), read
as the `vthn` / `vthp` measurements. It is the threshold the spec asks for (the minimum Vth over the
corner is the corner point's own Vth, the corner axes being process x T). Netlists are not changed.

`Vsrc` is the one shared card the harness does not own: `klt` rescales that PWL per corner, which it can do
only in the top-level deck, so every bench keeps its own copy of it (the unit test asserts this).

## Run length, step, steady state

- `.tran 100p 600u 540u 100p`: **100 ps max step over the whole run**, waveforms saved from 540 us (60 us).
  ngspice cannot vary the max step inside one run, and the default tolerances leave steps of 1.8-2.5 ns on
  the edges (probe: 545 SW-edge steps, largest 1.8 ns; `reltol=1e-4` still left 1.17 ns inside the edge
  window and cost 40 % more runtime), so the spec §0.4 edge window is met by stepping the whole run.
- Cost: ~6 M points per unit, ~0.19 ms/point in the quiet start-up, so a unit is ~20-55 min on the fleet.
  One unit per job, `timeout_s` 3300 (the fleet's whole-job ceiling is 3600 s). The 135-unit grid at 12 jobs
  in flight is several hours of fleet time; it is not run here (below).
- Edge window: [-2 ns, +10 ns] around every mid-swing crossing of SW and of both gates (the +10 ns covers
  the bond-wire ringing). `units[].edge.max_step_s` is the largest step inside them; a unit with any step
  above 100 ps cannot pass.
- Steady state: spec §0.4 via `sim/lib/rawgrade.py` / `buckmeas` (two consecutive 20-cycle windows,
  < 0.1 % mean Vout and < 1 % peak I(L)). `measure_window_s` and `settled_since_s` are per unit.

## Verdict rules (`collect.py`; nothing relaxed)

- A limit exceeded anywhere in the saved window **fails** the unit, settled or not (a coarser step can only
  under-read a peak, and R2 takes no transient credit). Overlap seen anywhere also fails R14.
- A **pass** needs: settled, every edge-window step <= 100 ps, all values inside their limits.
- A row is `pass` only if the full 135-unit grid is present and every unit passes (a subset such as C-typ never passes, whatever `--set` names); any other outcome without a
  failure is `not_demonstrated`. A unit that timed out, errored or was lost has no value.
- R2 grades SW as the lower of the die-side level and the level against the die ground (the substrate-diode
  clamp is die side); terminal peaks use the die-side `vin_d`, `sw_d`, `gnd_d` and the gates `xtop.gh`, `xtop.gl`.
- R14 dead time is measured per transition pair in the measurement window: LS gate Vgs falling through
  Vthn to the HS Vsg rising through Vthp, and HS Vsg falling through Vthp to the LS Vgs rising through Vthn.

## What ran (first record: 2026-11-02, commit c8af5c655ffb, ngspice-46 on the batch fleet)

Only the **C-typ x {0, 50, 500 mA}** subset (`request_ctyp.json`, 3 units) ran: the 135-unit grid does not
fit one session (above) and is the open remainder of #58. Both records are below the 45-point set, so
neither row can read `pass`; they can only `fail` or be `not_demonstrated`.

| Unit (typical, 27 C, 5.0 V) | settled | SW min | worst terminal | R14 dead time (min..max) | overlap |
|---|---|---|---|---|---|
| 0 mA | no | -2.07 V | LS Vgd 10.29 V | 1.48 .. 3.20 ns | >0 (<= 45 ns in 60 us) |
| 50 mA | no | -2.07 V | LS Vgd 9.78 V | 1.52 .. 3.20 ns | >0 (<= 45 ns) |
| 500 mA | no | -1.58 V | HS Vds 6.54 V | 3.08 .. 3.16 ns | >0 (<= 110 ns) |

- **R2 fails** on all three units (SW below -0.7 V; terminal peaks above 6.0 V). **R14 fails** on zero overlap
  on all three units, although every measured dead time is inside 1..6 ns.
- All three runs are **unsettled** under spec §0.4 (as in #57). The failures stand because a limit
  exceeded anywhere in the saved window fails the unit; the *values* are from an unsettled switching state
  and say nothing about the settled converter. A settled re-run needs the settling fix tracked from #57.
- Edge resolution holds in all three: largest step inside the edge windows is exactly 100 ps (787-924 windows).
- The R14 overlap mechanism, from the raw: while SW rises, the die ground bounces to about -1 V and the
  LS gate stays near 0 V, so the LS device's Vgs (gate to its own source) reaches ~+1.0 V, above the corner's
  0.686 V Vth, for 0.1-0.3 ns. Overlap is an upper bound quantised to the 100 ps step.
- Not run: the other 44 corner points x 3 loads, so no binding corner over C-full is known.
  Every number is simulated, pre-layout; it is not measured, and post-layout ringing is #27.
