# layout/drc: DRC evidence for T1 item 3 (issue #23)

**Item 3 is NOT met.** The curated-deck run is clean — the Via2 enclosure
defects were fixed by regenerating the layout (#176), and the orphan Via1 cuts
were fixed by clipping the strap extent to the rows (#182) — but the native 30
kA deck still cannot run on this 3LM variant, so item 3 cannot be claimed.

## Run of record

```
uvx --from klayout-tools==0.9.0 --with "klayout==0.30.12" klt drc layout/buck.gds \
    --deck gf180mcu --pdk gf180mcuA --format json -o layout/drc/curated-gf180mcu.json
uvx --from klayout-tools==0.9.0 klt drc --check layout/drc/curated-gf180mcu.json   # status: match
```

| Field | Value |
|---|---|
| klt | 0.9.0 (`5dbbad05`), pip KLayout 0.30.12 (engine pinned with `--with` above) |
| Deck | curated `gf180mcu`, content hash `sha256:cf44de63f0a5b01c1d09c4d58e0535e990aa4b070bcaae17fd3a94a67a1d97e1` |
| Input | `layout/buck.gds`, `sha256:a7afbfe7a635637e65cc127c77df3fd1fc51c104e8eab067a480fee8452106c3` (equals the committed GDS) |
| Status | `clean`, 0 findings, `rule_counts` empty. The 20 `metal2.enclosing.via2.1` findings carried by the pre-#176 GDS are gone (`body_ties` derives the Via2 band from the Metal2 ∩ Metal3-trunk intersection, #176). The deck's enclosing rules cannot see a cut with *no* metal on either side of it — `metal1.enclosing.via1.1` and `metal2.enclosing.via1.1` both sat clean over 1260 cuts with no Metal1 below and 720 with no Metal2 above (klayout-tools#5737, blind in both directions) — so `layout/check_layout.py` asserts cut coverage geometrically in both directions: `VIA1`/`VIA2`/`CONTACT` against the metal below and `VIA1` against Metal2, `VIA2` against Metal3 above (the Via1 probes added by #182). The gate buses no longer run under the left body-tie strip (#201): the bus left edge derives from the tie's Metal2 extent plus `2 x metal2.space.1`, and `metal2.space.1` — among the 57 checked rules — polices the new clearance. DRC has no connectivity, so the gate-to-tie short itself is asserted by `layout/check_layout.py`'s net-level Metal2 propagation and `gen_layout.py`'s generation-time invariant, not by this deck. |

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
- Upstream friction filed: klayout-tools#5091 (also #4950 for the earlier binary gap;
  #4950 is closed — it delivered the pinned standalone-KLayout env). #5091 was closed
  `completed` on 2026-11-06; it delivered the structured abort cause with
  `decks_executed` and a 3LM documentation note, never a way to run the deck. The live
  upstream dependency for running the native deck is **klayout-tools#4002** (open):
  make gf180mcu's native sign-off deck runnable from `klt drc --engine klayout`.

## Acceptance criteria status

| AC | Status |
|---|---|
| Clean curated report, hashes match | Met (#176): `clean`, hashes above |
| Claim quotes coverage fields verbatim | Done above, for the record only |
| 30 kA family run to completion under pinned KLayout | Unmet: native deck aborts in `mslot.rb` on 3LM (KLayout 0.30.12, klt 0.9.1); live dependency klayout-tools#4002 |
| Negative control on violating variant | Not done: meaningless until the native deck can run, since the curated deck has no MT30 rule to trip |
| Method recorded | Done: curated deck + native deck attempt, pins above |
| MT30.7 out-of-block | Listed as out-of-block per 0001 section 8 item 7 |
| `klt signoff` item 3 `met` | Unmet; not attested |

## To close this

1. ~~Regenerate the layout so `metal2.enclosing.via2.1` is clean~~ — done by #176,
   extended by #182: the curated run is clean and every cut is geometrically
   covered below and above in all six probes (asserted by
   `layout/check_layout.py`; the deck cannot check orphan cuts itself).
2. A native-deck run that completes on a 3LM variant: needs an upstream fix to the PDK
   `mslot.rb` (guard `metal4_drawn`) or a klt capability to run the native deck on this
   variant (klayout-tools#4002, open; its own criteria allow the 3LM `mslot.rb`
   breakage to be *disclosed* rather than fixed, so #4002 closing may not be enough).
   #5091 is closed and delivered only the structured abort cause and the 3LM
   documentation note. Then re-run both decks, add the negative control, attest item 3.
