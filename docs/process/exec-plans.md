---
id: PROCESS-EXEC-PLANS
type: reference
layer: process
status: active
related: [ADR-0012, ADR-0011, ADR-0003]
---

# ExecPlans — the execution-document loop

Canonical workflow for writing and driving *ExecPlans*: self-contained markdown files that a coding agent reads to deliver a working feature or system change end-to-end. Read end-to-end the first time, then jump to the section you need.

Decision: `docs/decisions/0012-adopt-exec-plan-methodology.md`. Rules: `.claude/rules/exec-plans.md`. Source methodology: OpenAI Cookbook, "Codex Exec Plans" (2026). Design spec: `docs/specs/2026-05-13-adopt-exec-plan-methodology-design.md`. Mechanical-forcing linter is a follow-up plan (not yet numbered) per the staged-forcing pattern of ADR-0011.

## 1. Purpose

The repo has plans (`docs/plans/`) and ADRs (`docs/decisions/`) and a registry. Together they form the *contract* layer: what to build, why, what the acceptance is. What they do not form is an *execution* layer — a document a stateless coding agent can read top-to-bottom and execute end-to-end without keeping the rest of the repo in its conversation context.

ExecPlans fill that gap. They are not a replacement for plans; they are the artifact a plan spawns when its implementation begins. The contract layer fixes intent; the ExecPlan is what happened.

Three load-bearing properties (carried verbatim from the OpenAI Cookbook):

- *"Every ExecPlan must be fully self-contained."*
- *"Every ExecPlan is a living document."*
- *"Every ExecPlan must produce a demonstrably working behavior, not merely code changes."*

The five rules in `.claude/rules/exec-plans.md` codify these properties plus two structural rules (twelve mandatory sections; three grep-able format bans).

## 2. When to open an ExecPlan

Open one when:

- Implementation work on an existing Plan begins (typical case). The ExecPlan declares `derives_from: PLAN-NNN` and inlines the relevant excerpts from the plan, the cited ADR(s), the SDD section(s), the TDD section(s), and the registry entries.
- A multi-session change is starting where keeping context in conversation would break at the hour mark (incident response, multi-file refactor, asset pipeline run that spans several Blender sessions). The ExecPlan is the persistent execution record; the conversation is ephemeral.
- A diff is expected to span more than a handful of files, or more than a single session, and the work touches `src/Assets/_Project/Scripts/**`, `src/Assets/_Editor/**`, `src/Assets/Scenes/**.unity`, `src/Assets/_Project/Prefabs/**`, `art/**`, or `scripts/**`.

Do not open one when:

- The diff is a single-file edit (a typo fix, a one-line tuning change, a comment).
- The work is documentation-only (an ADR edit, a `docs/process/` clarification, a `docs/plans/` lifecycle update). Documentation work uses Plans, not ExecPlans.
- The work is a sandbox spike under `src/Assets/_Sandbox/**` that is explicitly not going to be promoted. `prototype-code.md` already covers the short-lived disposable pattern.

Free-standing ExecPlans (no originating Plan) are allowed for the exceptional cases above. They omit `derives_from:` and cite the trigger (issue link, incident report, user-request transcript) in `Context and Orientation`.

## 3. The twelve mandatory sections

Every ExecPlan, at every status, carries these twelve top-level headings in this exact order. The order is fixed by `EXEC-PLAN-MANDATORY-SECTIONS` and matches the OpenAI Cookbook skeleton verbatim:

1. **Purpose / Big Picture** — user-visible behaviour and what becomes possible after this ExecPlan lands. Two to four sentences. No bullet list.
2. **Progress** — checkbox list with `(YYYY-MM-DD HH:MMZ)` timestamps. The only section in which checklists are permitted; the only section in which tables are permitted. Updated *at every commit* per `EXEC-PLAN-LIVING-DOCUMENT`.
3. **Surprises & Discoveries** — unexpected behaviours, bugs, optimisations encountered during execution. Each entry references a transcript, a diff, or a screenshot. Empty (heading-only with a placeholder line) at `proposed`; filled progressively while `active`.
4. **Decision Log** — `Decision: … / Rationale: … / Date & Author: …` triples. Every non-obvious choice the agent made during execution lands here. Examples: choosing a Cinemachine damping value, picking a serialization format, deferring a refactor.
5. **Outcomes & Retrospective** — written at `done`. Empty (heading + placeholder `_To be written at done._`) at `proposed` and (usually) at `active`. Three things: what was achieved, what was deferred, what would be done differently.
6. **Context and Orientation** — the load-bearing section. Current state of the relevant slice of the repo, with full file paths, the inline definitions of every internal ID the ExecPlan will cite downstream, and definitions of every term of art. The self-containment guarantee (per `EXEC-PLAN-SELF-CONTAINED`) is enforced here: an agent reading only this section must understand the problem space.
7. **Plan of Work** — prose description of the edits and additions. Concrete and minimal. No tables. No checklists. The reader comes out knowing the shape of the change.
8. **Concrete Steps** — exact commands, working directories, expected transcripts. Where commands run in sequence, they go in flat fenced code blocks (no nested fences per `EXEC-PLAN-FORMAT-DISCIPLINE`).
9. **Validation and Acceptance** — written as *observable behaviour* (per `EXEC-PLAN-OBSERVABLE-OUTCOME`). What to exercise, what to observe, what the runtime-probe artifact path is (the artifact path is *not* an external link and is allowed by the carve-out in `EXEC-PLAN-SELF-CONTAINED`).
10. **Idempotence and Recovery** — what happens if the ExecPlan is restarted mid-flight; safe retry paths; cleanup steps for failed partial runs. This is the section that lets a fresh agent pick up a paused ExecPlan without breaking state.
11. **Artifacts and Notes** — embedded transcripts, diffs, screenshots; everything an agent might want to compare against during execution. Code spans live here.
12. **Interfaces and Dependencies** — prescriptive naming for new types, modules, functions, files; explicit declaration of every dependency (registry IDs, ADRs, packages, MCP servers) and where each is defined inline in `Context and Orientation`.

