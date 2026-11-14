"""Tripwire: Guide's docs staging set vs evidence-pinned hygiene files.

Guide's Document Maintenance phase stages a fixed file set inside
create_docs_pr() in .loom/roles/guide.md. On this repo some of those files are
evidence-pinned: their content hash is committed in a
manifests/item*-inventory.json hygiene[] attestation, and CI re-verifies it on
every PR, so a docs PR that edits a pinned file without re-attesting can never
pass. See "Item 10 (repo hygiene) and the verdict of record" in
manifests/README.md for the regeneration cascade a pinned edit must perform.

This test is green while the overlap between the staged set and the pinned set
is exactly ALLOWED_OVERLAP, and goes red with a named cause if a future Loom
resync widens the staged set onto another pinned file. If the create_docs_pr
staging anchor cannot be parsed it FAILS rather than skips: an unparseable
anchor must never read as a pass. The generic defect (hardcoded staging set,
mergeability-blind skip of an open docs PR) is filed upstream at
rjwalters/loom#13897.
"""

import json
import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
GUIDE_PATH = REPO_ROOT / ".loom" / "roles" / "guide.md"
MANIFESTS_DIR = Path(__file__).resolve().parent

# Pinned paths Guide's docs PR is known to stage today. Each entry here must be
# covered by the regeneration recipe in manifests/README.md (item-10 section).
# A new overlap is a deliberate change: extend the recipe and this allowlist
# together, or stop staging the file.
ALLOWED_OVERLAP = {"README.md"}

_ANCHOR_MOVED = "the `create_docs_pr` staging anchor moved - re-point this test"


def staged_paths(guide_text):
    """Literal paths staged by create_docs_pr()'s fixed `git add` line.

    Raises ValueError when the function anchor or a literal staging path cannot
    be found: an unparseable staging set would otherwise make the overlap check
    pass vacuously on an empty set. Shell-expanded arguments (the per-file
    archive `git add` loop) are not literal staged paths and are ignored.
    """
    joined = re.sub(r"\\\n\s*", " ", guide_text)
    anchor = re.search(r"^create_docs_pr\(\)\s*\{", joined, re.M)
    if anchor is None:
        raise ValueError(_ANCHOR_MOVED)
    body = joined[anchor.end():]
    close = re.search(r"^\}", body, re.M)
    body = body[: close.start()] if close else body[:4000]
    paths = set()
    for add in re.finditer(r"^\s*git\s+(?:-C\s+\S+\s+)?add\s+(.+)$", body, re.M):
        for token in add.group(1).split():
            token = token.strip("'\"")
            if token.startswith("-") or "$" in token or "`" in token:
                continue
            paths.add(token)
    if not paths:
        raise ValueError(_ANCHOR_MOVED)
    return paths


def pinned_paths(inventories):
    """Union of hygiene[] members across every item inventory.

    An inventory without a hygiene[] key (item 9's bench inventory, for
    instance) contributes nothing and must not crash the caller.
    """
    paths = set()
    for name in sorted(inventories):
        paths.update(inventories[name].get("hygiene", []))
    return paths


def check_overlap(overlap):
    """The single assertion the tripwire exists for."""
    if overlap != ALLOWED_OVERLAP:
        raise AssertionError(
            "Guide's docs staging set overlaps evidence-pinned files beyond the "
            "allowlist: a docs PR editing one can never pass the signoff record "
            "check. Extend the regeneration recipe in manifests/README.md "
            "(item-10 section) and update ALLOWED_OVERLAP deliberately, or stop "
            "staging the file (upstream: rjwalters/loom#13897). Extra pinned "
            f"paths staged: {sorted(overlap - ALLOWED_OVERLAP)}"
        )


