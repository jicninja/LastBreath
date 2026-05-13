#!/usr/bin/env python3
"""Validate every art/*/manifest.yaml against the schema.

Mechanical enforcement of rules in .claude/rules/asset-design.md:
  - ASSET-DESIGN-MANIFEST-REQUIRED
  - ASSET-DESIGN-LICENSE-DOCUMENTED
  - ASSET-DESIGN-PROVENANCE-DOCUMENTED

Schema source of truth: docs/process/asset-design.md §5.

Companion to scripts/check-art-sync.py (Layer A sync). This script focuses on
the shape of each manifest in isolation; check-art-sync focuses on cross-file
consistency (hashes, layout references, Unity-side files).

Exit codes:
  0 - all manifests clean
  1 - one or more violations
  2 - infrastructure error (missing pyyaml, etc.)

Usage:
  python3 scripts/check-manifest-schema.py
  python3 scripts/check-manifest-schema.py --asset ART-CORRIDOR-PANEL-01
  python3 scripts/check-manifest-schema.py --quiet
  python3 scripts/check-manifest-schema.py --json
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
        "check-manifest-schema: pyyaml not installed. Run: pip install pyyaml\n"
    )
    sys.exit(2)

REPO_ROOT = Path(__file__).resolve().parent.parent
# Source-side staging — every art asset lives at art/<asset-kebab>/ with a
# sidecar manifest.yaml. See AGENTS.md §File conventions.
ART_SRC = REPO_ROOT / "art"
REGISTRY = REPO_ROOT / "docs" / "registry" / "architecture.yaml"

ART_ID_RE = re.compile(r"^ART-[A-Z0-9-]+$")
KEBAB_RE = re.compile(r"^[a-z][a-z0-9-]+$")

ALLOWED_SOURCES = {"polyhaven", "execute_blender_code", "hand_authored_user"}
RECOGNISED_LICENSES = {"CC0", "CC-BY-4.0", "hand_authored"}
LICENSE_PREFIX_OK = ("custom-",)
PLACEHOLDER_LICENSES = {"", "TODO", "unknown", "todo", "TBD", "tbd", "?"}

MANDATORY_FIELDS = [
    "id", "name", "purpose", "source", "license",
    "provenance", "exports", "screenshots", "approved",
]


def load_registry_ids() -> set[str] | None:
    if not REGISTRY.exists():
        return None
    try:
        with REGISTRY.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except Exception:
        return None
    art_assets = data.get("art_assets") or []
    ids: set[str] = set()
    for entry in art_assets:
        if isinstance(entry, dict) and entry.get("id"):
            ids.add(entry["id"])
    return ids


def load_manifest(path: Path) -> dict | None:
    try:
        with path.open("r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return None


def check_license(license_value) -> str | None:
    """Returns an error message, or None if the license is OK."""
    if license_value is None:
        return "license is null."
    if not isinstance(license_value, str):
        return f"license must be a string, got {type(license_value).__name__}."
    if license_value.strip() in PLACEHOLDER_LICENSES:
        return f"license is a placeholder ({license_value!r}). Set a concrete value."
    if license_value in RECOGNISED_LICENSES:
        return None
    if any(license_value.startswith(p) for p in LICENSE_PREFIX_OK):
        return None
    # Unknown license is allowed only if notes documents it; we cannot read
    # notes intent mechanically, so we flag it as advisory rather than fail
    # outright. The reviewer eyeballs the justification.
    return (
        f"license {license_value!r} is not in the recognised legend "
        f"({sorted(RECOGNISED_LICENSES)} or custom-*). "
        "Document the justification in manifest.notes and the reviewer can clear this."
    )


def check_provenance(source: str, provenance, asset_dir: Path) -> list[str]:
    errors: list[str] = []
    if not isinstance(provenance, dict):
        errors.append("provenance must be a mapping.")
        return errors
    if source == "polyhaven":
        if not provenance.get("polyhaven_id"):
            errors.append("provenance.polyhaven_id required when source=polyhaven.")
    elif source == "execute_blender_code":
        rp = provenance.get("recipe_path")
        if not rp:
            errors.append("provenance.recipe_path required when source=execute_blender_code.")
        else:
            recipe_path = REPO_ROOT / rp
            if not recipe_path.exists():
                errors.append(
                    f"provenance.recipe_path points at {rp!r} which does not exist on disk."
                )
    elif source == "hand_authored_user":
        if not provenance.get("hand_authored_by"):
            errors.append("provenance.hand_authored_by required when source=hand_authored_user.")
    return errors


def check_manifest(manifest_path: Path, registry_ids: set[str] | None) -> list[dict]:
    violations: list[dict] = []
    asset_dir = manifest_path.parent
    asset_dir_name = asset_dir.name
    rel_manifest = str(manifest_path.relative_to(REPO_ROOT))

    def fail(rule: str, detail: str) -> None:
        violations.append({
            "rule": rule,
            "file": rel_manifest,
            "asset": data.get("id") if isinstance(data, dict) else None,
            "detail": detail,
        })

    data = load_manifest(manifest_path)
    if data is None:
        violations.append({
            "rule": "ASSET-DESIGN-MANIFEST-REQUIRED",
            "file": rel_manifest,
            "asset": None,
            "detail": "manifest.yaml is unreadable or malformed YAML.",
        })
        return violations

    for field in MANDATORY_FIELDS:
        if field not in data or data[field] in (None, ""):
            fail("ASSET-DESIGN-MANIFEST-REQUIRED",
                 f"mandatory field {field!r} missing or empty.")

    asset_id = data.get("id")
    if asset_id is not None:
        if not isinstance(asset_id, str) or not ART_ID_RE.match(asset_id):
            fail("ASSET-DESIGN-MANIFEST-REQUIRED",
                 f"id {asset_id!r} must match {ART_ID_RE.pattern}.")
        elif registry_ids is not None and asset_id not in registry_ids:
            fail("ASSET-DESIGN-MANIFEST-REQUIRED",
                 f"id {asset_id!r} is not registered under art_assets: in "
                 f"docs/registry/architecture.yaml. Add it before committing.")

    name = data.get("name")
    if name is not None:
        if not isinstance(name, str) or not KEBAB_RE.match(name):
            fail("ASSET-DESIGN-MANIFEST-REQUIRED",
                 f"name {name!r} must match {KEBAB_RE.pattern}.")
        elif name != asset_dir_name:
            fail("ASSET-DESIGN-MANIFEST-REQUIRED",
                 f"name {name!r} disagrees with folder name {asset_dir_name!r}.")

    source = data.get("source")
    if source is not None and source not in ALLOWED_SOURCES:
        fail("ASSET-DESIGN-PROVENANCE-DOCUMENTED",
             f"source {source!r} is not allowed by ADR-0008. Allowed: {sorted(ALLOWED_SOURCES)}.")

    license_err = check_license(data.get("license"))
    if license_err:
        fail("ASSET-DESIGN-LICENSE-DOCUMENTED", license_err)

    if source in ALLOWED_SOURCES:
        for err in check_provenance(source, data.get("provenance"), asset_dir):
            fail("ASSET-DESIGN-PROVENANCE-DOCUMENTED", err)

    exports = data.get("exports")
    if isinstance(exports, list) and exports:
        first = exports[0]
        if not isinstance(first, dict) or not first.get("path") or not first.get("format"):
            fail("ASSET-DESIGN-MANIFEST-REQUIRED",
                 "exports[0] must have non-empty 'format' and 'path' fields.")
    elif "exports" in data:
        fail("ASSET-DESIGN-MANIFEST-REQUIRED",
             "exports must be a non-empty list.")

    screenshots = data.get("screenshots")
    if isinstance(screenshots, list):
        if not screenshots:
            fail("ASSET-DESIGN-MANIFEST-REQUIRED",
                 "screenshots must be a non-empty list (at least one preview).")
    elif "screenshots" in data:
        fail("ASSET-DESIGN-MANIFEST-REQUIRED",
             "screenshots must be a list of paths.")

    approved = data.get("approved")
    if approved not in (True, False, "pending"):
        fail("ASSET-DESIGN-MANIFEST-REQUIRED",
             f"approved must be one of pending|true|false, got {approved!r}.")

    target = data.get("target_unity_path")
    if target is not None:
        if not isinstance(target, str) or not target.startswith("src/Assets/_Project/Art/") or not target.endswith(".glb"):
            fail("ASSET-DESIGN-MANIFEST-REQUIRED",
                 f"target_unity_path {target!r} must start with 'src/Assets/_Project/Art/' and end with '.glb'.")

    if approved is True:
        if not data.get("approved_at"):
            fail("ASSET-DESIGN-MANIFEST-REQUIRED",
                 "approved=true requires approved_at to be set.")
        if not data.get("approved_by"):
            fail("ASSET-DESIGN-MANIFEST-REQUIRED",
                 "approved=true requires approved_by to be set.")
        if not data.get("imported_hash"):
            fail("ASSET-DESIGN-MANIFEST-REQUIRED",
                 "approved=true requires imported_hash to be set (sha256 of the .glb).")

    if data.get("imported_at") is not None:
        if not data.get("imported_hash"):
            fail("ASSET-DESIGN-MANIFEST-REQUIRED",
                 "imported_at is set but imported_hash is missing. Re-import to fix.")
        if not data.get("target_unity_guid"):
            fail("ASSET-DESIGN-MANIFEST-REQUIRED",
                 "imported_at is set but target_unity_guid is missing.")

    return violations


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--asset", help="focus on a single ART-* id")
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if not ART_SRC.exists():
        if args.json:
            print(json.dumps({"status": "ok", "violations": [], "summary": "no art/ yet"}))
        elif not args.quiet:
            print("manifest schema: no art/ directory (nothing to check)")
        return 0

    registry_ids = load_registry_ids()
    if registry_ids is None and not args.quiet and not args.json:
        sys.stderr.write(
            "manifest schema: warning — could not load architecture.yaml, "
            "skipping registry cross-check.\n"
        )

    all_violations: list[dict] = []

    # Mechanical ASSET-DESIGN-MANIFEST-REQUIRED check: every immediate child
    # directory under art/ must carry a manifest.yaml. Folders without one are
    # invisible to the glob below, so we scan the parent directly first.
    for child in sorted(ART_SRC.iterdir()):
        if not child.is_dir():
            continue
        if child.name.startswith("."):
            continue
        manifest_candidate = child / "manifest.yaml"
        if not manifest_candidate.exists():
            all_violations.append({
                "rule": "ASSET-DESIGN-MANIFEST-REQUIRED",
                "file": str(child.relative_to(REPO_ROOT)),
                "asset": None,
                "detail": (
                    f"folder {child.relative_to(REPO_ROOT)} has no manifest.yaml. "
                    "Every art/<asset-kebab>/ must include a manifest. Run "
                    "/scaffold-asset to create one, or delete the folder."
                ),
            })

    for mp in sorted(ART_SRC.glob("*/manifest.yaml")):
        violations = check_manifest(mp, registry_ids)
        for v in violations:
            if args.asset and v.get("asset") and v["asset"] != args.asset:
                continue
            all_violations.append(v)

    if args.json:
        print(json.dumps({
            "status": "ok" if not all_violations else "issues_found",
            "violations": all_violations,
            "summary": (
                "all manifests clean"
                if not all_violations
                else f"{len(all_violations)} violation(s)"
            ),
        }, indent=2))
        return 0 if not all_violations else 1

    if not all_violations:
        if not args.quiet:
            print("manifest schema: all green")
        return 0

    print(f"manifest schema: {len(all_violations)} violation(s)")
    for v in all_violations:
        asset = v["asset"] or "-"
        print(f"  [{v['rule']}] {asset} ({v['file']}): {v['detail']}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
