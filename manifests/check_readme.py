#!/usr/bin/env python3
"""T1 item 10 hygiene check: README structure and relative links.

Exits 0 when README.md has the required sections and every relative link
resolves to an existing repository path; prints each problem and exits 1
otherwise. Stdlib only. Run from the repository root:
    python3 -I manifests/check_readme.py
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REQUIRED = ("## Target specification", "## Reproduce", "## License")

text = (ROOT / "README.md").read_text(encoding="utf-8")
problems = [f"README.md: missing section '{h}'" for h in REQUIRED if h not in text]
if "spec/target-spec.md" not in text:
    problems.append("README.md: does not link spec/target-spec.md")

for target in re.findall(r"\]\(([^)\s]+)\)", text):
    if re.match(r"[a-z][a-z0-9+.-]*:", target) or target.startswith("#"):
        continue
    path = target.split("#", 1)[0]
    if path and not (ROOT / path).exists():
        problems.append(f"README.md: broken relative link '{target}'")

for line in problems:
    print(line, file=sys.stderr)
sys.exit(1 if problems else 0)
