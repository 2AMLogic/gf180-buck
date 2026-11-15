"""Tripwire: ROADMAP.md's header stamp anchors into main's history and warns
when it has drifted far behind it.

ROADMAP.md opens with a stamped status header ("Status as of <date>,
`main` @ `<sha>`"). Every claim in the file is true at that sha and may be
stale at HEAD; #190 ratified the framing, and #199 asks that the stamp's
distance from main carry a signal instead of being discovered at review
time. The measured drift it responds to: stamp a3cb225 was ~34 hours and 16
substantive landings behind main while all four "## Now" items had closed.

Severity split (warn, not fail, on staleness; this is a narrative document):

- FAIL: the header stamp is absent or unparseable - an unusable anchor must
  never read as a pass (same choice as test_docs_staging_pins.py).
- FAIL: the stamp sha is resolvable but is not an ancestor of HEAD - a typo
  or a sha from an abandoned branch, the genuinely bad state.
- SKIP (named reason): the clone is shallow, or the stamp sha is missing
  from the object store. A depth-1 checkout cannot answer the ancestry
  question at all: `git merge-base --is-ancestor` exits 128 there, which
  must never be read as "not an ancestor" (it would flag every PR). CI
  checks out with fetch-depth: 0 precisely so this test can run for real.
- WARN only: the stamp is a valid ancestor but more than
  DOC_EXCLUDING_DRIFT_WARN substantive (doc-excluding) first-parent landings
  behind HEAD. Printed to stderr, exit 0; no staleness distance can fail
  the suite.

Hosted in the existing stdlib suite (npm test -> unittest discover -s
manifests) rather than a new workflow or an item-10 checks[] entry: a
roadmap-staleness warning must not be able to change the T1 tier verdict
of record.
"""

import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ROADMAP_PATH = REPO_ROOT / "ROADMAP.md"

# A landing that touches only these paths is roadmap-refresh traffic (the
# file's own re-stamping), not tracker drift, so it does not count toward
# the distance warning.
DOC_ONLY_PATHS = frozenset({"ROADMAP.md", "WORK_PLAN.md", "README.md"})

# Warn past this many substantive first-parent landings since the stamp.
# Derivation (measured 2026-11-15, main @ 0d96844 line, first-parent landings
# whose diff touches any path outside DOC_ONLY_PATHS): main lands ~5.3
# substantive PRs/day on a 7-day average (37 in 7 days, wide day-to-day
# spread), and the worst observed neglect - stamp a3cb225 vs main ~34 hours
# later - was 16 substantive landings, with all four "## Now" items closed.
# Ten is about two average days of drift: a normal day stays quiet, the
# measured bad state fires. Tunable; not defended as optimal.
DOC_EXCLUDING_DRIFT_WARN = 10

# The stamp lives in the header block near the top of the file; searching
# only the first lines keeps a body quote of the same shape from shadowing
# the header stamp if one is ever added.
_STAMP_SEARCH_LINES = 15
_STAMP_RE = re.compile(r"`main` @ `([0-9a-f]{7,40})`")


def parse_stamp(text):
    """The stamped `main` @ `<sha>` from the ROADMAP.md header block.

    Raises ValueError when the header block carries no parseable stamp: the
    caller fails, it never passes on an unusable anchor.
    """
    header = "\n".join(text.splitlines()[:_STAMP_SEARCH_LINES])
    m = _STAMP_RE.search(header)
    if m is None:
        raise ValueError(
            "no parseable `main` @ `<sha>` status stamp in the first "
            f"{_STAMP_SEARCH_LINES} lines of ROADMAP.md - the header stamp "
            "anchor moved or was removed; restore it or re-point this test"
        )
    return m.group(1)


def _git(args, cwd=REPO_ROOT):
    return subprocess.run(
        ["git"] + args, cwd=str(cwd), capture_output=True, text=True
    )


