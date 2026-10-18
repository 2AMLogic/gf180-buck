# spec

The ratified specification and its decision records.

| File | What it is |
|---|---|
| [`target-spec.md`](target-spec.md) | The target specification: target, fallback and stretch tiers, one row per parameter, each with min / typ / max, grading condition, corner set and external parts |
| [`decision-records/0001-ratify-target-spec.md`](decision-records/0001-ratify-target-spec.md) | Ratifies the spec; records the electromigration budget method, the thick-MetalTop rule coverage in `klt`, the control and stability method, and the adopt-or-keep decisions on the same-PDK siblings |
| [`decision-records/0002-pdk-variant-pins.md`](decision-records/0002-pdk-variant-pins.md) | Relates the spec's `gf180mcuA` PDK pin to the simulation pin `gf180mcuD`: which results depend on which variant |
| [`../reuse.lock.json`](../reuse.lock.json) | The pinned sibling references behind the adopt-or-keep table |

A change to a ratified number needs a new decision record in
`decision-records/`; agents do not relax a row to make a result pass.