Subsections under each top-level heading are allowed and unconstrained. Adding a thirteenth top-level heading is forbidden — additional content goes as a subsection.

## 4. Lifecycle and the four living sections

ExecPlans use the same status names as plans (`proposed`, `active`, `paused`, `done`, `abandoned`, `superseded`) with additional constraints on what gets edited at each status. The full lifecycle:

- **`proposed`** — drafted, not started. All twelve sections present; `Progress` carries only the heading; `Outcomes & Retrospective` carries only the heading and the placeholder line. The frontmatter `derives_from:` is set if the ExecPlan derives from a Plan; otherwise absent.
- **`active`** — execution underway. The four mutable sections (`Progress`, `Surprises & Discoveries`, `Decision Log`, `Outcomes & Retrospective`) are updated at every commit per `EXEC-PLAN-LIVING-DOCUMENT`. The other eight sections (Purpose, Context and Orientation, Plan of Work, Concrete Steps, Validation and Acceptance, Idempotence and Recovery, Artifacts and Notes, Interfaces and Dependencies) may be edited to correct errors, but the audit trail is git history, not in-document strikethroughs.
- **`paused`** — `docs/plans/README.md` §Pause and resume applies verbatim: the frontmatter gains a `Paused at: <date>, last completed task: Task X` note and a one-paragraph handoff for whoever resumes. "Task X" references the last completed `Progress` checklist line by its `(timestamp)` prefix.
- **`done`** — work shipped, validation passed, retrospective written. The whole file becomes immutable except to add `superseded_by:` to the frontmatter when a later ExecPlan replaces it.
- **`abandoned`** — stopped without resuming. The `Outcomes & Retrospective` section is filled with the reason and what (if anything) survives in the working tree.
- **`superseded`** — a later ExecPlan replaces this one. The earlier ExecPlan gains `superseded_by: EXEC-NNN`; the later one declares `supersedes: EXEC-MMM`.

The transitions:

- `proposed → active → done` (happy path)
- `proposed → active → paused → active → done` (interrupted, resumed)
- `proposed → active → abandoned` (stopped without resuming)
- `done → superseded` (replaced by a later ExecPlan)
- `proposed → abandoned` (rejected before starting)

The contrast with plans is **not** "static vs living" — plans are also mutable while `active`. The contrast is what gets edited: a plan's `active` edits are typically narrow (checking off scope items, refining acceptance). An ExecPlan's `active` edits are continuous: the four living sections grow at every commit. `EXEC-PLAN-LIVING-DOCUMENT` makes this a binding obligation.

## 5. The self-containment carve-out — worked example

`EXEC-PLAN-SELF-CONTAINED` allows internal-repo IDs to be cited only if they are transcribed inline in `Context and Orientation` with enough detail for a fresh agent to act on them. "Enough detail" is the worked-example test below, not a one-line gloss.

Forbidden (one-line gloss):

> *"SYS-OXYGEN is the oxygen system."*

Forbidden (cites the registry without transcribing it):

> *"SYS-OXYGEN per `docs/registry/architecture.yaml::systems` — see also SDD §OxygenSystem."*

Allowed (transcribes responsibility, public surface, events, configs, file path; a fresh agent can act on it):

