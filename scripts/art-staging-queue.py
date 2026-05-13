#!/usr/bin/env python3
"""Scan art/ for pending approvals and surface them.

Wired as a SessionStart hook in .claude/settings.json. On every fresh session,
the hook runs this script; if any manifest has approved: pending, the script
prints a one-line system reminder asking the user to run /art-approval-queue.

Exit code is always 0 — this is a UX nudge, not a validator. The agentic
forcing is the reminder itself, not a failure mode.

Schema details: docs/process/asset-design.md §5.
Rationale: ADR-0008, especially the "agentic forcing" / approval-gate rationale.

Usage:
  python3 scripts/art-staging-queue.py             # human-readable
  python3 scripts/art-staging-queue.py --json      # JSON for hook consumption
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.stderr.write(
        "art-staging-queue: pyyaml not installed. Run: pip install pyyaml\n"
    )
    sys.exit(0)  # do not block the session start

REPO_ROOT = Path(__file__).resolve().parent.parent
# Source-side staging — every asset lives at art/<asset-kebab>/ with a
# sidecar manifest.yaml. See AGENTS.md §File conventions.
ART_SRC = REPO_ROOT / "art"


def scan_manifests() -> list[dict]:
    results = []
    if not ART_SRC.exists():
        return results
    for manifest_path in ART_SRC.glob("*/manifest.yaml"):
        try:
            with manifest_path.open("r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        except Exception as e:
            results.append({
                "path": str(manifest_path.relative_to(REPO_ROOT)),
                "id": None,
                "name": None,
                "approved": None,
                "imported_at": None,
                "error": f"unreadable: {e}",
            })
            continue
        results.append({
            "path": str(manifest_path.relative_to(REPO_ROOT)),
            "id": data.get("id"),
            "name": data.get("name"),
            "approved": data.get("approved"),
            "imported_at": data.get("imported_at"),
            "purpose": data.get("purpose"),
            "error": None,
        })
    return results


def categorise(manifests: list[dict]) -> dict[str, list[dict]]:
    pending = []
    approved_not_imported = []
    rejected = []
    malformed = []
    for m in manifests:
        if m["error"]:
            malformed.append(m)
            continue
        if m["approved"] == "pending":
            pending.append(m)
        elif m["approved"] is True and m["imported_at"] is None:
            approved_not_imported.append(m)
        elif m["approved"] is False:
            rejected.append(m)
    return {
        "pending": pending,
        "approved_not_imported": approved_not_imported,
        "rejected": rejected,
        "malformed": malformed,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true", help="emit JSON instead of prose")
    args = ap.parse_args()

    manifests = scan_manifests()
    cats = categorise(manifests)
    pending = cats["pending"]
    ani = cats["approved_not_imported"]
    malformed = cats["malformed"]

    if args.json:
        print(json.dumps({
            "pending_count": len(pending),
            "approved_not_imported_count": len(ani),
            "rejected_count": len(cats["rejected"]),
            "malformed_count": len(malformed),
            "pending": [{"id": m["id"], "name": m["name"], "purpose": m["purpose"]} for m in pending],
            "approved_not_imported": [{"id": m["id"], "name": m["name"]} for m in ani],
        }, indent=2))
        return 0

    if not pending and not ani and not malformed:
        # Silent on a clean queue — no need to spam every session.
        return 0

    lines = []
    if pending:
        lines.append(f"PENDING ART APPROVALS: {len(pending)} asset(s) in art/ awaiting human review.")
        for m in pending:
            lines.append(f"  - {m['id']} ({m['name']}): {m['purpose'] or '(no purpose)'}")
        lines.append("Run /art-approval-queue to triage (approve | reject | request-iteration).")
    if ani:
        lines.append(f"APPROVED-NOT-IMPORTED: {len(ani)} asset(s) waiting for the Unity importer (Wave B MenuItem).")
        for m in ani:
            lines.append(f"  - {m['id']} ({m['name']})")
        lines.append("Open Unity and run LastBreath > Art > Import Approved Assets when ready.")
    if malformed:
        lines.append(f"MALFORMED MANIFEST(S): {len(malformed)} file(s) could not be parsed.")
        for m in malformed:
            lines.append(f"  - {m['path']}: {m['error']}")

    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
