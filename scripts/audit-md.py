#!/usr/bin/env python3
"""Audit .md files in the repo: find orphans and broken cross-references.

A markdown file is considered USED if either:
  - It is an auto-used entry point (README.md, AGENTS.md, CLAUDE.md, VERSION.md, SKILL.md)
  - Its basename or repo-relative path appears inside another scanned file.

Scanned files: every *.md, *.yaml, *.yml, *.json under the repo, plus everything under .claude/.

Output sections:
  USED         — file + ref count
  ORPHANS      — candidates to delete or to link from somewhere
  BROKEN_REFS  — markdown links pointing to .md files that do not exist

Exit code: 0 if clean, 1 if any orphan or broken ref is found.

Usage:
  python3 scripts/audit-md.py
  python3 scripts/audit-md.py --quiet         # only ORPHANS + BROKEN_REFS
  python3 scripts/audit-md.py --fix-hints     # add ownership hints per orphan
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

EXCLUDE_DIR_NAMES = {".git", "node_modules"}
EXCLUDE_PATH_PREFIXES = (".claude/plugins/cache",)

AUTO_USED_BASENAMES = {
    "README.md",
    "AGENTS.md",
    "CLAUDE.md",
    "VERSION.md",
    "SKILL.md",
}

SCAN_EXTENSIONS = {".md", ".yaml", ".yml", ".json"}

MD_LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")


def _is_excluded(rel_dir: str) -> bool:
    for pref in EXCLUDE_PATH_PREFIXES:
        if rel_dir == pref or rel_dir.startswith(pref + "/"):
            return True
    return False


def walk_repo() -> tuple[list[Path], list[Path]]:
    """Return (all_md_files, all_scan_files)."""
    md_files: list[Path] = []
    scan_files: list[Path] = []
    for root, dirs, files in os.walk(REPO_ROOT):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIR_NAMES]
        rel_root = Path(root).relative_to(REPO_ROOT).as_posix()
        if _is_excluded(rel_root):
            dirs[:] = []
            continue
        for f in files:
            full = Path(root) / f
            ext = full.suffix.lower()
            rel = full.relative_to(REPO_ROOT).as_posix()
            if ext == ".md":
                md_files.append(full)
            if ext in SCAN_EXTENSIONS or rel.startswith(".claude/"):
                scan_files.append(full)
    md_files.sort()
    return md_files, scan_files


def is_auto_used(p: Path) -> bool:
    return p.name in AUTO_USED_BASENAMES


def suggest_owner(rel_path: str) -> str | None:
    rules = [
        ("docs/gdd/", "register id in docs/registry/architecture.yaml or link from another GDD doc"),
        ("docs/sdd/", "register id in docs/registry/architecture.yaml"),
        ("docs/tdd/", "link from its parent SDD"),
        ("docs/plans/", "link from docs/plans/README.md"),
        ("docs/decisions/", "link from docs/decisions/README.md"),
        ("docs/process/", "link from AGENTS.md or .claude/agents/<role>.md"),
        ("docs/engine-reference/", "link from AGENTS.md or .claude/rules/gameplay-code.md"),
        ("docs/registry/", "link from AGENTS.md"),
        ("docs/specs/", "link from docs/plans/<plan>.md when implementation begins"),
        (".claude/agents/", "list in .claude/agents/README.md"),
        (".claude/rules/", "list in .claude/rules/README.md"),
        (".claude/skills/", "ensure SKILL.md references it, or remove"),
    ]
    for pref, hint in rules:
        if rel_path.startswith(pref):
            return hint
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--quiet", action="store_true", help="only print ORPHANS and BROKEN_REFS")
    ap.add_argument("--fix-hints", action="store_true", help="suggest where each orphan could be linked from")
    args = ap.parse_args()

    md_files, scan_files = walk_repo()

    content_cache: dict[Path, str] = {}
    for sf in scan_files:
        try:
            content_cache[sf] = sf.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            content_cache[sf] = ""

    refs: dict[Path, list[Path]] = defaultdict(list)
    for md in md_files:
        rel = md.relative_to(REPO_ROOT).as_posix()
        base = md.name
        for sf, content in content_cache.items():
            if sf == md:
                continue
            if base in content or rel in content:
                refs[md].append(sf)

    md_resolved = {p.resolve() for p in md_files}
    broken: list[tuple[Path, str]] = []
    for md in md_files:
        content = content_cache.get(md, "")
        for m in MD_LINK_RE.finditer(content):
            target = m.group(1).split("#", 1)[0].strip()
            if not target or not target.endswith(".md"):
                continue
            if target.startswith(("http://", "https://", "mailto:", "/")):
                # Absolute URLs and root-absolute paths skipped to avoid false positives.
                continue
            try:
                resolved = (md.parent / target).resolve()
            except Exception:
                continue
            if resolved not in md_resolved:
                broken.append((md, target))

    used: list[Path] = []
    orphans: list[Path] = []
    for md in md_files:
        if is_auto_used(md) or refs[md]:
            used.append(md)
        else:
            orphans.append(md)

    def rel(p: Path) -> str:
        return p.relative_to(REPO_ROOT).as_posix()

    if not args.quiet:
        print(f"# MD audit — {len(md_files)} files scanned")
        print()
        print(f"## USED ({len(used)})")
        print()
        for md in used:
            n = len(refs[md])
            tag = "auto" if (is_auto_used(md) and n == 0) else f"{n} ref(s)"
            print(f"  {rel(md):<70}  [{tag}]")
        print()

    print(f"## ORPHANS ({len(orphans)})")
    print()
    if not orphans:
        print("  (none)")
    for md in orphans:
        print(f"  {rel(md)}")
        if args.fix_hints:
            hint = suggest_owner(rel(md))
            if hint:
                print(f"    hint: {hint}")
    print()

    print(f"## BROKEN_REFS ({len(broken)})")
    print()
    if not broken:
        print("  (none)")
    for src, link in broken:
        print(f"  {rel(src)} -> {link}")

    return 1 if (orphans or broken) else 0


if __name__ == "__main__":
    sys.exit(main())
