---
id: ADR-0012-adopt-exec-plan-methodology
type: decision
status: accepted
date: 2026-05-13
related: [ADR-0003, ADR-0011]
---

# ADR 0012: Adopt ExecPlan methodology — self-contained execution documents as binding artifact

## Context

The repo has reached a particular shape: 11 ADRs, 7 scoped rule files, 15 plans (6 `done`, 9 `proposed`), a stable-ID registry covering nine ID classes, canonical loops for asset-design, level-design, and harness-engineering. What it does **not** have yet is C# under `src/Assets/_Project/Scripts/**`. The next plans in the queue (PLAN-008 Unity bootstrap, PLAN-009 LevelSpec, PLAN-012 player and camera) are the first that will produce code.

Re-reading the 15 existing plans reveals a structural fact: none of them are *execution documents*. They are specs of intention — tables of deliverables, scope lists, acceptance criteria, all heavily cross-referenced to ADRs, SDD/TDD sections, and registry IDs. They tell a human reader (or a reviewer agent with access to the full repo) *what to build*. They do not, on their own, tell a stateless coding agent *how to execute end-to-end without other context*.

OpenAI's Cookbook article "Codex Exec Plans" (published 2026, accessible at `https://developers.openai.com/cookbook/articles/codex_exec_plans`) describes the missing artifact. They define an *ExecPlan* as *"a design document that a coding agent can follow to deliver a working feature or system change"* and observed agent runs spanning seven-plus hours from a single ExecPlan. The article names three non-negotiable invariants:

> *"Every ExecPlan must be fully self-contained."*
>
> *"Every ExecPlan is a living document."*
>
> *"Every ExecPlan must produce a demonstrably working behavior, not merely code changes."*

It also prescribes a twelve-section template (Purpose / Progress / Surprises & Discoveries / Decision Log / Outcomes & Retrospective / Context and Orientation / Plan of Work / Concrete Steps / Validation and Acceptance / Idempotence and Recovery / Artifacts and Notes / Interfaces and Dependencies) and four format rules (checklists only in Progress, no tables outside Progress, no nested code fences, every term of art defined inline).

This repo has the *contract* layer well developed but no *execution* layer. PLAN-012 was the original canary because its scope is precise, but the current execution order makes PLAN-008 the first implementation candidate. The moment any implementation plan begins, the agent will need either (a) full conversation context per session, which breaks at the multi-hour mark, or (b) a self-contained execution doc that re-anchors the work each session. (a) is the failure mode OpenAI's article specifically calls out; (b) is the ExecPlan.

The design spec at `docs/specs/2026-05-13-adopt-exec-plan-methodology-design.md` settles the details: which sections are mandatory, where ExecPlans live (`docs/exec-plans/`), how they relate to existing plans (cite via `derives_from:`, do not migrate), the self-containment carve-out that lets internal IDs be referenced (provided they are transcribed inline in `Context and Orientation`), and the lifecycle constraints. This ADR records the binding decision; it does not duplicate the spec's content.

Three authoring patterns were considered before settling on this one:

- **Tooling-first.** Build an `/exec-plan-new` skill, a linter that mechanically checks the five rule IDs, and a Stop-hook that refuses to "finish" without an ExecPlan when execution work is detected. Rejected — same reasoning as ADR-0011's tooling-first rejection: the tools would be tested against an empty execution surface and the design would be guess-work. Methodology lands first, mechanical surfaces follow.
- **Methodology-first (chosen).** Author the ADR, the canonical loop doc (`docs/process/exec-plans.md`), and the rule file (`.claude/rules/exec-plans.md`) now. Plus the supporting edits to `AGENTS.md`, `CLAUDE.md`, `docs/plans/README.md`. The forcing is by agent discipline plus `code-reviewer` audit until the linter follow-up plan ships. Same staged-forcing pattern as ADR-0011.
- **Full migration of existing plans.** Reshape the 15 current plans into the twelve-section format. Rejected — the existing plans are valid as specs of intention. They were never meant to be ExecPlans. Migrating them would dilute their meaning and produce twelve-section artifacts that have nothing to put in `Progress` or `Decision Log` because the work has not been executed yet.

