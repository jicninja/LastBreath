---
name: review-level
user-invocable: true
description: Run the code-reviewer subagent against a level-design diff. Loads .claude/rules/level-design.md and audits docs/levels/**, .unity composition, level prefabs, and level configs. Pass --strict to escalate (used pre-merge) and to run the idempotency rebuild against a scratch scene.
---

# review-level skill

## Purpose

User-facing entry point for the same review the `level-designer` dispatches automatically at the end of every session. Mirrors `review-gameplay` but scopes the reviewer to `.claude/rules/level-design.md` and the level-design surface.

## Args

- `--plan NNN` (optional) — scope the plan-adherence check to a specific plan. Default: auto.
- `--strict` (optional) — escalate to strict mode. Pre-merge default. In strict mode, the reviewer runs `LevelSpec.ApplySpec` on a scratch copy of every touched `.unity` and diffs against the committed scene to enforce `LEVEL-DESIGN-SPEC-IS-IDEMPOTENT`.
- `--range <git_range>` (optional) — review a specific git range. Default: working tree vs HEAD.

## Behaviour

1. Resolve `mode`: `advisory` by default; `strict` if `--strict`.
2. Resolve `plan`: from `--plan`, or `auto`.
3. Resolve `scope`: `level-design`. The reviewer loads `.claude/rules/level-design.md` as the primary rule source. `gameplay-code` rules still apply if the diff accidentally touches `src/Assets/_Project/Scripts/**` (which would already trip `LEVEL-DESIGN-NO-GAMEPLAY-CODE`).
4. Dispatch the `code-reviewer` subagent with `mode`, `plan`, `diff_range`, and `scope: level-design`.
5. The reviewer reads:
   - The touched `docs/levels/<scene>/<scene>.layout.yaml` spec(s).
   - The touched `docs/levels/<scene>/sessions/session-NNNN.md` log(s).
   - The committed screenshot filenames (visual review stays with the human; the reviewer only confirms the two expected files were committed with the matching session id).
   - The `.unity` filename(s) — but not the YAML contents; the reviewer does not parse Unity's serialised format.
6. In strict mode additionally:
   - Open each touched `.unity` in a scratch copy.
   - Run `LevelSpec.ApplySpec(yaml, scratchScene)`.
   - Diff scratchScene vs the committed scene. If they differ on load-bearing fields, fail with `LEVEL-DESIGN-SPEC-IS-IDEMPOTENT`.
7. Print the structured `status / violations / registry_drift / plan_adherence / non_blocking_notes` block.
8. Never edit any file.

## See also

- `.claude/agents/code-reviewer.md` — the agent this skill dispatches.
- `.claude/rules/level-design.md` — the primary rule source for this scope.
- `docs/process/level-design.md` — the canonical loop the reviewer audits adherence to.
- `.claude/skills/review-gameplay/` — sibling skill, same dispatch pattern.
