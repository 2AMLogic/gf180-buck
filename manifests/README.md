# manifests/

Block manifest and tier verdict of record, graded by `klt signoff`.

| File | What it is |
|---|---|
| `gf180-buck.json` | Block manifest: `kind: analog`; cites the item-1 and item-10 attestation envelopes (its `content_hash` is the sha256 of `item10-inventory.json`, the input the envelope is bound to). |
| `item1-attestation.json` | Envelope from `klt signoff --attest 1` over `design/inventory-item1.json` (every schematic, symbol, the generator, the compensator values and the netlists derived from them). Never hand-written. |
| `item2-attestation.json` | Envelope from `klt signoff --attest 2 --input layout/buck.gds`; cited with the GDS sha256. Never hand-written. Needs a `klt` newer than the pinned 0.9.0 (klayout-tools#4767), so CI does not re-attest it; the manifest grade does re-hash the GDS. |
| `item10-inventory.json` | T1 item 10 attestation inventory: hygiene files plus the audit commands whose exit status is attested. |
| `item10-attestation.json` | Envelope from `klt signoff --attest 10`. Never hand-written. |
| `item9-inventory.json` | T1 item 9 attestation inventory: every bench file, the `sim/cold-start.sh` cold start, PDK and tool pins. |
| `item9-attestation.json` | Envelope from `klt signoff --attest 9`. Never hand-written; the cold start needs the PDK, ngspice and the batch fleet, so it is written locally, see [`../sim/README.md`](../sim/README.md#cold-start). The manifest cites it with the sha256 of `item9-inventory.json`. |
| `check_readme.py` | The README structure and relative-link check the inventory runs. |
| `design-evidence-tiers.md` | Vendored, byte-identical copy of klayout-tools `docs/design-evidence-tiers.md` at commit `44cc42323184a2f3a440b89789bf174488a6b1e4`. Do not edit. |
| `gf180-buck.signoff.json` | Verdict of record: raw `klt signoff` output. Never hand-written. |

## Regenerating the verdict of record

Run from the repository root, with the pinned `klt` in a throwaway
environment (not a host install):

```
uvx --from "klayout-tools==0.9.0" klt signoff \
    --manifest manifests/gf180-buck.json \
    --tiers-doc manifests/design-evidence-tiers.md \
    --format json > manifests/gf180-buck.signoff.json
```

### Item 1 (design sources)

Whenever a schematic, symbol, `gen_schematics.py`, `design/compensator.md` or a
netlist changes: run `design/netlist.sh` (regenerates the netlists) and
`design/netlist.sh --check` (all `match`), then re-attest with a `klt` that
supports `klt netlist --ignore-comments` (newer than the pinned 0.9.0; the
netlist freshness checks are `local_only` and run only here):

```
klt signoff --attest 1 --inventory design/inventory-item1.json \
    -o manifests/item1-attestation.json
```

Set `evidence["1"].content_hash` in `gf180-buck.json` to
`sha256:$(sha256sum design/inventory-item1.json)`, then do the item-10 steps
below. CI re-runs `--attest 1 ... --check` (netlist checks skipped there). Note
that `klt signoff --manifest` alone does not go stale when a listed member
changes, only the `--check` does (klayout-tools#4764).

### Item 2 (layout)

After `python3 layout/gen_layout.py` (see `layout/README.md`), re-attest with a newer `klt` (command in `layout/README.md`), set `evidence["2"].content_hash` in `gf180-buck.json` to `sha256:$(sha256sum layout/buck.gds)`, then do the item-10 steps below.

### Item 10 (repo hygiene) and the verdict of record

Regenerate the item-10 envelope first whenever the inventory, any file it
lists, or a check's outcome changes. `klt` must be on `PATH` (the inventory
runs `klt signoff ... --check` as a check), so use a throwaway venv, not a host
install: `python3 -m venv /tmp/klt && /tmp/klt/bin/pip install klayout-tools==0.9.0`
and put `/tmp/klt/bin` on `PATH`:

```
klt signoff --attest 10 --inventory manifests/item10-inventory.json \
    -o manifests/item10-attestation.json
```

Then set the `content_hash` in `gf180-buck.json` to
`sha256:$(sha256sum manifests/item10-inventory.json)` and regenerate the
record as below. The inventory's `signoff-record-fresh` check reads the
committed record, so attest while the record is still fresh for the current
inventory (a changed inventory makes the cited envelope stale until it is
re-attested): after a normal edit, re-attest, update the hash, regenerate the
record, and confirm both `--check` runs below exit 0.

Exit code 0 (every T1 item met) and 3 (grader ran, items unmet) are both
valid runs; the redirect captures the report either way. Paths are relative
because the report records `source_doc` verbatim.

Refresh the vendored checklist from upstream:

```
gh api 'repos/2AMLogic/klayout-tools/contents/docs/design-evidence-tiers.md?ref=44cc42323184' \
    -H 'Accept: application/vnd.github.raw' > manifests/design-evidence-tiers.md
```

Verify without writing anything:

```
klt signoff --attest 10 --inventory manifests/item10-inventory.json \
    --check manifests/item10-attestation.json
klt signoff --manifest manifests/gf180-buck.json \
    --tiers-doc manifests/design-evidence-tiers.md \
    --check manifests/gf180-buck.signoff.json
```

## CI

`.github/workflows/signoff.yml` re-runs the same command with the pinned
`klayout-tools==0.9.0`, accepts exit 0 or 3 (anything else fails), and
`cmp`s the fresh output against the committed record. Changing the manifest,
cited evidence, or the vendored checklist without regenerating the record
fails the check. A second step runs `klt signoff --attest 10 ... --check`
against the committed envelope and fails on drift. The version is pinned exactly because the record is
byte-compared; bump the pin and regenerate the record in the same PR.