## Decision

Adopt the **ExecPlan** as a new binding artifact type for execution work. ExecPlans live under `docs/exec-plans/`, are numbered `EXEC-NNN-<kebab-title>.md` in a namespace separate from `PLAN-NNN`, and conform to the methodology recorded in `docs/process/exec-plans.md`. Five rule IDs in `.claude/rules/exec-plans.md` codify the invariants:

### A. `EXEC-PLAN-SELF-CONTAINED`

An ExecPlan reads end-to-end without any external file. Internal-repo IDs may be cited if they are transcribed inline in `Context and Orientation` with enough detail for a fresh agent to act on them (the worked-example test in the design spec is the bar). External links (blog posts, vendor docs, third-party articles) are forbidden in the body; if their content matters, paraphrase it inline. Artifact paths committed under the repo (runtime-probe screenshots, JSON reports) are explicitly *not* external links and may be cited as load-bearing references — they are the runtime-probe contract enforced by `HARNESS-LOOP-RUNTIME-PROBE-BEFORE-COMPLETION` (ADR-0011).

### B. `EXEC-PLAN-LIVING-DOCUMENT`

While the ExecPlan is `active`, the four mutable sections (`Progress`, `Surprises & Discoveries`, `Decision Log`, `Outcomes & Retrospective`) are updated *during* execution at every commit, not after. Once `done`, the entire file is immutable except to mark `superseded`. The mutability is load-bearing: it is the mechanism by which the ExecPlan stays a faithful execution record rather than a polished post-hoc retelling.

### C. `EXEC-PLAN-OBSERVABLE-OUTCOME`

`Validation and Acceptance` is written as observable behaviour, not as "the code is written" or "the tests exist". An acceptance line that reads "implement `OxygenSystem.Tick()`" is a violation; "after holding `space`, the oxygen bar fills back to 100% within 3 seconds" is valid. The rule inherits from Anthropic's observation that stubs appear functional in static review; observable acceptance is the lever.

### D. `EXEC-PLAN-MANDATORY-SECTIONS`

Every ExecPlan, at every status (`proposed`, `active`, `done`, `paused`, `abandoned`, `superseded`), has all twelve top-level headings from the design spec present and in the order listed there. Headings match the names verbatim. A `proposed` ExecPlan may have placeholder bodies under `Progress` (heading only, no items) and `Outcomes & Retrospective` (heading plus `_To be written at done._`). What it may not do is omit, rename, or reorder any of the twelve.

### E. `EXEC-PLAN-FORMAT-DISCIPLINE`

Three grep-able bans: checklists only in `Progress`; tables only in `Progress`; no nested code fences. The bans make the ExecPlan a sequential narrative an agent reads top to bottom, not a referenceable artifact it has to jump around inside.

### Staged-forcing convention

Mirroring ADR-0011: the five rules are enforced today by agent discipline plus `code-reviewer` audit. A follow-up plan (not scoped here) will ship `scripts/check-exec-plan.py` for mechanical enforcement, wired into the pre-commit hook chain. Until then, drift is expected; the reviewer is the primary sensor.

### Relationship to existing plans

ExecPlans do **not** replace plans. The 15 existing plans in `docs/plans/` remain valid as specs of intention. When implementation work begins on a plan, the executing role creates an `EXEC-NNN-<title>.md` that declares `derives_from: PLAN-NNN` in its frontmatter and inlines the relevant excerpts from the plan, the cited ADR(s), the SDD section(s), the TDD section(s), and the registry entries into `Context and Orientation`. The Plan = intent; the ExecPlan = what actually happened.

Free-standing ExecPlans (no originating Plan) are allowed in exceptional cases (incident response, single-session refactor that does not warrant a Plan). They omit `derives_from:` and cite the trigger in `Context and Orientation`.

## Alternatives considered

