# manifests/

Block manifest and tier verdict of record, graded by `klt signoff`.

| File | What it is |
|---|---|
| `gf180-buck.json` | Block manifest: `kind: analog`, `evidence: {}` (no evidence cited yet). |
| `design-evidence-tiers.md` | Vendored, byte-identical copy of klayout-tools `docs/design-evidence-tiers.md` at commit `44cc42323184a2f3a440b89789bf174488a6b1e4`. Do not edit. |
| `gf180-buck.signoff.json` | Verdict of record: raw `klt signoff` output. Never hand-written. |

## Regenerating the verdict of record

Run from the repository root, with the pinned `klt` in a throwaway
environment (not a host install):

```
uvx --from "klayout-tools==0.7.0" klt signoff \
    --manifest manifests/gf180-buck.json \
    --tiers-doc manifests/design-evidence-tiers.md \
    --format json > manifests/gf180-buck.signoff.json
```

Exit code 0 (every T1 item met) and 3 (grader ran, items unmet) are both
valid runs; the redirect captures the report either way. Paths are relative
because the report records `source_doc` verbatim.

Refresh the vendored checklist from upstream:

```
gh api 'repos/2AMLogic/klayout-tools/contents/docs/design-evidence-tiers.md?ref=44cc42323184' \
    -H 'Accept: application/vnd.github.raw' > manifests/design-evidence-tiers.md
```

## CI

`.github/workflows/signoff.yml` re-runs the same command with the pinned
`klayout-tools==0.7.0`, accepts exit 0 or 3 (anything else fails), and
`cmp`s the fresh output against the committed record. Changing the manifest,
cited evidence, or the vendored checklist without regenerating the record
fails the check. The version is pinned exactly because the record is
byte-compared; bump the pin and regenerate the record in the same PR.
