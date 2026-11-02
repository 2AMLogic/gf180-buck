# Work Plan

Roadmap generated from GitHub label state by the Guide role. Only the region
between the markers is machine-generated.

<!-- guide:plan-body:start -->
## Operator Attention: Merge-Risk-Hold Pileup

Judge-approved PRs under a hold (`loom:blocked` or `loom:operator`) — only a human merge decision is missing.

- **#46**: docs: add errata to control-rail record for rcosc cite, pass device, sibling Iq

## Very Important

`loom:very-important` (one counts per workspace); every stage takes these first.

- **#22**: T1 item 2 (layout): buck GDS with power-path widths and via counts per the R18 electromigration budget

## Important

`loom:important`; taken before unlabelled work.

- **#58**: T1 item 5b: device-stress and dead-time benches (R2, R14) as klt sim envelopes
- **#59**: T1 item 5c: load-step bench and averaged-model cross-check (R12, R13b/c) as klt sim envelopes
- **#60**: T1 item 5d: soft-start and current-limit benches (R15, R16) as klt sim envelopes
- **#62**: Draw device-level layout for the control blocks (gate_drive, osc_ramp, pwm_comp, soft_start, ocp_sense, compensator)
- **#69**: T1 item 5b remainder: run the R2 / R14 C-full grid (135 units at 100 ps) on the fleet

## Ready

Human-approved issues ready for implementation (`loom:issue`).

- **#22**: T1 item 2 (layout): buck GDS with power-path widths and via counts per the R18 electromigration budget

## In Progress

Issues currently being built (`loom:building`).

- **#45**: spec: §2.1 gf180-rcosc supply window cite (2.97-3.63 V) disagrees with rcosc's Supply row (3.0-3.6 V); §1 thick-oxide list omits the pass device
- **#59**: T1 item 5c: load-step bench and averaged-model cross-check (R12, R13b/c) as klt sim envelopes
- **#60**: T1 item 5d: soft-start and current-limit benches (R15, R16) as klt sim envelopes
- **#69**: T1 item 5b remainder: run the R2 / R14 C-full grid (135 units at 100 ps) on the fleet

## PRs Awaiting Review

PRs waiting on Judge (`loom:review-requested`).

- **#68**: sim: add load-step bench, step-pair grading and R13(c) cross-check

## Approved (Awaiting Merge)

PRs that passed review and are queued for Champion auto-merge (`loom:pr`).

- **#46**: docs: add errata to control-rail record for rcosc cite, pass device, sibling Iq

## Proposed

Issues carrying `loom:curated`.

- **#5**: Track the gap to T1 (klayout-tools design-evidence-tiers.md) *(curated)*
- **#22**: T1 item 2 (layout): buck GDS with power-path widths and via counts per the R18 electromigration budget *(curated)*
- **#26**: T1 item 6 (Monte Carlo): classify the statistical rows and produce klt yield evidence for R4 (and any other matching-dependent row) *(curated)*
- **#29**: T1 item 9 (testbenches shipped): testbench inventory and klt signoff --attest 9 envelope *(curated)*
- **#45**: spec: §2.1 gf180-rcosc supply window cite (2.97-3.63 V) disagrees with rcosc's Supply row (3.0-3.6 V); §1 thick-oxide list omits the pass device *(curated)*
- **#58**: T1 item 5b: device-stress and dead-time benches (R2, R14) as klt sim envelopes *(curated)*
- **#59**: T1 item 5c: load-step bench and averaged-model cross-check (R12, R13b/c) as klt sim envelopes *(curated)*
- **#60**: T1 item 5d: soft-start and current-limit benches (R15, R16) as klt sim envelopes *(curated)*
- **#69**: T1 item 5b remainder: run the R2 / R14 C-full grid (135 units at 100 ps) on the fleet *(curated)*

## Proposed (Architect / Hermit)

- **#74**: Dedupe sim collector and request-generator plumbing into sim/lib *(hermit)*

## Epics

_None._

## Backlog Balance

| Bucket | Count |
|------|-------|
| Operator merge-risk holds | 1 |
| Very important | 1 |
| Important | 5 |
| Ready (`loom:issue`) | 1 |
| In Progress (`loom:building`) | 4 |
| PRs awaiting review | 1 |
| Approved PRs awaiting merge | 1 |
| Curated | 9 |
| Architect / Hermit proposals | 1 |
| Active epics | 0 |
<!-- guide:plan-body:end -->
