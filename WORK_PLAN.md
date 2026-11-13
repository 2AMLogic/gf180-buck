# Work Plan

Roadmap generated from GitHub label state by the Guide role. Only the region
between the markers is machine-generated.

<!-- guide:plan-body:start -->
## Operator Attention: Merge-Risk-Hold Pileup

Judge-approved PRs under a hold (`loom:blocked` or `loom:operator`) — only a human merge decision is missing.

_None._

## Very Important

`loom:very-important` (one counts per workspace); every stage takes these first.

- **#82**: Diagnose closed-loop non-regulation: no switched unit passes the §0.4 settled test (R4 fail, blocks R12/R13/R2/R14 grading)

## Important

`loom:important`; taken before unlabelled work.

- **#59**: T1 item 5c: load-step bench and averaged-model cross-check (R12, R13b/c) as klt sim envelopes
- **#60**: T1 item 5d: soft-start and current-limit benches (R15, R16) as klt sim envelopes
- **#62**: Draw device-level layout for the control blocks (gate_drive, osc_ramp, pwm_comp, soft_start, ocp_sense, compensator)
- **#69**: T1 item 5b remainder: run the R2 / R14 C-full grid (135 units at 100 ps) on the fleet
- **#109**: Lay out gate_drive and connect GH/GL to the power-stage gate buses (first split of #62)
- **#111**: Lay out osc_ramp, pwm_comp, soft_start, ocp_sense, compensator and route the control strip (second split of #62)
- **#123**: Resize gate_drive final stages MP_HG5/MP_LG5: 0.189 um fingers below the 0.30 um Dualgate COMP minimum (r7-q53)

## Ready

Human-approved issues ready for implementation (`loom:issue`).

- **#151**: Extract the bench harness copied into five sim bench.spice decks into one shared include

## In Progress

Issues currently being built (`loom:building`).

_None._

## PRs Awaiting Review

PRs waiting on Judge (`loom:review-requested`).

_None._

## Approved (Awaiting Merge)

PRs that passed review and are queued for Champion auto-merge (`loom:pr`).

_None._

## Proposed

Issues carrying `loom:curated`.

- **#5**: Track the gap to T1 (klayout-tools design-evidence-tiers.md) *(curated)*
- **#23**: T1 item 3 (DRC clean): klt drc on the buck GDS plus the PDK-native 30 kA MetalTop rule family, coverage disclosed *(curated)*
- **#24**: T1 item 4 (LVS clean): klt lvs of the buck layout against its schematic netlist *(curated)*
- **#26**: T1 item 6 (Monte Carlo): classify the statistical rows and produce klt yield evidence for R4 (and any other matching-dependent row) *(curated)*
- **#60**: T1 item 5d: soft-start and current-limit benches (R15, R16) as klt sim envelopes *(curated)*
- **#69**: T1 item 5b remainder: run the R2 / R14 C-full grid (135 units at 100 ps) on the fleet *(curated)*
- **#82**: Diagnose closed-loop non-regulation: no switched unit passes the §0.4 settled test (R4 fail, blocks R12/R13/R2/R14 grading) *(curated)*
- **#109**: Lay out gate_drive and connect GH/GL to the power-stage gate buses (first split of #62) *(curated)*
- **#123**: Resize gate_drive final stages MP_HG5/MP_LG5: 0.189 um fingers below the 0.30 um Dualgate COMP minimum (r7-q53) *(curated)*

## Proposed (Architect / Hermit)

- **#96**: Remove 600-line buck_top_kelvin.spice copy: 6-line delta from buck_top.spice *(hermit)*
- **#152**: Single-source the spec 0.4 step rule, the 41-cycle clock guard and the no-waveform unit guard in sim/lib (hand-copied into 3-5 collectors) *(hermit)*
- **#153**: Correct the cold-start 'every shipped bench' claim: sim/cold-start.sh runs 3 of the 6 attested runners *(hermit)*
- **#154**: Move the item 9 inventory and envelope into manifests/: attest/ and evidence/ are one-file top-level directories *(hermit)*

## Epics

_None._

## Backlog Balance

| Bucket | Count |
|------|-------|
| Operator merge-risk holds | 0 |
| Very important | 1 |
| Important | 7 |
| Ready (`loom:issue`) | 1 |
| In Progress (`loom:building`) | 0 |
| PRs awaiting review | 0 |
| Approved PRs awaiting merge | 0 |
| Curated | 9 |
| Architect / Hermit proposals | 4 |
| Active epics | 0 |
<!-- guide:plan-body:end -->
