# 0002 — PDK variant and revision pins: spec facts vs. simulation

- **Status**: Ratified on merge of the pull request that carries this record
  (issue #9).
- **Date**: 2026-10-18
- **Amends**: nothing. No number in [`../target-spec.md`](../target-spec.md) is
  changed; the spec header gains one pointer to this record.
- **Claims made**: none. One file-hash comparison, described in §3. No
  schematic, simulation or layout was run.

## 1. Decision

The repo keeps two PDK pins and states what each is for. Which pin a result
depends on is decided by what kind of result it is:

| Result kind | Depends on | Pin |
|---|---|---|
| Device models, simulated electrical numbers (`sm141064.ngspice`, `design.ngspice`) | Model files only; byte-identical across variants A–D (§3) | `gf180mcuD` @ `c6d73a35f524070e85faff4a6a9eef49553ebc2b` (`sim/pdk.json`) |
| Metal stack, electromigration tables, DRC, LVS, parasitic extraction, any post-layout or EM claim | The variant's metal option | `gf180mcuA` (30 kÅ MetalTop) @ open_pdks `f6eeac7dad085ffcc829ccfd721f7b4ce39edcf7` (`spec/target-spec.md` header) |

Simulation is not re-pinned to A. `sim/pdk.json` is already merged and
checked by `sim/env.sh`, and the model files are identical, so re-pinning would
churn the merged simulation environment and its smoke record for no model
difference.

## 2. Rules that follow

1. Any post-layout, extracted, or EM result names its variant. DRC, LVS and
   extraction of the power metal run against `gf180mcuA` (30 kÅ), not D. The
   spec (R18) already notes that `tm11k` belongs to `gf180mcuB / D`, i.e.
   thinner metal than the A option; a result obtained on D's stack does not
   describe the drawn 30 kÅ design.
2. Any simulated number names the `sim/pdk.json` pin (D, `c6d73a35…`) and
   remains "simulated", never "measured".
3. If a model file ever differs between the pins, this record is superseded and
   the comparison in §3 is re-run at the new pins before any result is graded.

## 3. Model-file comparison

Run on 2026-10-18 against the installs under `~/.volare` (all four variant
directories resolve into the single version `c6d73a35…`):

```sh
for v in A B C D; do
  sha256sum ~/.volare/gf180mcu$v/libs.tech/ngspice/{sm141064,design}.ngspice
done
```

Result: identical across A, B, C and D, and equal to `model_files` in
`sim/pdk.json`:

- `libs.tech/ngspice/sm141064.ngspice`:
  `6edba54d23b38a2c60f8ffdbaa3eb75a7568c615e4820808969bd1121b77b1aa`
- `libs.tech/ngspice/design.ngspice`:
  `091cb530bf85160a1f07878fb81f789ca367d018991c8ab41a584cd1a85c6692`

**Limit of this comparison**: it was done at revision `c6d73a35…` only. The
spec's revision `f6eeac7d…` is not installed on the host that produced this
record, so its model files were not hashed and the revisions' equality is not
established. The identical-across-variants result is a statement about
`c6d73a35…`.

## 4. Residual (not traced here)

- Why the spec's PDK facts were read at `f6eeac7d…` while simulation was pinned
  at `c6d73a35…` is not recorded in either source; this record does not
  invent a reason.
- How `klt` selects the metal option (variant directory vs. a deck flag), and
  whether the klayout DRC/LVS decks differ between A and D beyond the
  variant-named magic/netgen/openlane files seen with
  `diff -rq gf180mcuA/libs.tech gf180mcuD/libs.tech`, were not traced.