def is_shallow(cwd=REPO_ROOT):
    r = _git(["rev-parse", "--is-shallow-repository"], cwd)
    if r.returncode != 0:
        raise unittest.SkipTest(
            f"cannot probe shallow state of {cwd} "
            f"(git rev-parse --is-shallow-repository exited {r.returncode}); "
            "cannot judge the stamp"
        )
    return r.stdout.strip() == "true"


def object_missing(sha, cwd=REPO_ROOT):
    return _git(["cat-file", "-e", f"{sha}^{{commit}}"], cwd).returncode != 0


def assert_stamp_ancestor(sha, cwd=REPO_ROOT):
    """The stamp sha is an ancestor of HEAD: pass, fail, or skip-with-reason."""
    if is_shallow(cwd):
        raise unittest.SkipTest(
            f"shallow clone at {cwd}: {sha} may simply be absent from a "
            "truncated object store, so ancestry cannot be judged here "
            "(CI checks out with fetch-depth: 0 to run this for real)"
        )
    if object_missing(sha, cwd):
        raise unittest.SkipTest(
            f"stamped object {sha} is missing from the object store at "
            f"{cwd} (this is the state where --is-ancestor exits 128); "
            "cannot judge ancestry"
        )
    r = _git(["merge-base", "--is-ancestor", sha, "HEAD"], cwd)
    if r.returncode == 1:
        raise AssertionError(
            f"ROADMAP.md stamps `main` @ `{sha}`, which is resolvable but is "
            f"NOT an ancestor of HEAD at {cwd}: a typo, or a sha from an "
            "abandoned branch. Re-stamp the header from a main commit."
        )
    if r.returncode != 0:
        raise unittest.SkipTest(
            f"git merge-base --is-ancestor exited {r.returncode} for {sha} "
            f"({r.stderr.strip()}); cannot judge ancestry"
        )


def doc_excluding_distance(sha, cwd=REPO_ROOT):
    """(substantive, total) first-parent landings between the stamp and HEAD.

    A landing is one commit on the first-parent line of sha..HEAD (a merge
    counts once, carrying its whole merged PR, via -m --first-parent); it is
    substantive when its diff touches any path outside DOC_ONLY_PATHS.
    Commits with no file list (rare empty landings) count as total only.
    """
    r = _git(
        ["log", "--format=%x00%H", "--name-only", "-m", "--first-parent",
         f"{sha}..HEAD"],
        cwd,
    )
    if r.returncode != 0:
        raise unittest.SkipTest(
            f"cannot walk {sha}..HEAD at {cwd} "
            f"(git log exited {r.returncode}: {r.stderr.strip()}); "
            "cannot measure drift"
        )
    substantive = total = 0
    for chunk in r.stdout.split("\x00"):
        chunk = chunk.strip("\n")
        if not chunk:
            continue
        paths = [l.strip() for l in chunk.split("\n")[1:] if l.strip()]
        total += 1
        if paths and not set(paths) <= DOC_ONLY_PATHS:
            substantive += 1
    return substantive, total


def stamp_distance_warning(sha, cwd=REPO_ROOT):
    """A stderr warning string past the threshold, or None. Never raises
    for staleness: distance is a signal, not a verdict."""
    substantive, total = doc_excluding_distance(sha, cwd)
    if substantive <= DOC_EXCLUDING_DRIFT_WARN:
        return None
    return (
        f"WARNING: ROADMAP.md stamps `main` @ `{sha}`, which predates "
        f"{substantive} substantive first-parent landings ({total} total) "
        f"at {cwd}: the tracker state it describes has had plenty of "
        "opportunity to drift. Re-read the tracker and refresh the roadmap "
        f"pass (> {DOC_EXCLUDING_DRIFT_WARN} substantive landings)."
    )


def _run(args, cwd):
    return subprocess.run(args, cwd=str(cwd), capture_output=True, text=True)


