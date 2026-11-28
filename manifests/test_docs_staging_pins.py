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
resync widens the staged set onto another pinned file or shrinks it off the
allowlist. If the create_docs_pr
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


def _function_body(joined, name):
    """Body text of the shell function `name() {`, or None if absent."""
    anchor = re.search(rf"^{name}\(\)\s*\{{", joined, re.M)
    if anchor is None:
        return None
    body = joined[anchor.end():]
    close = re.search(r"^\}", body, re.M)
    return body[: close.start()] if close else body[:4000]


def _literal_tokens(text):
    return {
        token
        for token in (t.strip("'\"") for t in text.split())
        if not (token.startswith("-") or "$" in token or "`" in token or token == ";")
    }


def staged_paths(guide_text, config_pinned=()):
    """Literal paths Guide's docs PR stages.

    Current Loom shape: stage_docs_paths() loops over a fixed set of doc names
    (`for doc_path in A B C; do`) and skips any the repo declared in
    guide.docsMaintenance.pinnedPaths (`config_pinned`). Older shape: a fixed
    `git add` line inside create_docs_pr(). The helper is preferred; the
    legacy parse is the fallback.

    Raises ValueError when no literal staging path can be found: an
    unparseable staging set would otherwise make the overlap check pass
    vacuously on an empty set. Shell-expanded arguments (the per-file archive
    `git add` loop) are not literal staged paths and are ignored.
    """
    joined = re.sub(r"\\\n\s*", " ", guide_text)
    paths = set()
    helper = _function_body(joined, "stage_docs_paths")
    if helper is not None:
        for loop in re.finditer(r"^\s*for\s+\w+\s+in\s+([^;\n]+);\s*do", helper, re.M):
            paths |= _literal_tokens(loop.group(1))
        if not paths:
            raise ValueError(_ANCHOR_MOVED)
        return paths - set(config_pinned)
    body = _function_body(joined, "create_docs_pr")
    if body is None:
        raise ValueError(_ANCHOR_MOVED)
    for add in re.finditer(r"^\s*git\s+(?:-C\s+\S+\s+)?add\s+(.+)$", body, re.M):
        paths |= _literal_tokens(add.group(1))
    if not paths:
        raise ValueError(_ANCHOR_MOVED)
    return paths


def config_pinned_paths():
    """guide.docsMaintenance.pinnedPaths from .loom/config.json (default [])."""
    cfg = json.loads((REPO_ROOT / ".loom" / "config.json").read_text())
    return cfg.get("guide", {}).get("docsMaintenance", {}).get("pinnedPaths", [])


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
        if overlap - ALLOWED_OVERLAP:
            direction = (
                "Extra pinned paths staged: "
                f"{sorted(overlap - ALLOWED_OVERLAP)} - extend the recipe and "
                "ALLOWED_OVERLAP together"
            )
        else:
            direction = (
                "Allowlisted pinned paths no longer staged (overlap shrank): "
                f"{sorted(ALLOWED_OVERLAP - overlap)} - prune the recipe and "
                "ALLOWED_OVERLAP to match"
            )
        raise AssertionError(
            "Guide's docs staging set no longer matches the evidence-pinned "
            "allowlist: a docs PR editing a pinned file it stages can never "
            "pass the signoff record check, and every change to the overlap "
            "is a deliberate one. Update the regeneration recipe in "
            "manifests/README.md (item-10 section) and ALLOWED_OVERLAP "
            "together, or stop staging the file (upstream: "
            f"rjwalters/loom#13897). {direction}"
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
        staged = staged_paths(GUIDE_PATH.read_text(), config_pinned_paths())
        check_overlap(staged & pinned_paths(inventories))

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


class HelperShape(unittest.TestCase):
    """The stage_docs_paths() helper shape (Loom resync, rjwalters/loom#13897)."""

    HELPER = (
        "stage_docs_paths() {\n"
        "  for doc_path in WORK_LOG.md WORK_PLAN.md README.md; do\n"
        "    :\n"
        "  done\n"
        "}\n"
        "create_docs_pr() {\n"
        '  git -C "$DOCS_WT" add -- "$archive_rel"\n'
        "}\n"
    )

    def test_helper_loop_is_parsed(self):
        self.assertEqual(
            staged_paths(self.HELPER), {"WORK_LOG.md", "WORK_PLAN.md", "README.md"}
        )

    def test_config_pinned_path_is_excluded(self):
        self.assertEqual(
            staged_paths(self.HELPER, ["README.md"]), {"WORK_LOG.md", "WORK_PLAN.md"}
        )


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

    def test_shrunk_overlap_message_names_the_stale_allowlist_entry(self):
        # When the upstream fix (rjwalters/loom#13897) lands and README.md
        # stops being staged, the overlap shrinks below the allowlist: the
        # failure must name the stale allowlist entry, not report an empty
        # "extra staged" list.
        text = (
            "create_docs_pr() {\n"
            '  git -C "$DOCS_WT" add WORK_LOG.md WORK_PLAN.md\n'
            "}\n"
        )
        inventories = {
            "item10-inventory.json": {"hygiene": ["README.md"]},
        }
        overlap = staged_paths(text) & pinned_paths(inventories)
        with self.assertRaises(AssertionError) as ctx:
            check_overlap(overlap)
        self.assertIn("no longer staged", str(ctx.exception))
        self.assertIn("README.md", str(ctx.exception))

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