> *"`SYS-OXYGEN` is the runtime oxygen budget for the player. It owns one `float Current` on `[0, _config.MaxOxygen]` and one `bool IsDepleted`. It publishes `Action<float, float> OxygenChanged(current, max)` every time `Current` changes and `Action OxygenDepleted` exactly once when `Current` hits zero. It reads from `OxygenConfig` (a `ScriptableObject` at `src/Assets/_Project/Config/Oxygen/`) which carries `MaxOxygen`, `BaseDrainPerSecond`, and `RefillPerSecond`. The class lives at `src/Assets/_Project/Scripts/Oxygen/OxygenSystem.cs` and is registered on the scene's `GameLifetimeScope` per `GAMEPLAY-CODE-DI-LIFETIMESCOPE-ONLY-AT-ROOT`. It runs in `Update`, not `FixedUpdate`. It restores state via `RestoreState(OxygenDto)` which assigns `Current` directly without firing `OxygenChanged` (per `GAMEPLAY-CODE-SAVE-NO-EVENTS-DURING-LOADING`)."*

The Allowed form is roughly the registry entry's purpose plus the SDD's invariants plus the TDD's class signature, paraphrased into one paragraph. That is the bar.

External resources (Unity docs, Cinemachine 3 release notes, an OpenAI blog post) are **not** covered by this carve-out. If their content matters, paraphrase it into `Context and Orientation` in the agent's own words and cite the source as provenance, never as the load-bearing reference.

Artifact paths committed under the repo (runtime-probe screenshots at `docs/levels/<scene>/img/`, JSON reports at `src/Assets/_Editor/RuntimeReports/`, transcripts at `docs/plans/<plan>/runtime-probe.md`) are **not** external links and may be cited anywhere in the ExecPlan. They are the runtime-probe contract from `HARNESS-LOOP-RUNTIME-PROBE-BEFORE-COMPLETION`.

## 6. Format discipline — the three grep-able bans

`EXEC-PLAN-FORMAT-DISCIPLINE` carries three mechanical bans that make the ExecPlan a sequential narrative an agent reads top to bottom:

- **Checklists only in `Progress`.** Grep: `grep -n -- '- \[' docs/exec-plans/EXEC-NNN-*.md` — every match must be inside the `Progress` section.
- **Tables only in `Progress`.** Grep: `grep -nE '^\|' docs/exec-plans/EXEC-NNN-*.md` — every match must be inside the `Progress` section.
- **No nested code fences.** Each fenced block opens with three backticks and closes with three backticks at the same indentation. Fences inside fences break the parser and obscure the narrative.

Prose lists with `-` or `*` bullets in any section are not checklists and are allowed. Inline code spans (single backticks) are allowed anywhere.

## 7. Relationship to existing plans, skills, and reviewers

ExecPlans extend the repo's harness; they do not replace any existing rule. Specific relationships:

- **Plans (`docs/plans/`)** are the contract layer. An ExecPlan that derives from a Plan declares `derives_from: PLAN-NNN` in its frontmatter and inlines the plan's deliverable list and acceptance into `Context and Orientation`. When the ExecPlan reaches `done`, the originating Plan is also marked `done` if its scope was satisfied; if the ExecPlan delivered a different scope (deferred items, descope, scope creep), the Plan is marked `superseded` and a follow-up Plan captures the new scope.
- **ADRs (`docs/decisions/`)** are inline-cited in `Context and Orientation`. The ExecPlan paraphrases the relevant decision in its own words; the ADR is the provenance, not the load-bearing reference.
- **SDD / TDD (`docs/sdd/`, `docs/tdd/`)** are inline-cited in `Context and Orientation` (responsibilities, invariants, class signatures). Same paraphrase-then-cite pattern.
- **Registry (`docs/registry/architecture.yaml`)** stays the source of truth. The ExecPlan transcribes registry content for the IDs it cites; it does not duplicate the registry or compete with it.
- **`.claude/rules/`** still applies path-by-path. The ExecPlan is the *vehicle*; the rule files are still the *constraint*. `GAMEPLAY-CODE-NO-FINDOBJECTOFTYPE` does not stop applying inside an ExecPlan-driven session.
- **`code-reviewer` subagent** reads ExecPlan diffs the same way it reads code diffs. A new ExecPlan, an `active` ExecPlan being updated, and a `done` ExecPlan all surface in `/review-gameplay` (or the matching review skill) if the same commit touches the relevant code scope. The reviewer also checks the ExecPlan against the five rule IDs in `.claude/rules/exec-plans.md`.
- **Harness loop (`.claude/rules/harness-loop.md`)** applies in full. An ExecPlan that ships C# under `src/Assets/_Project/Scripts/**` triggers `HARNESS-LOOP-REVIEW-BEFORE-COMPLETION` (the `/review-gameplay` skill must run) and `HARNESS-LOOP-RUNTIME-PROBE-BEFORE-COMPLETION` (the runtime-probe artifact path is cited in `Validation and Acceptance`).
- **Claude Code session state.** `TaskCreate` todos and `superpowers:writing-plans` scratch are *ephemeral* — they live in the conversation. The ExecPlan's `Progress` section is the *persistent* record; it survives when the session ends. `superpowers:writing-plans` may be used to draft the initial skeleton in a worktree; the committed ExecPlan conforms to this loop's rules regardless of how it was drafted.

