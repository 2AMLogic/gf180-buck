# Work Log

Chronological record of merged PRs and closed issues, newest first.
Maintained by the Guide role.

### 2026-11-06

- **Issue #23** (open, item 3 unmet): native 30 kA DRC re-run on klt 0.9.1 + KLayout 0.30.12 aborts in the PDK `mslot.rb` (`metal4_drawn` on a 3LM stack); evidence in `layout/drc/README.md`; friction filed as klayout-tools#5091

### 2026-11-05

- **Issue #29** (closed): T1 item 9 (testbenches shipped): testbench inventory and klt signoff --attest 9 envelope
- **PR #113**: feat: attest T1 item 9 testbenches with a single cold-start command
- **PR #112**: docs(layout): record curated DRC run on buck.gds and blocked native 30 kA deck
- **Issue #22** (closed): T1 item 2 (layout): buck GDS with power-path widths and via counts per the R18 electromigration budget

### 2026-11-04

- **PR #107**: chore: remove unreferenced steady-state long-probe sim request
- **PR #105**: docs: add errata E4 to control-rail record 0003
- **Issue #106** (closed): Remove orphan sim/steady-state/request_long_probe.json
- **Issue #103** (closed): Control-rail record 0003: wording and accounting follow-ups from the #46 key reviews
- **PR #46**: docs: add errata to control-rail record for rcosc cite, pass device, sibling Iq
- **Issue #45** (closed): spec: §2.1 gf180-rcosc supply window cite (2.97-3.63 V) disagrees with rcosc's Supply row (3.0-3.6 V); §1 thick-oxide list omits the pass device

### 2026-11-03

- **PR #99**: docs: trace the R15 drawdown to a lost PWM latch set and read the OCP trip at 0.407 A at a hot corner
- **PR #98**: docs: record R16 ramped-load trip probe reading 0.554 A at the typical corner (partial)
- **PR #97**: docs: trace on-time termination to the OCP trip at 0.565 A and raise decision 0005 (partial)
- **PR #95**: docs: record operator ruling to source a >= 8 MHz error amplifier from gf180-opamp
- **Issue #77** (closed): Diagnose R15/R16 failures at many corners seen in the partial soft-start and current-limit benches

### 2026-11-02

- **PR #94**: docs: record 3.6 ohm probe showing a fixed 0.563 A on-time termination
- **PR #93**: docs: record R15 single-corner probe at the 3.6 ohm load (partial)
- **PR #90**: docs: record R15 single-corner probe with kelvin control return and non-limiting error amp (partial)
- **PR #89**: refactor: move load-step collector and generator onto sim/lib recordkit and genkit
- **PR #88**: docs: diagnose closed-loop non-regulation as error-amp GBW instability (partial)
- **PR #87**: docs: record kelvin control-return probe for closed-loop non-regulation (partial)
- **PR #86**: docs: record die-ground-referenced R15 probe showing vc/out excursions are a bench artifact
- **PR #85**: docs: record partial diagnosis of closed-loop non-regulation (die-ground bounce)
- **Issue #81** (closed): Finish #74 dedupe: move sim/load-step collector and generator onto sim/lib recordkit/genkit
- **PR #80**: docs: record single-corner R15 start-up probe and partial diagnosis
- **PR #79**: refactor: share sim record and request-generator plumbing in sim/lib
- **Issue #74** (closed): Dedupe sim collector and request-generator plumbing into sim/lib
- **PR #68**: sim: add load-step bench, step-pair grading and R13(c) cross-check
- **PR #76**: sim: add soft-start and current-limit benches with partial R15/R16 records
- **Issue #58** (closed): T1 item 5b: device-stress and dead-time benches (R2, R14) as klt sim envelopes
- **PR #72**: sim: grade device-stress completeness against the full 135-unit grid
- **Issue #71** (closed): device-stress collect.py: ctyp (3-unit) set can read R2/R14 'pass', contradicting README
- **PR #70**: sim: add R2 device-stress and top-level R14 benches with a C-typ fleet record
- **PR #66**: sim: add steady-state bench on buck_top with first C-full record
- **Issue #57** (closed): T1 item 5a: steady-state switched bench (R4, R6, R7, R8, R11, pre-layout R9/R10) as klt sim envelopes

