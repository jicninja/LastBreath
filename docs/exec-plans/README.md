# docs/exec-plans/

ExecPlans — self-contained execution documents a coding agent reads to deliver a working feature or system change end-to-end. Numbered `EXEC-NNN-<kebab-title>.md`. The namespace is **independent** of `PLAN-NNN`.

Decision: `docs/decisions/0012-adopt-exec-plan-methodology.md`. Canonical loop: `docs/process/exec-plans.md`. Binding rules: `.claude/rules/exec-plans.md`.

## When to open an ExecPlan

When the implementation of a Plan begins, when a multi-session change starts where conversation context would break at the hour mark, or when a free-standing exceptional execution (incident response, multi-file refactor) is starting. Full guidance in `docs/process/exec-plans.md` §2.

Do not use an ExecPlan for documentation-only work, single-file edits, sandbox spikes, or pure design conversation — those stay in `docs/plans/`, in ADRs, or in `_Sandbox/`.

## Relationship to `docs/plans/`

Plans (`docs/plans/`) are the **contract** layer — they fix intent, scope, acceptance, ownership, dependencies. ExecPlans (`docs/exec-plans/`) are the **execution** layer — they record what actually happened. When an ExecPlan derives from a Plan, the frontmatter declares `derives_from: PLAN-NNN`. The two artifacts coexist as historical record: Plan = intent; ExecPlan = what happened.

The 15 existing plans in `docs/plans/` are **not** migrated to ExecPlan format. ADR-0012 explicitly preserves them; the ExecPlan model is additive, not a replacement.

## Lifecycle

ExecPlans share the plan lifecycle states (`proposed | active | paused | done | abandoned | superseded`) with extra constraints on what gets edited at each status. Full lifecycle and transition diagram in `docs/process/exec-plans.md` §4.

Headline difference from plans: while `active`, the four mutable sections (`Progress`, `Surprises & Discoveries`, `Decision Log`, `Outcomes & Retrospective`) are updated at every commit per `EXEC-PLAN-LIVING-DOCUMENT`. Plans' `active` edits are typically narrow; ExecPlans' `active` edits are continuous.

## Authoring

Copy the skeleton template from `docs/process/exec-plans.md` §8. Fill the placeholders. Keep all twelve mandatory headings, in order, verbatim. The five rule IDs that bind an ExecPlan are in `.claude/rules/exec-plans.md`:

- `EXEC-PLAN-SELF-CONTAINED`
- `EXEC-PLAN-LIVING-DOCUMENT`
- `EXEC-PLAN-OBSERVABLE-OUTCOME`
- `EXEC-PLAN-MANDATORY-SECTIONS`
- `EXEC-PLAN-FORMAT-DISCIPLINE`

The `code-reviewer` subagent reads the ExecPlan diff against these rules on every `/review-*` pass.

## Numbering

`EXEC-NNN`. Always increment from the highest existing `NNN`. Never reuse. Numbering is global within this folder and **not shared** with `PLAN-NNN`. The first ExecPlan, regardless of which plan it derives from, is `EXEC-001`.

## Index

Every ExecPlan is listed here, newest first. Add the entry the moment an ExecPlan file is created — `scripts/audit-md.py` flags missing entries as orphans.

| # | Title | Status | Derives from | Done |
|---|---|---|---|---|
| _none yet_ | _The first ExecPlan will be created when implementation begins. Current queue points to PLAN-008 as the first implementation candidate._ | — | — | — |
