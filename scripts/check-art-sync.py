#!/usr/bin/env python3
"""Layer A sync verifier — Blender source ↔ Unity import parity.

Hash-only + cross-reference check. Does not require Unity. Run before commit
or via /verify-art-sync. The Unity-side Layer B (Wave B) adds importer-setting
verification through [MenuItem("LastBreath/Art/Verify Sync")].

Schema: docs/process/asset-design.md §5.
Rules: .claude/rules/asset-design.md (ASSET-DESIGN-SYNC-PARITY).
Rationale: ADR-0008 §Sync verification.

Checks:
  1. For every manifest with approved: true and imported_at != null:
     - sha256(<glb>) == manifest.imported_hash                  → hash_drift
     - manifest.target_unity_path exists on disk                → target_missing
  2. For every prefab/mesh ref in docs/levels/**/*.layout.yaml:
     - resolves to a manifest's target_unity_path               → unmanifested_target
     - matching manifest is approved + imported                 → unapproved_target
  3. For every file under src/Assets/_Project/Art/**:
     - has a manifest's target_unity_path matching              → unmanifested_target

Exit 0 if clean, 1 if any violation, 2 on infrastructure error (e.g., missing pyyaml).

Usage:
  python3 scripts/check-art-sync.py
  python3 scripts/check-art-sync.py --asset ART-CORRIDOR-PANEL-01
  python3 scripts/check-art-sync.py --quiet
  python3 scripts/check-art-sync.py --json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.stderr.write(
        "check-art-sync: pyyaml not installed. Run: pip install pyyaml\n"
    )
    sys.exit(2)

REPO_ROOT = Path(__file__).resolve().parent.parent
# Source-side staging (editable Blender pipeline). Canonical roots per
# AGENTS.md §File conventions: art/ for editable source, src/Assets/ for
# the Unity project (which is the imported destination).
ART_SRC = REPO_ROOT / "art"
UNITY_ART = REPO_ROOT / "src" / "Assets" / "_Project" / "Art"
LEVELS_DIR = REPO_ROOT / "docs" / "levels"

PREFAB_REF_RE = re.compile(r"(?:prefab|mesh):\s*(\S+)")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def load_manifests() -> dict[str, dict]:
    out: dict[str, dict] = {}
    if not ART_SRC.exists():
        return out
    for mp in ART_SRC.glob("*/manifest.yaml"):
        try:
            with mp.open("r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        except Exception:
            continue
        data["_manifest_path"] = str(mp.relative_to(REPO_ROOT))
        data["_asset_dir"] = str(mp.parent.relative_to(REPO_ROOT))
        out[data.get("id", str(mp.parent.name))] = data
    return out


def gather_layout_refs() -> list[tuple[str, str]]:
    refs = []
    if not LEVELS_DIR.exists():
        return refs
    for lp in LEVELS_DIR.rglob("*.layout.yaml"):
        try:
            text = lp.read_text(encoding="utf-8")
        except Exception:
            continue
        for m in PREFAB_REF_RE.finditer(text):
            ref = m.group(1).strip().rstrip(",")
            if ref.startswith("src/Assets/_Project/Art/"):
                refs.append((str(lp.relative_to(REPO_ROOT)), ref))
    return refs


def gather_unity_files() -> list[Path]:
    if not UNITY_ART.exists():
        return []
    return [p for p in UNITY_ART.rglob("*") if p.is_file() and p.suffix != ".meta"]


def check(manifests: dict[str, dict], asset_filter: str | None) -> list[dict]:
    violations: list[dict] = []

    paths_by_manifest = {}
    for asset_id, m in manifests.items():
        if asset_filter and asset_id != asset_filter:
            continue
        target = m.get("target_unity_path")
        if target:
            paths_by_manifest[target] = m

        if m.get("approved") is True and m.get("imported_at") is not None:
            exports = m.get("exports") or []
            if not exports:
                violations.append({
                    "kind": "manifest_malformed",
                    "asset": asset_id,
                    "file": m.get("_manifest_path"),
                    "detail": "approved+imported manifest has no exports[].",
                })
                continue
            glb_rel = exports[0].get("path")
            if not glb_rel:
                violations.append({
                    "kind": "manifest_malformed",
                    "asset": asset_id,
                    "file": m.get("_manifest_path"),
                    "detail": "exports[0].path missing.",
                })
                continue
            glb_path = REPO_ROOT / glb_rel
            if not glb_path.exists():
                violations.append({
                    "kind": "target_missing",
                    "asset": asset_id,
                    "file": glb_rel,
                    "detail": f"Source .glb missing on disk: {glb_rel}.",
                })
            else:
                actual = sha256(glb_path)
                declared = m.get("imported_hash")
                if declared and actual != declared:
                    violations.append({
                        "kind": "hash_drift",
                        "asset": asset_id,
                        "file": glb_rel,
                        "detail": (
                            f"sha256(.glb) != manifest.imported_hash. "
                            f"actual={actual[:16]}…, declared={declared[:16]}…. "
                            "Re-approve via /art-approval-queue."
                        ),
                    })

            if target:
                target_path = REPO_ROOT / target
                if not target_path.exists():
                    violations.append({
                        "kind": "target_missing",
                        "asset": asset_id,
                        "file": target,
                        "detail": "Imported file missing under src/Assets/_Project/Art/.",
                    })

    refs = gather_layout_refs()
    for layout, ref in refs:
        if ref not in paths_by_manifest:
            violations.append({
                "kind": "unmanifested_target",
                "asset": None,
                "file": ref,
                "detail": f"Referenced in {layout} but no manifest claims this target_unity_path.",
            })
            continue
        m = paths_by_manifest[ref]
        if m.get("approved") is not True or m.get("imported_at") is None:
            violations.append({
                "kind": "unapproved_target",
                "asset": m.get("id"),
                "file": ref,
                "detail": (
                    f"Referenced in {layout} but the manifest is "
                    f"approved={m.get('approved')!r} imported_at={m.get('imported_at')!r}."
                ),
            })

    for up in gather_unity_files():
        rel = str(up.relative_to(REPO_ROOT))
        if rel not in paths_by_manifest:
            violations.append({
                "kind": "unmanifested_target",
                "asset": None,
                "file": rel,
                "detail": "File under src/Assets/_Project/Art/ with no manifest.",
            })

    return violations


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--asset", help="focus on a single ART-* id")
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    manifests = load_manifests()
    violations = check(manifests, args.asset)

    if args.json:
        print(json.dumps({
            "status": "ok" if not violations else "issues_found",
            "layer": "A",
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
            print("art sync: all green (layer A)")
        return 0

    print(f"art sync: {len(violations)} violation(s) (layer A)")
    for v in violations:
        asset = v["asset"] or "-"
        print(f"  [{v['kind']}] {asset} {v['file']}: {v['detail']}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
