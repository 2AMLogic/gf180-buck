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

## Native 30 kA deck: could not run

`klt drc --engine klayout --pdk gf180mcuA` fails up front with
`klayout_version_too_old`: the standalone KLayout application on PATH is 0.28.16
and the run needs >= 0.30.9. The pip `klayout==0.30.12` wheel (tried in a
throwaway venv) ships the Python module only, no standalone application, and
`--engine klayout` does not use it. Host tools may not be changed on a loom
worker, so no pinned standalone KLayout was available.

## Acceptance criteria status

| AC | Status |
|---|---|
| Clean curated report, hashes match | Unmet: 20 violations |
| Claim quotes coverage fields verbatim | Done above, for the record only |
| 30 kA family run to completion under pinned KLayout | Unmet: needs standalone KLayout >= 0.30.9 |
| Negative control on violating variant | Not done: meaningless until the native deck can run, since the curated deck has no MT30 rule to trip |
| Method recorded | Done: curated deck + native deck attempt, pins above |
| MT30.7 out-of-block | Listed as out-of-block per 0001 section 8 item 7 |
| `klt signoff` item 3 `met` | Unmet; not attested |

Upstream friction filed: klayout-tools#4950.

## To close this

1. Regenerate the layout so `metal2.enclosing.via2.1` is clean (new issue).
2. Provide a standalone KLayout >= 0.30.9 for the worker (a change to the worker spec, not this host).
3. Re-run both decks, add the negative control, attest item 3.