### 2026-11-01

- **PR #64**: chore: remove duplicate design/xschemrc and document netlist.sh
- **PR #63**: feat: generate power-stage GDS with EM-budgeted slotted Metal3 trunks
- **Issue #52** (closed): Consolidate duplicate xschemrc files and netlisting recipes under design/
- **PR #56**: feat: scale VREF_SS to 0.6 V with a 1:1 divider in buck_top and add reference smoke
- **Issue #53** (closed): VREF_SS ceiling (1.2 V) vs compensator Vref (0.6 V) mismatch at the top level
- **Issue #21** (closed): T1 item 1 (design sources): transistor-level buck schematics (power stage, gate drive with dead time, PWM, soft start, current limit) and derived netlists with item-1 attestation
- **PR #54**: feat: add compensator and top-level schematics, attest T1 item 1
- **Issue #35** (closed): T1 item 1d: type-III network, top-level schematic, netlists and item-1 attestation
- **PR #49**: feat: controller schematics and netlists for oscillator, PWM, soft start and Ron-sense OCP
- **Issue #34** (closed): T1 item 1c: controller schematics (oscillator/ramp, PWM comparator, soft start, Ron-sense current limit)
- **PR #50**: docs: record 162-point averaged loop-gain sweep run on the batch fleet
- **Issue #17** (closed): design: averaged power-stage model and type-III compensator with AC loop-gain sweep over P-T tolerances (R13a, T1 item 1)
- **PR #48**: feat: power-stage and gate-drive schematics with dead-time smoke
- **Issue #33** (closed): T1 item 1b: power-stage and gate-drive schematics with dead time (HS/LS, level shift)
- **PR #37**: docs(spec): record the 3.3 V control-rail decision
- **Issue #32** (closed): T1 item 1a: record the 3.3 V control-rail choice (residual 3)
- **PR #43**: Bump Repo Skills 0.24.7 -> 0.25.1

### 2026-10-27

- **PR #40**: chore: untrack generated sweep_request.json
- **Issue #39** (closed): Remove tracked generated sweep_request.json (regenerated by run.sh every run)
- **PR #36**: feat: attest T1 item 10 repo hygiene with klt 0.8.0
- **Issue #30** (closed): T1 item 10 (repo hygiene): hygiene inventory and klt signoff --attest 10 envelope

### 2026-10-23

- **PR #19**: feat(sim): add §0.4 buck measurement module and ideal-switch bench
- **PR #18**: feat: averaged buck loop-gain bench, type-III compensator and fc/PM/GM extractor
- **PR #6**: ci: grade T1 verdict with pinned klt signoff and compare against committed record
- **Issue #16** (closed): sim: §0.4 steady-state and switching-measurement module with an ideal-switch buck bench (T1 items 5, 9 groundwork)
- **Issue #3** (closed): Add the T1 signoff scaffolding: block manifest, vendored checklist and CI (item 10)

### 2026-10-21

- **PR #12**: Bump Repo Skills 0.24.3 -> 0.24.7

### 2026-10-18

- **PR #10**: docs(spec): record PDK variant pins (spec A vs sim D) and model-file hash check
- **Issue #9** (closed): Reconcile PDK variant/revision pins: spec (gf180mcuA) vs sim/pdk.json (gf180mcuD)

### 2026-10-17

- **PR #8**: feat(sim): pin gf180mcuD PDK, env.sh revision check, inverter smoke bench
- **PR #7**: docs(spec): ratify buck target spec with EM budget, thick-metal coverage and sibling reuse
- **PR #1**: chore(loom): Install Loom 0.19.1181
- **Issue #4** (closed): Pin the PDK and commit a smoke simulation (T1 item 9 bring-up)
- **Issue #2** (closed): Draft and ratify the target spec