## 8. Skeleton template

Copy-paste-ready. Fill in the angle-bracketed placeholders. Do not omit, rename, or reorder any of the twelve headings.

```
---
id: EXEC-<NNN>-<kebab-title>
type: exec-plan
status: proposed
date: <YYYY-MM-DD>
derives_from: PLAN-<NNN>   # omit if free-standing
owners: [<role>]            # gameplay-programmer | level-designer | asset-designer | systems-designer
---

# EXEC-<NNN> — <short, action-oriented title>

> This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds. Once `done`, the whole file becomes immutable except to mark `superseded`. See `docs/process/exec-plans.md` for the full methodology and `.claude/rules/exec-plans.md` for the binding rules.

## Purpose / Big Picture

<Two to four sentences. User-visible behaviour and what becomes possible after this ExecPlan lands. No bullet list, no table, no checklist.>

## Progress

- [ ] (YYYY-MM-DD HH:MMZ) <First atomic step in execution.>
- [ ] (YYYY-MM-DD HH:MMZ) <Second atomic step.>
- [ ] (YYYY-MM-DD HH:MMZ) <…>

## Surprises & Discoveries

_None yet._

## Decision Log

_None yet._

## Outcomes & Retrospective

_To be written at done._

## Context and Orientation

<The load-bearing section. Inline-define every internal ID the ExecPlan cites downstream. For each cited system / config / event / scene / rule, transcribe the registry entry's purpose plus the SDD's invariants plus the TDD's class signature, paraphrased into one paragraph. Define every term of art on first use. Paraphrase relevant ADRs in the agent's own words.>

## Plan of Work

<Prose description of the edits and additions. Concrete and minimal. No tables, no checklists. The reader comes out knowing the shape of the change.>

## Concrete Steps

<Exact commands, working directories, expected transcripts. Flat fenced code blocks where commands run in sequence. No nested fences.>

## Validation and Acceptance

<Observable behaviour, not code presence. Each bullet describes what to exercise and what to observe. The runtime-probe artifact path is cited here (committed under `docs/levels/<scene>/img/` or `src/Assets/_Editor/RuntimeReports/` or `docs/plans/<plan>/runtime-probe.md`).>

## Idempotence and Recovery

<What happens if the ExecPlan is restarted mid-flight. Safe retry paths. Cleanup steps for failed partial runs.>

## Artifacts and Notes

<Embedded transcripts, diffs, screenshots. Everything an agent might want to compare against during execution.>

## Interfaces and Dependencies

<Prescriptive naming for new types, modules, functions, files. Explicit declaration of every dependency (registry IDs, ADRs, packages, MCP servers) and where each is defined inline in `Context and Orientation` above.>
```

## 9. The end-of-session ritual

When closing a session that worked on an ExecPlan:

1. Verify the four mutable sections are current. `Progress` reflects what landed in the diff. `Surprises & Discoveries` has any new entries the session produced. `Decision Log` has any new decisions. `Outcomes & Retrospective` is still the placeholder unless the ExecPlan is reaching `done`.
2. If the ExecPlan transitions to `paused`, write the pause note: `Paused at: <ISO date>, last completed task: Task X` (referencing the last completed `Progress` line by `(timestamp)` prefix) plus a one-paragraph handoff.
3. If the ExecPlan transitions to `done`, write `Outcomes & Retrospective` (achieved / deferred / would-do-differently). The whole file becomes immutable; any further changes require a successor ExecPlan that supersedes this one.
4. Run the matching `/review-*` skill per `HARNESS-LOOP-REVIEW-BEFORE-COMPLETION`. The reviewer checks both the code diff and the ExecPlan diff against the five `EXEC-PLAN-*` rules.
5. Commit. The commit message names the ExecPlan ID and the `Progress` lines it advanced.

## 10. Staged forcing — where this is going

Today the five rules are enforced by agent discipline plus `code-reviewer` audit. A follow-up plan (not yet numbered) will ship `scripts/check-exec-plan.py` with the same exit-code convention as the other `check-*.py` scripts (0 clean, 1 violation, 2 infrastructure error). The script will be wired into `scripts/git-hooks/pre-commit` for the grep-able rules (`MANDATORY-SECTIONS`, `FORMAT-DISCIPLINE`) and into `SessionStart` advisory mode for the inferential rules (`SELF-CONTAINED`, `LIVING-DOCUMENT`, `OBSERVABLE-OUTCOME`).

The steering convention from ADR-0011 applies: when a new Claude / Codex / Gemini release lands, the next plan touching the harness re-examines each forcing component by removing it once and measuring the cost. Components whose absence no longer hurts are retired. ExecPlan rules are subject to the same review.
