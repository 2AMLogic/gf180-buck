# 0011 — The §0.4 whole-run max-step rule gates device-stress R2/R14: a step violation is no value, not a pass

- **Status**: Recorded 2026-11-15. **No ratified row changed.** This extends decision record 0009 §2
  ("a step violation is no value, not a pass") to the last collector that computed the §0.4 answer and
  discarded it, and corrects one factual claim in 0009 §5 (§3 here). Nothing in
  [`../target-spec.md`](../target-spec.md) is relaxed.
- **Date**: 2026-11-15
- **Raised by**: issue #170, the follow-up 0009 §1 called for ("`sim/device-stress/collect.py` has no
  step flag ... and is out of scope" of #161 and its PR #167).
- **Claims made**: none. This record changes no number on record and re-runs no bench (§4: no committed
  device-stress unit can violate the rule, so nothing published moves).

## 1. Finding

`sim/device-stress/collect.py` handed `buckmeas.STEP_MAX_S` into `rawgrade.grade` purely as plumbing:
`rawgrade.grade` produces `run.step_ok` and sets `graded = True` unconditionally once the clock is found
(0009 §1), and the collector neither stored a per-unit step flag nor read one in a verdict — one grep
hit, the argument itself. `status_of` gated `pass` on `u.get("settled")` and
`(u.get("edge") or {}).get("ok")` only, so a run whose largest saved step exceeded §0.4's T/200 limit
could still read `pass` on R2 (device stress) and on the R14 dead-time value the same units feed.

The uncovered case is narrower than in the collectors #167 gated, and the record should say so
precisely: device-stress is the only collector that already enforced part of §0.4. Its bench requests a
uniform 100 ps step over the whole run (`request_grid.json`'s analysis args), and `status_of` gated
`pass` on `edge.ok`, which `stressmeas.edge_resolution` sets False when any step inside a
`[-2 ns, +10 ns]` edge window exceeds 100 ps. What was ungated was the **whole-run** T/200 rule: a run
with steps ≤ 100 ps inside every edge window but > `buckmeas.STEP_MAX_S` somewhere between them had
`edge.ok == True` and `settled == True`, and read `pass`.

## 2. Decision

**device-stress follows 0009 §2 as written**: a unit whose largest saved time step exceeds
`buckmeas.STEP_MAX_S` (to `STEP_TOL`) contributes no value to R2 and to R14, exactly like a unit with
no waveform. The row is `not_demonstrated` unless another unit fails it outright. Implemented as an
early return in `unit_record`, immediately after the time column is read and before
`stressmeas.stress_peaks` / `edge_resolution` / `rawgrade.grade` run: the unit records its step
evidence (`step_max_s`, `step_ok`) and `buckmeas.step_reason`'s wording, and carries no peaks and no
dead time.

Leaving `peaks` and `dead_time` unset is what makes the gate complete, not just kind: `judge` builds
its `valued` list — and with it the row's `binding` unit — from the margin, not from the status, so a
gate added only in `status_of` would return `no_value` while still letting the step-violating unit be
reported as the row's binding R2/R14 value. With the early return, `r2_margin` and `r14_margin` both
return `None` naturally and the unit drops out of `pass`, `fail`, `valued` and `binding` together, with
no change to `status_of`, `judge`, `r2_margin` or `r14_margin`. One gate covers both rows because both
are judged from the same `unit_record`.

The threshold and the wording stay in `buckmeas.step_check` / `buckmeas.step_reason`; no copy of the
2.5 ns limit exists under `sim/device-stress/` — enforced by
`sim/lib/test_collect_step_gate.py::StepReasonTest::test_no_collector_carries_its_own_copy_of_the_threshold`,
which now enumerates this bench too.

**The soft-start asymmetry of 0009 §3 is untouched.** R15 keeps its `fail` disposition. This record
introduces no new asymmetry: it applies the general rule 0009 §2 already decided to the one bench 0009
§1 had left out of scope.

Why this and not the alternatives:

- **Rejected: gate inside `status_of`.** Leaves the unit in `valued`, so it can still be reported as
  the row's binding value with its margin (above).
- **Rejected: make a step violation a `fail`.** 0009 §2 rejected this explicitly, and the same reason
  holds here: a coarse run says the run is ungradable, not that the design is out of bounds.
- **Rejected: record the flag but do not read it.** That is the status quo this record closes — an
  unrecorded relaxation of §0.4, which agents may not make (`spec/README.md`).
- **Rejected: tighten the gate to the bench's own 100 ps request.** §0.4's "Max time step" row carries
  two rules — the whole-run T/200 limit and the ≤ 100 ps edge-window resolution — and only the whole-run
  one was ungated. What a valid run may *request* is its own question; `edge.ok` already enforces the
  edge half and is unchanged here.

## 3. Correction to 0009 §5

0009 §5 says of the ≤ 100 ps switching-edge-window rule: *"No collector checks it today, and none is
changed to here."* The first half was wrong when written: `sim/device-stress/collect.py` checks it —
`stressmeas.edge_resolution` runs on every waveform the collector grades, and `status_of` gates `pass`
on its `ok` (verified on `a13150c`: the only `edge_resolution` caller under `sim/*/collect.py`). 0009
§5 was surveyed while §1 held device-stress out of scope, and the survey missed this collector. This
record corrects the claim instead of editing 0009: the edge rule was already enforced here, the rule
that was genuinely ungated was the whole-run T/200 one, and this issue changes only the latter. `edge.ok`
behaviour is unchanged.

## 4. No recorded verdict changes

`grep -ohE '"step(_max)?_ok": *(true|false)'` over every file under `sim/device-stress/records/` and
every `*-top.json` under `sim/dead-time/records/` returns no matches: no committed device-stress unit
carries a step flag at all, which is the gap itself. The one committed record
(`sim/device-stress/records/20261102T083205Z-c8af5c655ffb.json`, with its R14 top-level twin
`sim/dead-time/records/20261102T083205Z-c8af5c655ffb-top.json`) has all 3 units at
`edge.max_step_s = 1.0e-10` s — 25x under the T/200 limit — and both rows already read `fail` on margin
(R2 binding −4.4049, R14 binding −1.0944e-07), so the new gate is inert on every number on record twice
over. The bench requests a uniform 100 ps step (`request_grid.json`), which is why no committed unit can
violate the rule and why this gap was latent rather than a wrong number.

So this decision changes no number already on record. No record was edited and no bench was re-run for
it; `sim/**/records/` is append-only evidence. The new no-value path is exercised by unit tests on
synthetic rawfiles (`sim/lib/test_collect_step_gate.py::DeviceStressStepGateTest`), like every other
collector 0009 gated.
