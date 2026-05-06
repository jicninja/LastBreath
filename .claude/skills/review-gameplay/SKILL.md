---
name: review-gameplay
user-invocable: true
description: Run the code-reviewer subagent in advisory mode against the current diff. Use to audit a change against rules, registry, active plan, and Unity patterns. Pass --strict to escalate to strict mode (used pre-merge).
---

# review-gameplay skill

## Purpose

User-facing entry point for the same review the gameplay-programmer agent dispatches automatically at the end of every gameplay change. One canonical review prompt, two entry points (this skill + auto-dispatch from the role).

## Args

- `--plan NNN` (optional) — scope the plan-adherence check to a specific plan. Default: auto (reviewer picks the active plan whose scope matches the diff).
- `--strict` (optional) — escalate to strict mode. Use before merging.
- `--range <git_range>` (optional) — review a specific git range. Default: working tree vs HEAD.

## Behaviour

1. Resolve `mode`: `advisory` by default; `strict` if `--strict` is passed.
2. Resolve `plan`: from `--plan`, or `auto`.
3. Dispatch the `code-reviewer` subagent with `mode`, `plan`, and `diff_range`.
4. Print the structured output.
5. Never edit any file.

## See also

- `.claude/agents/code-reviewer.md` — the agent this skill dispatches.
- `docs/process/unity-patterns.md` — one of the rule sources the reviewer consults.
