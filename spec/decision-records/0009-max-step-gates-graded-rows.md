# 0009 — The §0.4 max-step rule gates every graded row: a step violation is no value, not a pass

- **Status**: Recorded 2026-11-14. **No ratified row changed.** §0.4 of [`../target-spec.md`](../target-spec.md)
  is read as written, not relaxed: the collectors are changed to enforce it where three of them did not.
- **Date**: 2026-11-14
- **Raised by**: issue #161, split out of #152 (which single-sourced the rule into `buckmeas.step_check`
  and deliberately changed no verdict rule).
- **Claims made**: none. This record changes no number and re-runs no bench; it fixes what a future
  run is allowed to report.

## 1. Finding

§0.4 fixes the max time step at **T/200** (2.5 ns at 2 MHz) for every graded switching-converter
number, and says "a result record must restate them". Four collectors compute the rule per unit from
the one helper. Measured on `977a286` with
`git grep -n 'step_ok\|step_max_ok' -- 'sim/*/collect.py'`, only one of them read the answer when it
built a verdict:

| Collector | Flag | Read by a verdict on `977a286`? | Rows it feeds |
|---|---|---|---|
| `sim/current-limit/collect.py` | `u["step_ok"]` (assigned line 47) | no | R16 trip window, R16 min bound |
| `sim/load-step/collect.py` | `u["run"]["step_ok"]` (line 83) | no — the `step_ok(r)` function at line 99 is the unrelated per-load-step R12 check | R12, R13(b), R13(c) |
| `sim/steady-state/collect.py` | `u["step_max_ok"]` (line 52) | no | R4, R6, **R7**, R8, R9, R10, R11 |
| `sim/soft-start/collect.py` | `u["step_ok"]` (line 51) | **yes**, line 62: `r15_ok = all(checks.values()) and u["step_ok"]` | R15 |

So a run with a too-coarse step could still produce a `pass` on ten of the eleven rows above. Two
things that look like gates and are not:

- `sim/steady-state/collect.py:46` hands `buckmeas.STEP_MAX_S` to `rawgrade.grade`, but
  `rawgrade.grade` (`sim/lib/rawgrade.py:80-104`) only forwards it to `buckmeas.analyze_columns` to
  produce `res["run"]["step_ok"]`, and then sets `res["graded"] = True` unconditionally once the
  clock is found. Passing the threshold in was evidence plumbing, not a gate.
- R7 is easy to miss in the steady-state list: `rows["R7"] = judge_row(grid, "f_sw_hz", ...)` reads a
  field set only inside the graded/settled branch, so it is gated by the same flag as
  R4/R8/R9/R10/R11. Seven steady-state rows, not six.

`sim/device-stress/collect.py` has no step flag (same grep, no hit) and is out of scope.

## 2. Decision

**A unit whose largest saved time step exceeds the §0.4 limit contributes no value to any graded
row**, exactly like a unit with no waveform. The row is `not_demonstrated` unless another unit fails
it outright.

Applied in `sim/{current-limit,load-step,steady-state}/collect.py` at the point each already
computes the flag, reusing the no-value path each collector already had. The rule itself stays in one
place (`buckmeas.step_check`, with `buckmeas.step_reason` for the wording); no collector carries its
own copy of the threshold.

Why this and not "record it but do not read it": §0.4 is ratified and grants no exception for R16 or
for threshold-crossing measurements, and R16's own grading condition is "in the switched `.tran`".
Leaving a step-violating unit valued would be an unrecorded relaxation of §0.4, which agents may not
make (`spec/README.md`). The R16 trip value is also I(L) read at the TRIP crossing — a waveform
sample on the same time grid the rule constrains.

Rejected: **do not gate, comment only.** That needs a decision record relaxing §0.4 for these rows,
with evidence that each measurement is step-insensitive. Nobody has that evidence.

Rejected: **make a step violation a `fail`.** A coarse run says the run is ungradable, not that the
design is out of bounds, and every collector already had a no-value path for an ungradable unit.

## 3. Two differences left in place deliberately

**Soft-start keeps `fail`, not `not_demonstrated`.** `sim/soft-start/collect.py:62` folds the flag
into `r15_ok`, so a step violation makes R15 `fail` rather than no-value. That is the opposite
disposition to the one decided above, and it is **left as it is** by #161: changing an R15 verdict
rule is its own spec-grading question, not a side effect of this one. Recorded here so the next
reader finds the asymmetry explained rather than rediscovering it. R15 is the only row where a
step violation reads as a design failure.

**R13(c) counts what it withholds; the pre-existing no-waveform drop is untouched.** `r13c` is fed
only graded units, so an ungraded unit leaves its table entirely instead of becoming a `no_value`
entry — and `verdict = ... ("not_demonstrated" if n["no_value"] or not table else "pass")` could
therefore still read `pass` on a silently smaller set. This is visible in committed evidence:
`sim/load-step/records/20261102T081442Z-c8af5c655ffb.json` has `R12.n_units` 106 against
`R13c.n_units` 13, with 93 of 162 units `"graded": false`. Gating without accounting would have
extended that silent narrowing under a change whose whole point is adding a no-value path, so
`r13c` now reports `n_withheld_step_violation` and is `not_demonstrated` when it is non-zero. The
identical drop for **no-waveform** and unlocked-clock units is pre-existing, is **not** fixed here,
and needs its own issue: making R13(c) account for every ungraded unit the way R12 does is a further
change to an existing verdict rule.

## 4. No recorded verdict changes

No committed record holds a unit that violates the rule. Counted per file with
`grep -oE '"step(_max)?_ok": *(true|false)'` over every record under
`sim/{current-limit,load-step,steady-state,soft-start}/records/` on `977a286`: **0 `false`** in every
file, and 21 / 69 / 155 / 33 units `true` in the four grid records (current-limit, load-step,
steady-state, soft-start). The remaining records are the #77 / #82 probe artifacts, which carry no
step flag.

So this decision changes no number already on record. No record was edited and no bench was re-run
for it; `sim/**/records/` is append-only evidence.

## 5. Not established

- Whether any bench **can** produce a step violation in practice on the batch fleet: every unit on
  record is compliant, so the new no-value path is exercised by the unit tests
  (`sim/lib/test_collect_step_gate.py`), not by a recorded run.
- The ≤ 100 ps switching-edge window of §0.4 (gate and SW transitions) is a separate rule. No
  collector checks it today, and none is changed to here.
