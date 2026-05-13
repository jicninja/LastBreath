#!/usr/bin/env python3
"""Append an art_assets: entry to docs/registry/architecture.yaml idempotently.

Called by the /scaffold-asset skill so the registry block lands automatically
instead of being copy-pasted by hand. Closes gap G3 in the methodology audit.

Behaviour:
  - If the id already appears under art_assets:, exit 0 with a "skipped" notice.
  - If art_assets: exists as an empty list ([]), replace it with a single-entry list.
  - If art_assets: already has entries, append the new entry at the end.
  - If art_assets: is missing or in a shape we don't recognise, exit 1 and ask
    the user to add the block manually (do NOT silently mangle the registry).

The script edits the YAML *textually* (not via yaml.dump round-trip) so that
comments and section ordering in architecture.yaml stay intact. yaml.safe_load
is used only for the dry-run validation that the file parses after the edit.

Exit codes:
  0 - entry added or already present
  1 - registry shape unrecognised, manual paste required
  2 - infrastructure error (missing pyyaml, file not found, etc.)

Usage:
  python3 scripts/add-art-asset-to-registry.py \
      --id ART-CORRIDOR-PANEL-01 \
      --name corridor-panel-01 \
      --source hand_authored_user \
      --license hand_authored \
      --manifest art/corridor-panel-01/manifest.yaml
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.stderr.write(
        "add-art-asset-to-registry: pyyaml not installed. Run: pip install pyyaml\n"
    )
    sys.exit(2)

REPO_ROOT = Path(__file__).resolve().parent.parent
REGISTRY = REPO_ROOT / "docs" / "registry" / "architecture.yaml"

EMPTY_LINE_RE = re.compile(r"^art_assets:\s*\[\s*\]\s*$")
HEADER_LINE_RE = re.compile(r"^art_assets:\s*$")
ENTRY_LINE_RE = re.compile(r"^\s*-\s*id:\s*(\S+)")


def find_id_in_registry(text: str, asset_id: str) -> bool:
    in_art_assets = False
    for line in text.splitlines():
        if line.startswith("art_assets:"):
            in_art_assets = True
            continue
        if in_art_assets:
            if line and not line.startswith(" ") and not line.startswith("-") and not line.startswith("#"):
                in_art_assets = False
                continue
            m = ENTRY_LINE_RE.match(line)
            if m and m.group(1) == asset_id:
                return True
    return False


def build_entry_block(asset_id: str, name: str, source: str, license_value: str, manifest_path: str) -> str:
    return (
        f"  - id: {asset_id}\n"
        f"    name: {name}\n"
        f"    source: {source}\n"
        f"    license: {license_value}\n"
        f"    manifest: {manifest_path}\n"
        f"    status: active\n"
    )


def insert_entry(text: str, entry_block: str) -> tuple[str, str]:
    """Return (new_text, mode). mode is 'replaced_empty' | 'appended' | 'unrecognised'."""
    lines = text.splitlines(keepends=True)
    for i, line in enumerate(lines):
        if EMPTY_LINE_RE.match(line.rstrip("\n")):
            lines[i] = "art_assets:\n"
            lines.insert(i + 1, entry_block)
            return ("".join(lines), "replaced_empty")
        if HEADER_LINE_RE.match(line.rstrip("\n")):
            insert_at = i + 1
            while insert_at < len(lines):
                ln = lines[insert_at]
                stripped = ln.rstrip("\n")
                if not stripped:
                    insert_at += 1
                    continue
                if stripped.startswith(" ") or stripped.startswith("-") or stripped.startswith("#"):
                    insert_at += 1
                    continue
                break
            lines.insert(insert_at, entry_block)
            return ("".join(lines), "appended")
    return (text, "unrecognised")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--id", required=True, dest="asset_id")
    ap.add_argument("--name", required=True)
    ap.add_argument("--source", required=True)
    ap.add_argument("--license", required=True, dest="license_value")
    ap.add_argument("--manifest", required=True, help="repo-relative path to the manifest.yaml")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not REGISTRY.exists():
        sys.stderr.write(f"registry not found: {REGISTRY}\n")
        return 2

    text = REGISTRY.read_text(encoding="utf-8")

    if find_id_in_registry(text, args.asset_id):
        print(f"add-art-asset-to-registry: {args.asset_id} already present, no change.")
        return 0

    entry_block = build_entry_block(
        args.asset_id, args.name, args.source, args.license_value, args.manifest
    )
    new_text, mode = insert_entry(text, entry_block)

    if mode == "unrecognised":
        sys.stderr.write(
            "add-art-asset-to-registry: art_assets: section not found in a recognised shape.\n"
            "Paste this block manually under art_assets: in docs/registry/architecture.yaml:\n\n"
        )
        sys.stderr.write(entry_block + "\n")
        return 1

    try:
        yaml.safe_load(new_text)
    except yaml.YAMLError as e:
        sys.stderr.write(
            f"add-art-asset-to-registry: edit would break YAML parsing: {e}\n"
            "No changes written.\n"
        )
        return 1

    if args.dry_run:
        print(f"add-art-asset-to-registry: would {mode} entry for {args.asset_id} (dry-run).")
        return 0

    REGISTRY.write_text(new_text, encoding="utf-8")
    print(f"add-art-asset-to-registry: {mode} entry for {args.asset_id} in {REGISTRY.relative_to(REPO_ROOT)}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
