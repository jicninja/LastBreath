---
name: review-asset
user-invocable: true
description: Run the code-reviewer subagent against an asset-design diff. Loads .claude/rules/asset-design.md and audits art/**, art_assets: entries, manifest schema, provenance, and sync parity. Pass --strict to escalate (used pre-merge).
---

# review-asset skill

## Purpose

User-facing entry point for the asset-design diff review. Mirrors `review-gameplay` and `review-level` but scopes the reviewer to `.claude/rules/asset-design.md`.

## Args

- `--plan NNN` (optional) — scope the plan-adherence check to a specific plan. Default: auto.
- `--strict` (optional) — escalate to strict mode. Pre-merge default. In strict mode, the reviewer runs `python3 scripts/check-art-sync.py` and fails the review if the verifier exits non-zero.
- `--range <git_range>` (optional) — review a specific git range. Default: working tree vs HEAD.

## Behaviour

1. Resolve `mode`: `advisory` by default; `strict` if `--strict`.
2. Resolve `plan`: from `--plan`, or `auto`.
3. Resolve `scope`: `asset-design`. The reviewer loads `.claude/rules/asset-design.md` as the primary rule source.
4. Dispatch the `code-reviewer` subagent with `mode`, `plan`, `diff_range`, and `scope: asset-design`.
5. The reviewer reads:
    - Every touched `art/<asset>/manifest.yaml`.
    - The corresponding `art_assets:` entries in `architecture.yaml`.
    - The screenshot filenames (existence check; visual review stays with the human).
    - The `.glb` filename only — the reviewer does not parse the binary.
    - If the diff also touches `src/Assets/_Project/Art/`, the reviewer verifies the matching manifest has `approved: true` and `imported_at != null`.
6. In strict mode additionally:
    - Run `python3 scripts/check-art-sync.py` (Layer A).
    - If exit code != 0, attach the violations as `ASSET-DESIGN-SYNC-PARITY` failures.
7. Print the structured `status / violations / registry_drift / plan_adherence / non_blocking_notes` block.
8. Never edit any file.

## See also

- `.claude/agents/code-reviewer.md` — the agent this skill dispatches.
- `.claude/rules/asset-design.md` — the primary rule source for this scope.
- `docs/process/asset-design.md` — the canonical loop the reviewer audits adherence to.
- `scripts/check-art-sync.py` — the verifier strict mode invokes.
- `.claude/skills/review-gameplay/`, `.claude/skills/review-level/` — sibling skills.