- **Tooling-first.** Reject; documented above. The pre-code moment is the wrong time to design tools against an empty execution surface.
- **Full migration of existing plans.** Reject; documented above. Existing plans are specs of intention, not execution records.
- **Status quo.** Reject. Without an execution artifact, the multi-hour execution work the article describes is unreachable — the agent has to keep all relevant context in conversation, which breaks the moment the session resets or a subagent is dispatched.
- **Folder split `docs/plans/` → game-plans vs process-plans.** Considered early in the design conversation as a way to make the plans index legible. Rejected once the ExecPlan model surfaced: the split would have been bureaucracy without solving the actual problem (no execution artifact). ExecPlans solve it; the split is unnecessary.
- **Adopt OpenAI's `PLANS.md` filename verbatim.** Reject. The repo's convention is `docs/process/<name>.md` for canonical loops; `docs/process/exec-plans.md` follows the convention without changing the content.

## Consequences

- **Easy.** The methodology lands in five new files (`docs/decisions/0012-*.md`, `.claude/rules/exec-plans.md`, `docs/process/exec-plans.md`, `docs/exec-plans/README.md`, `docs/exec-plans/.gitkeep`) plus pointers in `AGENTS.md`, `CLAUDE.md`, and `docs/plans/README.md`. Stable `rule_id`s are allocated in `architecture.yaml::rules`. Plans written from this point cite the rule IDs; the agent already reads `.claude/rules/**` at the start of every session.
- **Easy.** No existing plan is migrated. The 15 plans keep their current text. Cross-references to them remain valid.
- **Hard.** Until the linter follow-up plan ships, the five `EXEC-PLAN-*` rules are enforced by agent discipline plus `code-reviewer` audit. The first ExecPlan (`EXEC-001-unity-bootstrap.md`, deriving from PLAN-008) will be the field test for whether the discipline holds.
- **Hard.** The self-containment carve-out (internal IDs may be cited if transcribed inline) is a quality bar, not a mechanical check. The reviewer flags egregious omissions by `EXEC-PLAN-SELF-CONTAINED`. Drift toward one-line glosses ("`SYS-OXYGEN` is the oxygen system, see SDD") is the expected failure mode; the worked example in the design spec is the reference.
- **Accepted loss.** The term-of-art discipline (every term in `docs/registry/glossary.md` is inline-paraphrased on first use) is advisory under `EXEC-PLAN-SELF-CONTAINED`, not separately enforced. The reviewer catches egregious cases; minor omissions slip.
- **Mandatory acceptance** (no new tests in this ADR — the artifacts are documentation):
  - Every new `rule_id` is registered in `architecture.yaml::rules` with `status: active` and `cite_adr: ADR-0012`.
  - `scripts/audit-md.py` runs clean against the new files.
  - The grep checks in the design spec's §Acceptance criteria all return the expected matches.
- **Mandatory rules** (`.claude/rules/exec-plans.md`):
  - `EXEC-PLAN-SELF-CONTAINED`
  - `EXEC-PLAN-LIVING-DOCUMENT`
  - `EXEC-PLAN-OBSERVABLE-OUTCOME`
  - `EXEC-PLAN-MANDATORY-SECTIONS`
  - `EXEC-PLAN-FORMAT-DISCIPLINE`

## Notes

- The design spec at `docs/specs/2026-05-13-adopt-exec-plan-methodology-design.md` is the canonical reference for section-by-section detail (the twelve mandatory sections, the worked example for the self-containment carve-out, the four open questions and their resolutions). This ADR records the decision; the spec records the design.
- OpenAI's Cookbook article is cited as external provenance for the methodology and the section names. It is **not** load-bearing inside any ExecPlan body — `EXEC-PLAN-SELF-CONTAINED` forbids external blog/vendor/article links in ExecPlans. ADR-0012 may cite the article because the ADR is a `type: decision`, not an ExecPlan.
- ExecPlans share the existing plan lifecycle states (`proposed | active | paused | done | abandoned | superseded`) and the existing pause-note convention (`Paused at: <date>, last completed task: Task X` plus one-paragraph handoff for whoever resumes). The "Task X" entry in an ExecPlan references the last completed `Progress` checklist line by its `(timestamp)` prefix.
- The follow-up linter plan is not numbered here; it will be allocated when the first `EXEC-001` runs and the discipline shows whether mechanical forcing is needed sooner or later. Same steering convention as ADR-0011: components whose absence no longer hurts are retired; components whose absence hurts are escalated.
