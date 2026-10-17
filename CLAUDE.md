# gf180-buck — agent instructions

Open-source canary block: a synchronous inductive buck converter on the
gf180mcu PDK, with on-die power switches and an external inductor, designed
and verified by AI agents. **Analog** (power).

- **PDK**: gf180mcu (open PDK, google/gf180mcu-pdk), drawn for the 30 kÅ
  MetalTop option. Open-source flow: xschem + ngspice for design and
  simulation; layout, DRC, and LVS through klayout-tools (`klt`).
- **Power metal is the point, and the risk.** The switches carry amperes and
  the switch node swings the input rail every cycle. Budget every strap,
  via array, and pad path against the design manual's electromigration
  tables at the top of the temperature range, and record the budget before
  drawing. Thick-MetalTop rules — wide-metal spacing, density, and any
  slotting the manual requires — are where the deck and the tools are least exercised; establish which
  rules apply from the PDK documentation, and check that `klt` actually
  enforces them rather than assuming it does. File accordingly.
- **Efficiency is a layout number.** Conduction loss includes metal and via
  resistance from pad to switch. Grade efficiency post-layout with the
  extracted power path, never from the schematic alone.
- **Scope discipline.** The inductor and output capacitor are external:
  model them, with their parasitics, at the boundary, and state the part
  values every efficiency and ripple number assumes. On this PDK,
  `gf180-gate-driver` has ratified a low-side on-die power switch, its
  `Ron·W` baseline, and a thick-MetalTop electromigration budget; take that
  work by pinned reference (`reuse.lock.json`) or record why not. The same
  adopt-or-record rule applies to `gf180-bandgap` (reference), `gf180-opamp`
  (error amplifier), `gf180-comparator` (current limit, PWM comparator), and
  `gf180-rcosc` (oscillator). Do not size a second one by accident.
- **Switching converters need long runs.** Startup, load steps, and loop
  stability need transient runs over many cycles, and ngspice has no
  periodic steady-state analysis to shortcut them. State the run length,
  step, and how steady state was established next to every number, and
  cross-check loop stability against an averaged model.
- **Friction protocol (the canary's job)**: every time klayout-tools is
  awkward, missing a capability, or wrong for what you need, file an issue at
  `2AMLogic/klayout-tools` describing the tool gap generically — that tracker
  is scoped to the tool, so keep design-specific detail out of it and describe
  the gap, not the design.
- **Verification is the product**: no claim without a testbench. PVT corners
  on every recorded result; `sim/` results are append-only evidence. A
  simulated number is never called measured.
- Spec changes go through `spec/` with a decision record; agents do not relax
  the ratified spec to make results pass.
- **5 V to 1.8 V at 500 mA and 2 MHz is the target.** 200 mA is the
  fallback and 1 A a stretch. Do not let the 1 A power stage drive the
  layout before 500 mA closes.
