# 0010 — R13(c) accounts for every withheld unit: per-reason counts, and `not_demonstrated` when any is non-zero

- **Status**: Recorded 2026-11-15. **One ratified row's entitlement to read `pass` is narrowed**: R13(c)
  (sim/load-step/collect.py) now reports every unit it withholds from its table, by reason, and reads
  `not_demonstrated` whenever any unit was withheld. The pass criterion itself is unchanged.
- **Date**: 2026-11-15
- **Raised by**: issue #171, the follow-up decision record 0009 §3 called for ("making R13(c) account
  for every ungraded unit the way R12 does is a further change to an existing verdict rule"); #167
  (which implemented #161) added the step-violation count and listed the rest as out of scope.
- **Claims made**: none. This record changes no number on record and re-runs no bench; it changes what
  a future run is allowed to report (§4: no committed R13(c) `pass` was ever reached on a narrowed
  table, so nothing published is retracted).

## 1. Finding

`r13c` grades a cross-check — the switched load-step result against the averaged-model prediction,
per unit — and computes its verdict from the rows that reach its table. It filters its inputs to
graded units, so a unit that never reaches the table cannot make the row anything but more
`pass`-like. Before this record, exactly one withhold cause was counted (a §0.4 step violation,
added by #167 as `n_withheld_step_violation`, keyed on `(u.get("run") or {}).get("step_ok") is
False`); the other two causes left the table with **no count and no note anywhere on the row**:

| `grade_unit` ungrading path | Ungrades at | Written before the return? | Old count saw it? |
|---|---|---|---|
| no waveform (`recordkit.waveform_or_reason`) | before `u["run"]` exists | no | **no** |
| unlocked clock (`rawgrade.clock_from_crossings`) | before `u["run"]` exists | no | **no** |
| §0.4 step violation (`buckmeas.step_check`) | after `u["run"]` is written | yes | yes |

So a count keyed on `run.step_ok` structurally cannot see two of the three causes — it keys a proxy
that only one cause sets. Measured on the only committed load-step record
(`sim/load-step/records/20261102T081442Z-c8af5c655ffb.json`): 162 units, **93 ungraded** (9 of 18
`tol`, 84 of 90 `full`, 0 of 54 `avg`), all with the single reason `"no waveform: klt status error
['lost_shard']"`; zero unlocked-clock drops and zero `run.step_ok is False` among graded units.
R12 counts the same units as no-value steps and reads `not_demonstrated` at `n_units` 106; R13(c)
simply had a smaller table (13). **The #167 counter would have counted none of the real population.**
R12 already gets this right on the same bench and the same units, so this is R13(c) being brought to
an existing discipline, not a new one.

## 2. Decision

**R13(c) accounts for every unit withheld from its table, on the invariant itself**: a unit with
`graded: false` is not in the table, so every such unit handed to the row is counted — bucketed by a
stable reason classifier (`withheld_reason_key`: `step_violation` / `no_waveform` /
`unlocked_clock`) — and the row reads `not_demonstrated` whenever any withheld unit exists:

```
"fail" if n["fail"] else ("not_demonstrated" if n["no_value"] or withheld or not table else "pass")
```

(`fail` still outranks `not_demonstrated`; a withheld unit cannot mask an out-of-bounds result.)
Keys off `graded`, not off `run.step_ok` or any other per-cause proxy, so a **future fourth
ungrading cause is counted automatically** — it lands in the closest bucket rather than being
silently dropped — which is the recurrence this record exists to close. The raw free-text `reason`
still rides along per unit in the record's `units`.

Why this and not the alternatives:

- **Rejected: emit withheld units as `no_value` table entries (R12's shape).** Arguably the better
  long-term form, but it changes the `table` schema downstream readers and the `--dry` brief already
  consume, widening a verdict-honesty fix into a schema migration. Recorded here as the considered
  alternative, not built.
- **Rejected: extend the `run.step_ok`-keyed predicate with extra per-cause predicates.** Each new
  cause needs a new predicate, so the next one is silently dropped again; and two of the three
  present causes never write `run` at all, so the predicate family cannot see them even today.
- **Rejected: keep the `graded` filter at the call site and count there.** Accounting outside the
  function that owns the verdict is exactly how the gap arose; it would also revert #167's
  structural improvement (callers pass unfiltered sets; the filter lives inside `r13c`).

## 3. Row shape

The withheld accounting is on the row, machine-readable:

- `n_withheld` — every ungraded unit handed to the row, both sides;
- `n_withheld_switched` / `n_withheld_averaged` — the same, per side. **`n_units +
  n_withheld_switched` is the switched population the row was handed** — the denominator identity
  the narrowing broke (on the committed record: 13 + 93 = 106). The split is needed because the
  table holds one entry per *graded switched* unit: a graded averaged unit whose switched
  counterpart is withheld contributes no table entry, and the corner is still accounted by the
  withheld switched unit (no silent drop either way);
- `n_withheld_by_reason` — counts per stable bucket;
- `withheld_units` — the withheld unit ids, per bucket;
- `withheld_note` — now states that **every** cause is counted. #167's note said the opposite
  ("Units withheld for no waveform or an unlocked clock are not counted") and would have become
  false the moment this landed.

The classifier buckets a not-graded unit by what it carries: a `run` dict with `step_ok: false` is
the §0.4 gate (decision record 0009); a reason beginning `"no waveform"` failed before any waveform
existed; anything else that got past the waveform check failed the clock extraction. The raw reason
strings stay free text and are never used as bucket keys. `n_withheld_step_violation` /
`withheld_step_violation_units` (added by #167, present on no committed record) are replaced by the
general form.

**The first-wins corner dedupe in `main()` is unchanged.** On the committed record, one of the 93
withheld units is a dedupe artefact rather than a genuinely unmeasured corner (a *graded* `full`
copy discarded behind an *ungraded* `tol` copy of the same corner). The per-reason counts do not
distinguish it. Fixing the dedupe ordering moves R12 and R13(b) as well, so it is deliberately out
of scope here.

## 4. No recorded verdict changes

Re-measured at implementation time, not assumed from the curation notes: `sim/load-step/records/`
holds exactly **one** committed record, and its R13(c) reads **`not_demonstrated`** (`n_units` 13,
`n_pass` 0, `n_fail` 0, `n_no_value` 13). **No committed R13(c) `pass` was ever reached on a
narrowed table**, so no published claim is retracted and this decision changes no number already on
record. Re-grading that record through the patched collector reproduces the row with the new
accounting: 93 withheld, all `no_waveform` (93 switched, 0 averaged), verdict unchanged at
`not_demonstrated`, and R12 / R13(b) unchanged. No record was edited and no bench was re-run for
this; `sim/**/records/` is append-only evidence.

## 5. Not established

- Whether the `lost_shard` klt failures that left 93 units without a waveform will recur: that is a
  simulation-infrastructure problem, out of scope here. This record only guarantees the narrowing
  can no longer be silent.
- The averaged-side withheld path (an ungraded averaged unit) is exercised by the unit tests
  (`sim/lib/test_collect_step_gate.py`) but by no committed run: the one committed record graded
  54 of 54 averaged units.
- Whether `not_demonstrated`-with-withheld should some day degrade to a hard `fail` at publication
  time is a reporting-policy question no collector decides today.