def scratch_repo(tmp):
    """A two-commit scratch git repo on `main`; returns (repo_path, sha)."""
    repo = Path(tmp) / "scratch"
    repo.mkdir()
    assert _run(["git", "init", "-b", "main", "."], repo).returncode == 0
    _run(["git", "config", "user.email", "stamp-test@example.com"], repo)
    _run(["git", "config", "user.name", "stamp-test"], repo)
    (repo / "design").mkdir()
    (repo / "design" / "root.spice").write_text("* root\n")
    assert _run(["git", "add", "-A"], repo).returncode == 0
    assert _run(["git", "commit", "-m", "root"], repo).returncode == 0
    sha = _run(["git", "rev-parse", "HEAD"], repo).stdout.strip()
    return repo, sha


def unrelated_root_commit(repo):
    """A resolvable commit with no parent, outside the scratch repo's
    history - the "typo / abandoned branch" sha as a real object."""
    blob = subprocess.run(
        ["git", "hash-object", "-w", "--stdin"], cwd=str(repo),
        input="unrelated\n", capture_output=True, text=True)
    assert blob.returncode == 0, blob.stderr
    tree = subprocess.run(
        ["git", "mktree"], cwd=str(repo),
        input=f"100644 blob {blob.stdout.strip()}\tx.spice\n",
        capture_output=True, text=True)
    assert tree.returncode == 0, tree.stderr
    commit = _run(
        ["git", "commit-tree", tree.stdout.strip(), "-m", "unrelated root"],
        repo)
    assert commit.returncode == 0, commit.stderr
    return commit.stdout.strip()


class RoadmapHeaderStamp(unittest.TestCase):
    """The real repo state."""

    def test_header_stamp_is_parseable(self):
        # ValueError propagates as a test error: an absent/unparseable
        # stamp must fail, never pass vacuously.
        parse_stamp(ROADMAP_PATH.read_text(encoding="utf-8"))

    def test_stamp_sha_is_ancestor_of_head(self):
        sha = parse_stamp(ROADMAP_PATH.read_text(encoding="utf-8"))
        assert_stamp_ancestor(sha)

    def test_stamp_drift_warns_but_never_fails(self):
        sha = parse_stamp(ROADMAP_PATH.read_text(encoding="utf-8"))
        warning = stamp_distance_warning(sha)
        if warning is not None:
            print(warning, file=sys.stderr)


class StampParsing(unittest.TestCase):
    """Fixture-driven proof an unusable anchor fails."""

    def test_absent_header_fails(self):
        with self.assertRaises(ValueError):
            parse_stamp("# Roadmap\n\nNo status line here.\n")

    def test_stamp_with_wrong_shape_fails(self):
        with self.assertRaises(ValueError):
            parse_stamp("**Status as of 2026-11-15; main at a3cb225.**\n")

    def test_abbreviated_and_full_sha_both_parse(self):
        text = "**Status as of 2026-11-15, `main` @ `a3cb225f`; ok.**\n"
        self.assertEqual(parse_stamp(text), "a3cb225f")
        full = "a" * 40
        self.assertEqual(
            parse_stamp(f"**`main` @ `{full}`; ok.**\n"), full)

    def test_body_shadowing_is_ignored(self):
        # A quote of the stamp shape deeper in the file must not satisfy
        # the header search.
        body = "# Roadmap\n\n" + "\n" * 20 + "see `main` @ `1111111`\n"
        with self.assertRaises(ValueError):
            parse_stamp(body)


