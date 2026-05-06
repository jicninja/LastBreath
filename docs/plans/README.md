# docs/plans/

Plans before code. Numbered sequentially: `NNN-kebab-name.md`.

## When to open a plan

- Any change that touches more than one class or more than one doc layer.
- Any change that adds, renames, or removes a system, mechanic, or class.
- Any structural move (file renames, folder restructures).

## When NOT to open a plan

- Single-class trivial changes inside `_Sandbox/`.
- Single-file typo fixes in docs.
- Sandbox spikes that won't be promoted (per `.claude/rules/prototype-code.md`).

## Lifecycle

| Status | Meaning |
|---|---|
| `proposed` | Drafted, not approved. |
| `active` | Approved; in flight. Only one or two should be `active` at once. |
| `paused` | Started but stopped mid-execution; will be resumed later. Must include a "Paused at: \<date\>, last completed task: Task X" note and a one-paragraph handoff for whoever resumes. |
| `done` | Acceptance criteria all met; keep the file as historical record. |
| `abandoned` | Cancelled before completion. Append a "Reason for abandonment" section. |
| `superseded` | A later plan replaced this one. Add `superseded_by: PLAN-NNN` to the frontmatter and link the replacement at the top of the file. |

`done` is the normal terminal state. `superseded` and `abandoned` are explicit failure / replacement states; `deprecated` is **not** used on plans (it's reserved for ADRs and registry IDs).

## Transitions

```
proposed → active → done                 (happy path)
proposed → active → paused → active → done   (interrupted, resumed)
proposed → active → abandoned            (stopped without resuming)
done → superseded                        (later plan replaces this one)
proposed → abandoned                     (rejected before starting)
```

Edits to a `done` plan are forbidden except to mark it `superseded`. If the work needs amending, open a new plan that supersedes this one.

## Pause and resume

Pausing:

1. Commit work in a green state.
2. Set `status: paused` in the plan frontmatter.
3. Append a "Pause note" with date, last completed task, and a one-paragraph handoff.
4. Commit the plan update.

Resuming:

1. Set `status: active`.
2. Continue from the first unchecked step.
3. Dispatch `code-reviewer` after the next commit lands on this plan's scope.

Use kickoff prompts §10 (`docs/process/kickoff-prompts.md`) for the canonical pause/resume invocations.

## Numbering

- Always increment from the highest existing `NNN`. Never reuse numbers.
- Numbering is global across all plans regardless of status.

## Index

Every plan is listed here, newest first. Add the entry the moment a plan file is created — `scripts/audit-md.py` flags missing entries as orphans.

| # | Title | Status | Done |
|---|---|---|---|
| [003](003-document-and-prompt-scaffolding.md) | Document and Prompt Scaffolding | done | 2026-05-05 |
| [002](002-restructure-docs-and-add-reviewer.md) | Restructure Docs and Add Reviewer | done | 2026-05-05 |
| [001](001-pilot-split-oxygen.md) | Pilot — split the Oxygen system | poc | — |