class DocsStagingPins(unittest.TestCase):
    """The real repo state."""

    def test_staged_overlap_matches_allowlist(self):
        inventories = {
            p.name: json.loads(p.read_text())
            for p in sorted(MANIFESTS_DIR.glob("item*-inventory.json"))
        }
        self.assertTrue(
            inventories, "no manifests/item*-inventory.json found - glob broke"
        )
        overlap = staged_paths(GUIDE_PATH.read_text()) & pinned_paths(inventories)
        check_overlap(overlap)

    def test_parse_failure_is_a_failure_not_a_pass(self):
        # A resync that moves or rewrites the staging line must fail loudly
        # here, never skip-as-pass on an unparseable (empty) staged set.
        with self.assertRaises(ValueError) as no_anchor:
            staged_paths('docs_pr() {\n  git add -A\n}\n')
        self.assertIn("anchor moved", str(no_anchor.exception))
        with self.assertRaises(ValueError) as no_literals:
            staged_paths(
                'create_docs_pr() {\n'
                '  git -C "$DOCS_WT" add "$DOCS_STAGED"\n'
                '}\n'
            )
        self.assertIn("anchor moved", str(no_literals.exception))


class NegativeCases(unittest.TestCase):
    """Fixture-driven proof the tripwire trips; no .loom/roles/guide.md edit."""

    def test_widened_staged_set_fails(self):
        # Staging line widened onto a second pinned path (LICENSE is in
        # item10's hygiene[]): the overlap check must reject it, naming the
        # extra path and pointing at the recipe.
        text = (
            "create_docs_pr() {\n"
            '  git -C "$DOCS_WT" add WORK_LOG.md WORK_PLAN.md README.md LICENSE\n'
            "}\n"
        )
        inventories = {
            "item9-inventory.json": {"schema_version": 1},
            "item10-inventory.json": {
                "hygiene": ["README.md", "LICENSE"],
            },
        }
        overlap = staged_paths(text) & pinned_paths(inventories)
        with self.assertRaises(AssertionError) as ctx:
            check_overlap(overlap)
        self.assertIn("LICENSE", str(ctx.exception))

    def test_new_pinned_inventory_fails(self):
        # Same staging line, but a future inventory pins WORK_PLAN.md: the
        # glob must pick the new inventory up and the check must fail.
        text = (
            "create_docs_pr() {\n"
            '  git -C "$DOCS_WT" add WORK_LOG.md WORK_PLAN.md README.md\n'
            "}\n"
        )
        inventories = {
            "item10-inventory.json": {"hygiene": ["README.md"]},
            "item11-inventory.json": {"hygiene": ["WORK_PLAN.md"]},
        }
        overlap = staged_paths(text) & pinned_paths(inventories)
        with self.assertRaises(AssertionError) as ctx:
            check_overlap(overlap)
        self.assertIn("WORK_PLAN.md", str(ctx.exception))

    def test_inventory_without_hygiene_key_is_tolerated(self):
        text = (
            "create_docs_pr() {\n"
            '  git -C "$DOCS_WT" add WORK_LOG.md WORK_PLAN.md README.md\n'
            "}\n"
        )
        inventories = {
            "item9-inventory.json": {"schema_version": 1, "benches": ["a.sh"]},
            "item10-inventory.json": {"hygiene": ["README.md"]},
        }
        overlap = staged_paths(text) & pinned_paths(inventories)
        check_overlap(overlap)  # no crash, and still exactly the allowlist

    def test_archived_files_are_not_staged_paths(self):
        # The per-file archive loop stages shell-expanded paths; they are not
        # part of the literal staging set.
        text = (
            "create_docs_pr() {\n"
            '  git -C "$DOCS_WT" add WORK_LOG.md WORK_PLAN.md README.md\n'
            '  for f in "$DOCS_WT"/work_log/*.md; do\n'
            '    git -C "$DOCS_WT" add -- "work_log/${f##*/}"\n'
            "  done\n"
            "}\n"
        )
        self.assertEqual(staged_paths(text), {"WORK_LOG.md", "WORK_PLAN.md", "README.md"})


if __name__ == "__main__":
    unittest.main()
