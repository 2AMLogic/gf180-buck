# layout/drc: DRC evidence for T1 item 3 (issue #23)

**Item 3 is NOT met.** This directory records the run and why it cannot be claimed.

## Run of record

```
uvx --from klayout-tools==0.9.0 klt drc layout/buck.gds --deck gf180mcu \
    --pdk gf180mcuA --format json -o layout/drc/curated-gf180mcu.json
uvx --from klayout-tools==0.9.0 klt drc --check layout/drc/curated-gf180mcu.json   # status: match
```

| Field | Value |
|---|---|
| klt | 0.9.0 (`5dbbad05`), pip KLayout 0.30.12 |
| Deck | curated `gf180mcu`, content hash `sha256:cf44de63f0a5b01c1d09c4d58e0535e990aa4b070bcaae17fd3a94a67a1d97e1` |
| Input | `layout/buck.gds`, `sha256:0d3d4c3a09391cab7198eea829b0649636eacff7cf2ac148386594d8da566c0c` (equals the committed GDS) |
| Status | `violations`, 20 findings, all `metal2.enclosing.via2.1` (Metal2 overlap of Via2, at x near -7.5..-5.2 um and 580..583 um, y 88.9 and 462.4 um) |

The 20 findings are real layout defects in the committed GDS, not a coverage
artefact. Fixing them is a regenerate of the layout (#22's domain), out of scope here.

## Coverage (verbatim from the report)

- `coverage.layers_in_stream_without_rules`: `36/10`, `42/3`, `42/10`, `998/0`, `999/0`. Note `42/3` is the `Metal3_Slot` mark.
- `coverage.deck_scope`: 10.4.2 MIM Option B; 10.7 DRC_BJT Mark Layer; 7.12 Contact; 7.13 Metaln; 7.14 Vian; 7.15 MetalTop; 7.4 Nwell; 7.5 Comp; 7.7 Poly2; 7.8 Nplus; 7.9 Pplus; 9.1 Bond Pad; EF; ESD; GR; MDN; MDP; OFFGRID; SB.
- `coverage.rules_skipped`: 69 rules, including `metaltop.width.1`, `metaltop.space.1`, `metaltop.ongrid.1`. Full list in the JSON.
- `coverage.unmodeled_rules` includes `MT30.1a` through `MT30.8` (17 ids; 210 unmodeled in total) and `MSLOT.1` through `MSLOT.8`.

So the curated deck enforces no `MT30.*`, wide-metal spacing or slotting rule on
this GDS (decision record 0001 section 5.2 still holds on klt 0.9.0).

## Native 30 kA deck: aborts (second attempt, 2026-11-06)

```
uvx --from klayout-tools==0.9.1 klt drc layout/buck.gds --engine klayout \
    --klayout-binary /usr/bin/klayout --pdk gf180mcuA --format json -o out.json
```

- klt 0.9.1, standalone KLayout 0.30.12 (>= the 0.30.9 floor, so the earlier
  `klayout_version_too_old` blocker is cleared). Input sha256 equals the committed GDS
  (`0d3d4c3a...66c0c`). Wall time about 85 s.
- The deck ran through the earlier decks, then exited 1 at `rule_decks/mslot.rb` with
  `undefined local variable or method 'metal4_drawn'` (`gf180mcu.drc:191`). `mslot.rb`
  uses `metal4_drawn` unconditionally and this variant is 3LM (no Metal4).
- Passing the variant's own defaults (`--deck-var metal_level=3LM --deck-var metal_top=30K`)
  gives the identical abort.
- klt refuses the partial report (it would need `--allow-deck-errors`). No report is
  committed: a partial report must not be counted as clean, and none of
  `metaltop_30k`, `density`, `mslot` is established as run to completion.
- Upstream friction filed: klayout-tools#5091 (also #4950 for the earlier binary gap).

## Acceptance criteria status

| AC | Status |
|---|---|
| Clean curated report, hashes match | Unmet: 20 violations |
| Claim quotes coverage fields verbatim | Done above, for the record only |
| 30 kA family run to completion under pinned KLayout | Unmet: native deck aborts in `mslot.rb` on 3LM (KLayout 0.30.12, klt 0.9.1) |
| Negative control on violating variant | Not done: meaningless until the native deck can run, since the curated deck has no MT30 rule to trip |
| Method recorded | Done: curated deck + native deck attempt, pins above |
| MT30.7 out-of-block | Listed as out-of-block per 0001 section 8 item 7 |
| `klt signoff` item 3 `met` | Unmet; not attested |

## To close this

1. Regenerate the layout so `metal2.enclosing.via2.1` is clean (new issue).
2. A native-deck run that completes on a 3LM variant: needs an upstream fix to the PDK
   `mslot.rb` (guard `metal4_drawn`) or a klt capability to run a recorded deck subset
   (klayout-tools#5091). Then re-run both decks, add the negative control, attest item 3.
