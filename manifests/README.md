# manifests/

Block manifest and tier verdict of record, graded by `klt signoff`.

| File | What it is |
|---|---|
| `gf180-buck.json` | Block manifest: `kind: analog`; cites the item-10 attestation envelope (its `content_hash` is the sha256 of `item10-inventory.json`, the input the envelope is bound to). |
| `item10-inventory.json` | T1 item 10 attestation inventory: hygiene files plus the audit commands whose exit status is attested. |
| `item10-attestation.json` | Envelope from `klt signoff --attest 10`. Never hand-written. |
| `check_readme.py` | The README structure and relative-link check the inventory runs. |
| `design-evidence-tiers.md` | Vendored, byte-identical copy of klayout-tools `docs/design-evidence-tiers.md` at commit `44cc42323184a2f3a440b89789bf174488a6b1e4`. Do not edit. |
| `gf180-buck.signoff.json` | Verdict of record: raw `klt signoff` output. Never hand-written. |

## Regenerating the verdict of record

Run from the repository root, with the pinned `klt` in a throwaway
environment (not a host install):

```
uvx --from "klayout-tools==0.8.0" klt signoff \
    --manifest manifests/gf180-buck.json \
    --tiers-doc manifests/design-evidence-tiers.md \
    --format json > manifests/gf180-buck.signoff.json
```

Regenerate the item-10 envelope first whenever the inventory, any file it
lists, or a check's outcome changes. `klt` must be on `PATH` (the inventory
runs `klt signoff ... --check` as a check), so use a throwaway venv, not a host
install: `python3 -m venv /tmp/klt && /tmp/klt/bin/pip install klayout-tools==0.8.0`
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
`klayout-tools==0.8.0`, accepts exit 0 or 3 (anything else fails), and
`cmp`s the fresh output against the committed record. Changing the manifest,
cited evidence, or the vendored checklist without regenerating the record
fails the check. A second step runs `klt signoff --attest 10 ... --check`
against the committed envelope and fails on drift. The version is pinned exactly because the record is
byte-compared; bump the pin and regenerate the record in the same PR.
