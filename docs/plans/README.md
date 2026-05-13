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

> **Execution of these plans is tracked separately in ExecPlans under `docs/exec-plans/`** — see `docs/process/exec-plans.md` and ADR-0012. Plans here are the contract layer (intent, scope, acceptance); ExecPlans are the execution layer (what actually happened). When a plan's implementation begins, the executing role spawns an `EXEC-NNN-<title>.md` that declares `derives_from: PLAN-NNN`.

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

> **Execution order (priority, not numeric):** PLAN-013 (harness methodology, lands first because it binds every subsequent plan) → PLAN-008 → PLAN-009 → PLAN-010 (validation gate) → PLAN-011 (second validation gate, art) → PLAN-012 and any future gameplay/save/dialogue plans. PLAN-014, PLAN-015, and PLAN-016-spike are queued as follow-up harness investments and run alongside or after the bootstrap chain (see ADR-0011 §Consequences). Numbers preserve identity, not order. Slot `007` is reserved as a numbering gap (first attempt at the player/camera plan landed there, was renumbered to `012` once the bootstrap chain was sequenced ahead of it).

| # | Title | Status | Done |
|---|---|---|---|
| [016-spike](016-spike-runtime-probe.md) | Unity runtime-probe feasibility spike (B) | proposed | — |
| [015](015-promote-feedback-skill.md) | Implement /promote-feedback skill (D) | proposed | — |
| [014](014-enforced-review-loop.md) | Implement enforced review loop — Stop hook + router (A) | proposed | — |
| [013](013-harness-methodology.md) | Adopt harness-engineering methodology before first gameplay code lands | done | 2026-05-12 |
| [012](012-player-controls-and-camera.md) | Player controls, billboard, and side-rig camera with DOF | proposed | — |
| [011](011-asset-pipeline-wave-b.md) | Asset pipeline Wave B — Unity import gate + first dogfood asset | proposed | — |
| [010](010-validate-level-design-loop.md) | Validate level-design loop — SCENE-CORREDOR-C7 with primitives | proposed | — |
| [009](009-levelspec-and-unity-mcp.md) | LevelSpec utility (DumpSpec/ApplySpec/ValidateScene) + unity-mcp wiring | proposed | — |
| [008](008-unity-bootstrap.md) | Unity project bootstrap — minimum playable shell | proposed | — |
| [006](006-asset-pipeline-blender.md) | Asset pipeline — Blender → staging → human approval → Unity (Wave A) | done | 2026-05-12 |
| [005](005-ship-ai-dialogue.md) | Ship AI dialogue mechanic — documentation only | done | 2026-05-12 |
| [004](004-progression-and-save.md) | Progression and Save documentation | done | 2026-05-12 |
| [003](003-document-and-prompt-scaffolding.md) | Document and Prompt Scaffolding | done | 2026-05-05 |
| [002](002-restructure-docs-and-add-reviewer.md) | Restructure Docs and Add Reviewer | done | 2026-05-05 |
| [001](001-pilot-split-oxygen.md) | Pilot — split the Oxygen system | done | 2026-05-12 |

## Specs (proposed, awaiting an implementation plan)

Specs live in `docs/specs/` and document a coherent block of decisions before any implementation plan picks them up. They appear here so the audit reaches them through the plans index.

- [docs/specs/2026-05-12-ship-ai-context-and-runtime-design.md](../specs/2026-05-12-ship-ai-context-and-runtime-design.md) — `SPEC-2026-05-12-ship-ai-context-and-runtime` (status: `proposed`). Extends PLAN-005 / ADR-0006 with concrete decisions for the ship-AI context shape, prompt template, chat UI substrate, and availability gating. Implementation requires its own plan.
