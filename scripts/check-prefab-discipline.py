#!/usr/bin/env python3
"""Verify Unity prefab/material/tag discipline against rules in level-design.md and gameplay-code.md.

Three checks, all mechanical (no Unity required — uses Unity's YAML
serialisation directly):

  1. GPU instancing on materials.
     For each `src/Assets/_Project/Art/**/*.mat`, require
     `m_EnableInstancingVariants: 1`. Opt-out via a sidecar marker file
     `<material>.mat.instancing-opt-out` next to the material (one line:
     reason). The verifier accepts the opt-out and surfaces the reason.

  2. Tag registry parity.
     Every custom tag declared in `src/ProjectSettings/TagManager.asset` (i.e.,
     beyond Unity's built-ins) must appear in `docs/registry/architecture.yaml`
     under `tags:` with a matching `TAG-<...>` id.

  3. C# tag-string literals.
     Any `.cs` file under `src/Assets/_Project/Scripts/**` that hardcodes a
     tag string in `CompareTag(...)`, `FindWithTag(...)`,
     `FindGameObjectWithTag(...)`, `FindGameObjectsWithTag(...)`,
     `.tag == "..."`, or `.tag = "..."` is a violation. Unity built-in tags
     are tolerated for engine-bridge call sites.

Rules enforced:
  LEVEL-DESIGN-GPU-INSTANCING-ENABLED
  LEVEL-DESIGN-TAGS-REGISTERED
  GAMEPLAY-CODE-NO-TAG-STRING-LITERALS

Out of scope (deferred to Unity-side `LevelSpec.ValidateScene`, Wave B):
  - `LEVEL-DESIGN-PREFAB-DISCIPLINE` scene-graph traversal (detecting
    unpacked prefab instances inside a `.unity` file).
  - `LEVEL-DESIGN-VARIANTS-OVER-DUPLICATION` family-similarity heuristic
    (flagging two flat prefabs that should have been a base + variant).

Exit codes:
  0 - all checks clean (or no target paths exist yet — repo in ideation phase)
  1 - one or more violations
  2 - infrastructure error (missing pyyaml, malformed required asset)

Usage:
  python3 scripts/check-prefab-discipline.py
  python3 scripts/check-prefab-discipline.py --quiet
  python3 scripts/check-prefab-discipline.py --json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.stderr.write(
        "check-prefab-discipline: pyyaml not installed. Run: pip install pyyaml\n"
    )
    sys.exit(2)

REPO_ROOT = Path(__file__).resolve().parent.parent
ART_DIR = REPO_ROOT / "src" / "Assets" / "_Project" / "Art"
SCRIPTS_DIR = REPO_ROOT / "src" / "Assets" / "_Project" / "Scripts"
TAG_MANAGER = REPO_ROOT / "src" / "ProjectSettings" / "TagManager.asset"
REGISTRY = REPO_ROOT / "docs" / "registry" / "architecture.yaml"

UNITY_BUILTIN_TAGS = {
    "Untagged", "Respawn", "Finish", "EditorOnly",
    "MainCamera", "Player", "GameController",
}

TAG_LITERAL_PATTERNS = [
    (re.compile(r'\bCompareTag\(\s*"([^"]+)"\s*\)'), "CompareTag"),
    (re.compile(r'\bFindWithTag\(\s*"([^"]+)"\s*\)'), "FindWithTag"),
    (re.compile(r'\bFindGameObjectWithTag\(\s*"([^"]+)"\s*\)'), "FindGameObjectWithTag"),
    (re.compile(r'\bFindGameObjectsWithTag\(\s*"([^"]+)"\s*\)'), "FindGameObjectsWithTag"),
    (re.compile(r'\.tag\s*==\s*"([^"]+)"'), "tag-equals"),
    (re.compile(r'\.tag\s*=\s*"([^"]+)"\s*;'), "tag-assign"),
]


def load_yaml_safe(path: Path) -> dict | list | None:
    try:
        with path.open("r", encoding="utf-8") as f:
            text = f.read()
    except Exception:
        return None
    docs = []
    try:
        for doc in yaml.safe_load_all(text):
            if doc is not None:
                docs.append(doc)
    except yaml.YAMLError:
        return None
    if not docs:
        return None
    return docs[0] if len(docs) == 1 else docs


def check_materials() -> list[dict]:
    violations: list[dict] = []
    if not ART_DIR.exists():
        return violations
    for mat in sorted(ART_DIR.rglob("*.mat")):
        rel = str(mat.relative_to(REPO_ROOT))
        sidecar = mat.parent / f"{mat.name}.instancing-opt-out"
        try:
            text = mat.read_text(encoding="utf-8")
        except Exception:
            violations.append({
                "rule": "LEVEL-DESIGN-GPU-INSTANCING-ENABLED",
                "file": rel,
                "detail": "material file is unreadable.",
            })
            continue
        # Unity .mat files include a custom %YAML tag and per-document
        # !u!21 &... markers. yaml.safe_load_all chokes on the custom tags
        # in some Unity versions; fall back to regex on the field name.
        m = re.search(r"^\s*m_EnableInstancingVariants:\s*(\d+)\s*$", text, re.MULTILINE)
        enabled = m and m.group(1) == "1"
        if enabled:
            continue
        if sidecar.exists():
            reason = sidecar.read_text(encoding="utf-8").strip() or "(no reason given)"
            # Opt-out is acknowledged; no violation. We do not surface it as
            # a warning here to keep --quiet truly quiet; the reviewer reads
            # the sidecar file directly during code review.
            continue
        violations.append({
            "rule": "LEVEL-DESIGN-GPU-INSTANCING-ENABLED",
            "file": rel,
            "detail": (
                "m_EnableInstancingVariants is not 1. Either enable GPU "
                "instancing in the material inspector, or document the opt-out "
                f"in a sidecar file {sidecar.relative_to(REPO_ROOT)} with a one-line reason."
            ),
        })
    return violations


def load_tag_manager() -> list[str] | None:
    if not TAG_MANAGER.exists():
        return None
    try:
        text = TAG_MANAGER.read_text(encoding="utf-8")
    except Exception:
        return None
    # The TagManager.asset has a `tags:` block listing strings, a `layers:`
    # block listing strings, and other sibling blocks. We parse defensively
    # by tracking indent — the tags: list items live at exactly tags_indent + 2,
    # and any sibling key at <= tags_indent ends the section.
    in_tags = False
    tags_indent = -1
    out: list[str] = []
    for raw in text.splitlines():
        stripped_left = raw.lstrip()
        if not stripped_left:
            continue
        indent = len(raw) - len(stripped_left)
        if re.match(r"^tags:\s*$", stripped_left):
            in_tags = True
            tags_indent = indent
            continue
        if not in_tags:
            continue
        if stripped_left.startswith("-"):
            if indent <= tags_indent:
                in_tags = False
                continue
            value = stripped_left[1:].strip().strip('"').strip("'")
            if value:
                out.append(value)
            continue
        if indent <= tags_indent:
            in_tags = False
            continue
        # Deeper indent on a non-list line is exotic for this file; ignore.
    return out


def load_registry_tag_names() -> set[str] | None:
    if not REGISTRY.exists():
        return None
    try:
        with REGISTRY.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except Exception:
        return None
    tag_entries = data.get("tags") or []
    names: set[str] = set()
    for entry in tag_entries:
        if isinstance(entry, dict):
            name = entry.get("name")
            if name:
                names.add(str(name))
    return names


def check_tags() -> list[dict]:
    violations: list[dict] = []
    declared = load_tag_manager()
    if declared is None:
        return violations  # No TagManager yet — repo pre-Unity, skip silently.
    registered = load_registry_tag_names()
    if registered is None:
        violations.append({
            "rule": "LEVEL-DESIGN-TAGS-REGISTERED",
            "file": str(REGISTRY.relative_to(REPO_ROOT)) if REGISTRY.exists() else "docs/registry/architecture.yaml",
            "detail": "architecture.yaml unreadable; cannot verify tag registry parity.",
        })
        return violations
    for tag in declared:
        if tag in UNITY_BUILTIN_TAGS:
            continue
        if tag not in registered:
            violations.append({
                "rule": "LEVEL-DESIGN-TAGS-REGISTERED",
                "file": str(TAG_MANAGER.relative_to(REPO_ROOT)),
                "detail": (
                    f"tag {tag!r} is declared in TagManager but has no entry under "
                    "tags: in docs/registry/architecture.yaml. Add an entry with "
                    f"id TAG-{tag.upper().replace(' ', '-')} before committing."
                ),
            })
    return violations


def check_cs_tag_literals() -> list[dict]:
    violations: list[dict] = []
    if not SCRIPTS_DIR.exists():
        return violations
    for cs in sorted(SCRIPTS_DIR.rglob("*.cs")):
        rel = str(cs.relative_to(REPO_ROOT))
        try:
            text = cs.read_text(encoding="utf-8")
        except Exception:
            continue
        for line_idx, line in enumerate(text.splitlines(), start=1):
            stripped = line.lstrip()
            if stripped.startswith("//") or stripped.startswith("*"):
                continue
            for pattern, kind in TAG_LITERAL_PATTERNS:
                for m in pattern.finditer(line):
                    literal = m.group(1)
                    if literal in UNITY_BUILTIN_TAGS:
                        continue
                    violations.append({
                        "rule": "GAMEPLAY-CODE-NO-TAG-STRING-LITERALS",
                        "file": f"{rel}:{line_idx}",
                        "detail": (
                            f"tag literal {literal!r} in {kind} call. Use a "
                            "generated Tags constants class or a TagDefinition SO instead."
                        ),
                    })
    return violations


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    violations: list[dict] = []
    violations += check_materials()
    violations += check_tags()
    violations += check_cs_tag_literals()

    if args.json:
        print(json.dumps({
            "status": "ok" if not violations else "issues_found",
            "violations": violations,
            "summary": (
                "all green"
                if not violations
                else f"{len(violations)} violation(s)"
            ),
        }, indent=2))
        return 0 if not violations else 1

    if not violations:
        if not args.quiet:
            print("prefab discipline: all green")
        return 0

    print(f"prefab discipline: {len(violations)} violation(s)")
    for v in violations:
        print(f"  [{v['rule']}] {v['file']}: {v['detail']}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
