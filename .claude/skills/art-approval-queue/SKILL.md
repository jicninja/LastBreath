---
name: art-approval-queue
user-invocable: true
description: List pending art approvals from art/, show manifest + screenshots, and let the user approve | reject | request-iteration per asset. Writes the decision back into the manifest. The only path that sets approved: true.
---

# art-approval-queue skill

## Purpose

User-facing triage queue for assets sitting in `art/` with `approved: pending`. This is the **only** skill or tool that writes `approved: true` into a manifest. The forcing function for the human-in-the-loop gate.

The SessionStart hook (`scripts/art-staging-queue.py`) surfaces the pending count at every session start; the user runs this skill to act on it.

## Args

- `asset_id` (optional) — focus on a single `ART-*` ID. Default: triage everything pending.
- `screenshots` (optional, default `true`) — when `true`, the skill prints the screenshot paths so the user can open them. When `false`, only the manifest fields are printed.

## Behaviour

1. Scan `art/*/manifest.yaml`. Build the queue:
    - Pending: `approved == pending`.
    - Already-approved-not-imported: `approved == true && imported_at == null` (informational — the level-designer must run the MenuItem).
    - Rejected: `approved == false`.
2. If `asset_id` is supplied, filter to that asset.
3. For each pending entry, print to the user:
    - `id`, `name`, `purpose`.
    - `source`, `license`, `provenance`.
    - `screenshots[*]` — full paths so the user can open them.
    - `target_unity_path`.
    - `importer_settings` (compact).
    - `notes`.
4. Ask the user for a decision per asset:
    - `approve` — set `approved: true`, `approved_at: <ISO now>`, `approved_by: <user>`, `imported_hash: sha256(<glb>)`. The hash is computed from the file on disk at this moment; if the file is missing, abort with an error.
    - `reject` — set `approved: false`. Leave the bundle in staging marked rejected; the asset-designer either deletes it or supersedes it with a new `ART-*`.
    - `iterate` — leave `approved: pending`, append a note from the user into `manifest.notes` so the asset-designer reads it next session.
    - `skip` — leave untouched (the user does not want to decide now).
5. Save manifest updates atomically (read-modify-write per file; the skill does not run if the user is mid-edit).
6. Print a final summary: counts of approve / reject / iterate / skip.
7. For each approved asset, print the next step: "Asset ready to import. Open Unity and run `LastBreath > Art > Import Approved Assets` (Wave B), or commit the manifest update and import later."

## Failure modes

- Missing `<glb>` for an asset being approved: surface and stop. The user re-runs `asset-design-session` to rebuild.
- Concurrent manifest edit (the file changed between read and write): surface, do not clobber.
- No pending assets: print "Queue is empty." and exit. Optionally print the already-approved-not-imported list as a courtesy.

## Constraints

- The **only** skill that writes `approved: true`. No other code path sets that field non-interactively.
- Never modifies the `.glb`, the screenshots, or any field other than the decision quartet (`approved`, `approved_at`, `approved_by`, `imported_hash`, `notes` on iterate).
- Never copies files into `src/Assets/_Project/Art/`. That is the MenuItem's job (Wave B).
- Never commits — the user reviews the manifest diff and commits.

## See also

- `docs/decisions/0008-asset-pipeline.md` `§Decision` (Approval gate).
- `docs/process/asset-design.md` `§6`.
- `scripts/art-staging-queue.py` — the SessionStart hook that surfaces pending counts.
- `.claude/skills/asset-design-session/` — sibling skill the asset-designer runs before this one.
- `.claude/skills/verify-art-sync/` — sibling skill that detects drift after import.
