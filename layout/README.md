# layout

Power-stage layout for the 500 mA target tier, generated, not hand-edited.
PDK variant `gf180mcuA` (3LM, 30 kÅ MetalTop; MetalTop is Metal3, 42/0).

| File | What it is |
|---|---|
| `gen_layout.py` | Deterministic generator (KLayout `pya`/`klayout.db`). Reads `MHS`/`MLS` W, L, nf, m from `design/schematics/power_stage.sch`; derives trunk heights from the EM table (spec R18, decision record 0001 §5.1). `--current` sets the load (default 500 mA); 200 mA and 1 A are parameters, not verified. |
| `buck.gds` | Committed output. Two runs give the same sha256 (GDS timestamps are off). |
| `buck.info.json` | Generator's own bookkeeping (rows, trunk heights, die, pads). |
| `check_layout.py` | Recomputes widths (net of `Metal3_Slot`), cuts per level, fingers and pad counts **from the GDS** and compares with the 500 mA row. Exit 0 only if all pass. `--write` rewrites `record.md`. |
| `record.md` | The per-net table with the GDS hash. Never hand-written. |

## Regenerate

From the repository root (needs the `klayout` Python module; no host installs):

```
python3 layout/gen_layout.py
python3 layout/check_layout.py --write
sha256sum layout/buck.gds                 # cited by manifests/gf180-buck.json
klt signoff --attest 2 --input layout/buck.gds \
    --generator "python3 layout/gen_layout.py" \
    --regenerated-hash sha256:$(sha256sum layout/buck.gds | cut -d' ' -f1) \
    -o manifests/item2-attestation.json    # needs a klt newer than 0.8.0
```

Then update `evidence["2"].content_hash` and regenerate the verdict of record
(`manifests/README.md`). A `design/` change that alters `MHS`/`MLS` is a
regenerate, not a redraw (#53 may change the divider, not these devices).

## What is drawn

- HS pfet (3 000 fingers, L 0.55 µm, 6 rows of 500) and LS nfet (2 240 fingers,
  L 0.70 µm, 5 rows of 448), 10 µm fingers, merged diffusion, `Dualgate`.
- Metal1 S/D rails, Metal2 collection straps, Via1/Via2 over the whole array,
  Metal3 strips (20 µm, below the 30 µm slot threshold) into three slotted
  trunks: VIN (62 µm drawn, 60 net), SW (126 / 120), GND (94 / 90). Slots are
  `Metal3_Slot` marks (42/3), 2 µm wide, 30 µm of metal between, 250 µm long,
  staggered; Metal3 itself is solid.
- Two 80 µm `Pad` sites per power net on the trunk tails (R19); gate buses
  `GH`/`GL` on Metal2; body-tie strips with Metal2 to the trunks.

## What is NOT drawn (disclosed)

- **Control blocks** (gate_drive, osc_ramp, pwm_comp, soft_start, ocp_sense,
  compensator) are a floorplan reservation on marker layer 998/0 only. No
  devices, so LVS (#24) cannot match the full `buck_top` yet. Tracked in a
  follow-up issue.
- No signal pads, seal ring, dummy fill, or die-level MT30.7 density.
- Body ties only at the two array ends (interior row tap density not drawn).
- Metal1/Metal2 current density along rails and straps is sized by
  construction (rail 3.4 µm, 5 straps of 3.4 µm per 20 µm group), not
  measured; `klt power` extraction is future work (#31/#23 consumers).
- Not DRC-checked. `klt drc` curated deck does not enforce MT30.* / MSLOT
  (decision record 0001 §5.2); DRC is #23. Rule values for the device
  geometry were taken from the PDK deck by hand and are unverified.
- Die outline (999/0) keeps 400 µm from the nearest metal on every side,
  satisfying the 300 µm metal-to-corner rule by construction.