class StampAncestry(unittest.TestCase):
    """Fixture-driven ancestry outcomes in throwaway scratch repos."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="roadmap-stamp-")
        self.addCleanup(self._tmp.cleanup)
        self.repo, self.root_sha = scratch_repo(self._tmp.name)

    def test_resolvable_non_ancestor_fails(self):
        sha = unrelated_root_commit(self.repo)
        with self.assertRaises(AssertionError) as ctx:
            assert_stamp_ancestor(sha, cwd=self.repo)
        self.assertIn("NOT an ancestor", str(ctx.exception))
        self.assertIn(sha[:7], str(ctx.exception))

    def test_ancestor_passes(self):
        assert_stamp_ancestor(self.root_sha, cwd=self.repo)

    def test_missing_object_skips_not_fails(self):
        missing = _run(
            ["git", "hash-object", "--stdin"], self.repo).stdout.strip()
        with self.assertRaises(unittest.SkipTest) as ctx:
            assert_stamp_ancestor(missing, cwd=self.repo)
        self.assertIn("missing from the object store", str(ctx.exception))

    def test_shallow_clone_skips_not_fails(self):
        clone = Path(self._tmp.name) / "shallow"
        r = _run(
            ["git", "clone", "--depth", "1",
             f"file://{self.repo.resolve()}", str(clone)], self.repo)
        self.assertEqual(r.returncode, 0, r.stderr)
        with self.assertRaises(unittest.SkipTest) as ctx:
            assert_stamp_ancestor(self.root_sha, cwd=clone)
        self.assertIn("shallow clone", str(ctx.exception))


class StampDistance(unittest.TestCase):
    """The doc-excluding distance signal: warn only, never fail."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="roadmap-stamp-")
        self.addCleanup(self._tmp.cleanup)
        self.repo, self.root_sha = scratch_repo(self._tmp.name)

    def _landing(self, paths):
        for path, content in paths.items():
            target = self.repo / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content)
        _run(["git", "add", "-A"], self.repo)
        assert _run(["git", "commit", "-m", "landing"], self.repo).returncode == 0

    def test_doc_only_landings_are_excluded(self):
        self._landing({"ROADMAP.md": "# refreshed\n"})
        self._landing({"WORK_PLAN.md": "# plan\n"})
        self._landing({"design/foo.spice": "* substantive\n"})
        substantive, total = doc_excluding_distance(self.root_sha, cwd=self.repo)
        self.assertEqual((substantive, total), (1, 3))

    def test_merge_landing_counts_once_with_its_content(self):
        # A landed PR branch (three substantive commits) merged to the
        # first-parent line counts as one substantive landing, not four.
        _run(["git", "checkout", "-b", "pr"], self.repo)
        for i in range(3):
            self._landing({f"design/p{i}.spice": f"* p{i}\n"})
        _run(["git", "checkout", "main"], self.repo)
        self._landing({"ROADMAP.md": "# stale\n"})  # land a doc-only commit
        assert _run(["git", "merge", "--no-ff", "pr", "-m", "merge pr"],
                    self.repo).returncode == 0
        substantive, total = doc_excluding_distance(self.root_sha, cwd=self.repo)
        # One block per first-parent landing: the doc-only main-line commit,
        # and the merge counting ONCE while carrying the PR's substantive
        # content (not four blocks, and not a zero-path merge).
        self.assertEqual((substantive, total), (1, 2))

    def test_large_distance_warns_and_exits_clean(self):
        # The measured bad state: many substantive landings past the stamp.
        for i in range(DOC_EXCLUDING_DRIFT_WARN + 6):
            self._landing({f"design/f{i}.spice": f"* {i}\n"})
        warning = stamp_distance_warning(self.root_sha, cwd=self.repo)
        self.assertIsNotNone(warning)
        self.assertIn("WARNING", warning)
        self.assertIn(str(DOC_EXCLUDING_DRIFT_WARN + 6), warning)

    def test_doc_only_heavy_history_stays_quiet(self):
        # Twenty refresh-only landings are not drift: the counter excludes
        # them, so no warning fires even though the window is long.
        for i in range(20):
            self._landing({"ROADMAP.md": f"# refresh {i}\n"})
        self.assertIsNone(stamp_distance_warning(self.root_sha, cwd=self.repo))
        substantive, total = doc_excluding_distance(self.root_sha, cwd=self.repo)
        self.assertEqual((substantive, total), (0, 20))


if __name__ == "__main__":
    unittest.main()
