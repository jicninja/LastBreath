---
id: SPEC-2026-05-13-adopt-exec-plan-methodology
type: spec
layer: spec
status: proposed
related: [ADR-0011, PLAN-012]
---

# Adopt ExecPlan methodology — design spec

> **Documentation-only spec.** Establishes the *ExecPlan* artifact (per OpenAI Cookbook, "Codex Exec Plans") as the binding format for execution work in this repo. Adds one new folder, one ADR, one rule file, one process doc, and edits to `AGENTS.md` + `CLAUDE.md`. Does not migrate or alter any existing plan in `docs/plans/`. Implementation of the spec is scheduled via a follow-up plan.

## Context

The repo today has 15 plans under `docs/plans/`, of which 6 are `done`, 1 is `active` (PLAN-012), and the rest are `proposed`. Re-reading them reveals that none are *execution documents* in the OpenAI sense — they are **specs of intention**: tables of deliverables, scope lists, acceptance criteria, all heavily cross-referenced to ADRs, SDD/TDD, and registry IDs.

OpenAI's Cookbook article "Codex Exec Plans" (`https://developers.openai.com/cookbook/articles/codex_exec_plans`) describes a different artifact: a *living, self-contained document that a stateless coding agent can read top-to-bottom and execute end-to-end without any other context.* They observed agent runs spanning seven-plus hours from a single ExecPlan and concluded:

> *"Every ExecPlan must enable a complete novice to implement the feature end-to-end without prior knowledge."*
>
> *"Every ExecPlan must produce a demonstrably working behavior, not merely code changes."*

This repo has the *contract* layer well-developed (ADRs + SDD + TDD + registry) but no *execution* layer. When PLAN-012 (player + camera) actually moves from `active` to producing C# under `src/Assets/_Project/Scripts/**`, the agent will need either (a) to keep all the relevant context in conversation, or (b) a self-contained execution doc that re-anchors the work each session. (a) breaks at the multi-hour mark; (b) is the ExecPlan model.

The gap is precise: **we have plans, we do not have ExecPlans.** This spec adopts the ExecPlan as a new artifact type, parallel to the existing plan format, and binds it via rules.

The spec does **not** retroactively reshape the 15 existing plans. They remain valid as specs of intention. When their execution begins, a new ExecPlan is created that cites the plan and expands its content inline.

---

## Decisions

### 1. ExecPlan as a distinct artifact

An *ExecPlan* is a single markdown file under `docs/exec-plans/`, numbered `EXEC-NNN-<kebab-title>.md`. It is the artifact a coding agent reads — and only that artifact — to execute multi-session implementation work end-to-end.

Distinct from the existing plan format:

| Property | Plan (`docs/plans/`) | ExecPlan (`docs/exec-plans/`) |
|---|---|---|
| Purpose | Fix intent, scope, acceptance | Execute the work |
| Lifetime | `proposed` → `active` → `done` (immutable once `done`) | `proposed` → `active` (mutable, four sections required-updated per commit) → `done` (whole file frozen) |
| Self-containment | Cross-refs ADRs, SDD, TDD freely | Must inline-define every term, ID, and dependency |
| Format | Tables, bullet lists, frontmatter, scope sections with checkboxes | 12 mandatory sections; checklists *only* in `Progress`; no tables outside `Progress` |
| Audience | Human reader + reviewer agents | Stateless coding agent (single-shot or multi-session) |
| Relationship | Source of intent | Execution doc that *cites* a Plan |

ExecPlans coexist with the existing plan format. They do not replace plans.

### 2. The twelve mandatory sections

Every ExecPlan, from creation, carries these twelve top-level sections in this order. Their names match the OpenAI Cookbook verbatim so an agent trained on that vocabulary recognises the surface:

1. **Purpose / Big Picture** — user-visible behaviour and what becomes possible after the ExecPlan lands.
2. **Progress** — checkbox list with `(YYYY-MM-DD HH:MMZ)` timestamps; the only section in which checklists are permitted; the only section in which the format allows enumerated/tabular content.
3. **Surprises & Discoveries** — unexpected behaviours, bugs, optimisations encountered during execution; each entry references a transcript, diff, or screenshot.
4. **Decision Log** — `Decision: … / Rationale: … / Date & Author: …` triples. Every non-obvious choice the agent made during execution lands here.
5. **Outcomes & Retrospective** — written once the ExecPlan reaches `done`; what was achieved, what was deferred, what would be done differently.
6. **Context and Orientation** — current state of the relevant slice of the repo, full file paths, definitions of every term of art used downstream in the doc. The self-containment guarantee is enforced here: an agent reading only this section must understand the problem space.
7. **Plan of Work** — prose description of the edits and additions, concrete and minimal. No tables. No checklists.
8. **Concrete Steps** — exact commands, working directories, expected transcripts. Where commands are listed in sequence, they go in fenced code blocks; no nested fences inside.
9. **Validation and Acceptance** — how to exercise the resulting system and what to *observe* (not what was written). Phrased as observable behaviour: "After running X, the console prints Y", "the smoke scene reaches state Z without errors", "the test `Foo_Bar_Baz` passes".
10. **Idempotence and Recovery** — what happens if the ExecPlan is restarted mid-flight; safe retry paths; cleanup steps for failed partial runs.
11. **Artifacts and Notes** — embedded transcripts, diffs, screenshots; everything an agent might want to compare against during execution.
12. **Interfaces and Dependencies** — prescriptive naming for new types, modules, functions, files; explicit declaration of every dependency (registry IDs, ADRs, packages, MCP servers) and where each is defined inline.

The order is fixed. Adding sections beyond these twelve is allowed only when scoped under one of the twelve as a subsection. Removing or renaming any of the twelve is forbidden.

### 3. The three non-negotiable invariants

Carried verbatim from the OpenAI Cookbook and rephrased here as binding properties:

- **`EXEC-PLAN-SELF-CONTAINED`** — the doc reads end-to-end without any external file. Internal-repo IDs (`PLAN-NNN`, `ADR-NNNN`, `SYS-*`, `EVT-*`, `CFG-*`, `LAYOUT-*`, …) may be cited *only if* they are defined inline in `Context and Orientation` with enough detail to act on them (see §5 for the worked-example test of "enough detail"). External links (blog posts, vendor docs, third-party articles) are forbidden in the body; if their content matters, paraphrase it inline. Artifact paths committed under the repo (for example `docs/levels/<scene>/img/*.png`, `src/Assets/_Editor/RuntimeReports/*.json`, `docs/plans/<plan>/runtime-probe.md`) are **not** external links and may be cited as load-bearing references — they are the runtime-probe contract enforced by `HARNESS-LOOP-RUNTIME-PROBE-BEFORE-COMPLETION` (ADR-0011) and inlining a screenshot or a JSON report makes the ExecPlan less, not more, self-contained. References that name internal IDs without inline definitions, or that say "as defined previously" / "see ADR-0011" without copying the relevant excerpt, are violations.

  Term-of-art discipline rides on this rule (advisory, not separately enforced): every term that has an entry in `docs/registry/glossary.md` is inline-paraphrased the first time the ExecPlan uses it. Terms outside the glossary are defined in the agent's own words near first use. The reviewer flags egregious omissions as `EXEC-PLAN-SELF-CONTAINED` violations.

- **`EXEC-PLAN-LIVING-DOCUMENT`** — `Progress`, `Surprises & Discoveries`, `Decision Log`, `Outcomes & Retrospective` are updated *during* execution, not after. While the ExecPlan is `active`, edits to those four sections are not just allowed but required at every commit. Once the ExecPlan reaches `done` (the work is shipped, validation passed, retrospective written), the file becomes immutable except to mark `superseded`.

- **`EXEC-PLAN-OBSERVABLE-OUTCOME`** — `Validation and Acceptance` is written as observable behaviour, not as "the code is written" or "the tests exist". An acceptance line that reads "implement `OxygenSystem.Tick()`" is a violation; "after holding `space`, the oxygen bar fills back to 100% within 3 seconds" is valid.

### 4. Structural and format rules

Two further rules govern the ExecPlan's shape on disk. Both are mechanical (a reviewer can grep for violations) and both derive from OpenAI's prescribed skeleton template:

- **`EXEC-PLAN-MANDATORY-SECTIONS`** — every ExecPlan, at every status (`proposed`, `active`, `done`, `paused`, `abandoned`, `superseded`), has all twelve top-level headings from §2 present and in the order listed there. Headings match the names verbatim. A `proposed` ExecPlan may have a `Progress` section with only the heading and no checklist items; it may have an `Outcomes & Retrospective` section with only the heading and a placeholder line (`_To be written at done._`). What it may not do is omit, rename, or reorder any of the twelve. The reviewer greps for each of the twelve heading strings; a missing one is a violation.

- **`EXEC-PLAN-FORMAT-DISCIPLINE`** — three grep-able bans:
  - Checklists (`- [ ]`, `- [x]`) appear *only* in the `Progress` section. The reviewer greps for `- [` outside `Progress`; matches are violations.
  - Tables (lines beginning with `|`) appear *only* in `Progress`. The rest of the doc is prose-first.
  - Code fences are not nested. Each fenced block is flat.

The bans are deliberate. Their effect is to make the ExecPlan a sequential narrative that an agent reads from top to bottom rather than a referenceable artifact it has to jump around inside.

### 5. Self-containment carve-out — internal IDs

The strictest reading of OpenAI's rule would forbid any cross-reference at all. That collides with this repo's foundational pattern: stable IDs in `docs/registry/architecture.yaml` are the canonical names for systems, configs, events, scenes, and rules. An ExecPlan that re-derives "what is `SYS-OXYGEN`" from scratch each time is unmaintainable and risks divergence from the registry.

The carve-out: **internal-repo IDs may be cited in any section of an ExecPlan, provided they are defined inline in `Context and Orientation` with the minimum content needed for a fresh agent to act on them.** The inline definition is a copy-paste-and-adapt from the registry entry, the ADR, the SDD section, or the TDD signature — whichever is the source of truth.

"Minimum content" is the worked-example test below, not a one-line gloss. If the inline definition is shorter than the registry entry it transcribes, it is insufficient. If a downstream section names the ID and the reader has to scan backwards to figure out what it means, the carve-out has been abused.

Worked example — what counts as a sufficient inline definition for `SYS-OXYGEN`:

> **Forbidden** (one-line gloss; relies on external knowledge):
> *"SYS-OXYGEN is the oxygen system."*
>
> **Forbidden** (cites the registry without transcribing it):
> *"SYS-OXYGEN per `docs/registry/architecture.yaml::systems` — see also SDD §OxygenSystem."*
>
> **Allowed** (transcribes the responsibility, the public surface, the events, the configs, and the file path; a fresh agent can act on it):
> *"`SYS-OXYGEN` is the runtime oxygen budget for the player. It owns one `float Current` on `[0, _config.MaxOxygen]` and one `bool IsDepleted`. It publishes `Action<float, float> OxygenChanged(current, max)` every time `Current` changes and `Action OxygenDepleted` exactly once when `Current` hits zero. It reads from `OxygenConfig` (a `ScriptableObject` at `src/Assets/_Project/Config/Oxygen/`) which carries `MaxOxygen`, `BaseDrainPerSecond`, and `RefillPerSecond`. The class lives at `src/Assets/_Project/Scripts/Oxygen/OxygenSystem.cs` and is registered on the scene's `GameLifetimeScope` per `GAMEPLAY-CODE-DI-LIFETIMESCOPE-ONLY-AT-ROOT`. It runs in `Update`, not `FixedUpdate`. It restores state via `RestoreState(OxygenDto)` which assigns `Current` directly without firing `OxygenChanged` (per `GAMEPLAY-CODE-SAVE-NO-EVENTS-DURING-LOADING`)."*

The Allowed form is roughly the registry entry's purpose line plus the SDD's Invariants list plus the TDD's class signature — paraphrased into one paragraph. That is the bar.

The agent's mental model when writing an ExecPlan: `Context and Orientation` is the agent's *transcribed working memory* of the slice of the repo being modified. If a fact is true but absent from `Context and Orientation`, it is invisible to a future agent reading the doc cold. The rule forces transcription.

External resources (Unity docs, Cinemachine 3 release notes, an OpenAI blog post) are **not** covered by this carve-out. If their content matters, the agent paraphrases the relevant fact into `Context and Orientation` in its own words, and cites the source only as provenance — never as the load-bearing reference.

### 6. Lifecycle and mutability

ExecPlan status values mirror the existing plan lifecycle (`docs/plans/README.md` §Lifecycle and §Transitions) but with extra constraints on what gets edited at each status:

- `proposed` — drafted, not yet started. All twelve sections present (`EXEC-PLAN-MANDATORY-SECTIONS`); `Progress` carries only the heading, no items; `Outcomes & Retrospective` carries only the heading and the placeholder `_To be written at done._`.
- `active` — execution underway. `Progress`, `Surprises & Discoveries`, `Decision Log` updated at every commit per `EXEC-PLAN-LIVING-DOCUMENT`. `Outcomes & Retrospective` may stay as the placeholder until `done`.
- `done` — work shipped, validation passed, retrospective written. **The whole file becomes immutable** except to mark `superseded`. This is stricter than plans, where only the `done` plan's content is frozen by `docs/plans/README.md` line 40; in ExecPlans the freeze covers `Outcomes & Retrospective` too.
- `paused` — `docs/plans/README.md` §Pause and resume applies verbatim: the frontmatter carries a `Paused at: <date>, last completed task: Task X` note and a one-paragraph handoff for whoever resumes. The "Task X" entry references the last completed `Progress` checklist line by its `(timestamp)` prefix. The four living sections capture the state at pause; resuming continues editing them.
- `abandoned` — stopped without resuming. The `Outcomes & Retrospective` section is filled with the reason for abandonment and what (if anything) survives in the working tree to be picked up later.
- `superseded` — a later ExecPlan replaced this one. `superseded_by: EXEC-NNN` lands in the frontmatter and a link to the replacement goes at the top of the body.

The real contrast with `docs/plans/` is not "static vs living" — both are mutable while `active`, both freeze at `done`. The real contrast is:

1. **What gets edited while `active`.** A plan's `active` edits are typically narrow (checking off scope items, refining acceptance). An ExecPlan's `active` edits are continuous: every commit appends to `Progress`, `Surprises & Discoveries`, or `Decision Log` if any of those grew. `EXEC-PLAN-LIVING-DOCUMENT` makes this a binding obligation, not a habit.
2. **What `done` freezes.** A plan's `done` freeze (per `docs/plans/README.md` line 40) covers the plan's intent — the scope and acceptance the team committed to. An ExecPlan's `done` freeze covers the *execution record* — what actually happened, what the agent decided, what it tripped on. Both are historical artifacts after `done`; what they record is different.

### 7. Numbering — separate space

ExecPlans use `EXEC-NNN`, plans use `PLAN-NNN`. The two namespaces do not share numbering. The first ExecPlan is `EXEC-001`, regardless of what plan number it derives from. The numbering is global within `docs/exec-plans/` (never reused, always incremented from the highest existing `NNN`).

Rationale: ExecPlans are a different *class* of artifact, not a different *category* of plan. Sharing the `PLAN-NNN` series would obscure that distinction every time the agent or a human reads a number.

Cross-reference is by ID. An ExecPlan that derives from PLAN-012 declares it in the frontmatter `derives_from: PLAN-012` and re-defines the relevant content inline in `Context and Orientation`. Free-standing ExecPlans (no originating Plan) omit `derives_from:`; see Open Question 4 for when that is appropriate.

### 8. Relationship to existing plans

The 15 existing plans in `docs/plans/` are not migrated, renamed, or reformatted. They retain their current role as **specs of intention** — they fix scope, acceptance, ownership, dependencies. They are valuable to humans and to reviewer agents.

When execution work on a plan begins, the executing role creates an `EXEC-NNN-<title>.md` that:

- declares `derives_from: PLAN-NNN` in its frontmatter,
- expands the plan's deliverable list into the twelve mandatory ExecPlan sections,
- inlines the relevant excerpts from the cited ADR(s), SDD section(s), TDD section(s), and registry entries into `Context and Orientation`,
- becomes the single artifact the agent reads during execution.

When the ExecPlan reaches `done`, the originating Plan is also marked `done` (its acceptance criteria are now met by the ExecPlan's outcomes). The two artifacts live side by side as historical record: Plan = intent; ExecPlan = what actually happened.

PLAN-012 (currently `active`) is the first candidate. Its execution will be tracked by `EXEC-001-implement-player-and-camera.md`, created at the start of the implementation session.

### 9. Compatibility with existing methodology

ExecPlans extend the repo's harness; they do not replace any existing rule.

- **AGENTS.md global rules** stay binding. An ExecPlan that ships C# under `src/Assets/_Project/Scripts/**` triggers `HARNESS-LOOP-REVIEW-BEFORE-COMPLETION` (the `/review-gameplay` skill) and `HARNESS-LOOP-RUNTIME-PROBE-BEFORE-COMPLETION` (the runtime-probe artifact) just like any other gameplay-touching change. The ExecPlan's `Validation and Acceptance` section is where the runtime-probe artifact gets cited.
- **`.claude/rules/`** still applies path-by-path. The ExecPlan is the *vehicle*; the rule files are still the *constraint*. `GAMEPLAY-CODE-NO-FINDOBJECTOFTYPE` does not stop applying inside an ExecPlan-driven session.
- **`docs/registry/architecture.yaml`** stays the source of truth. The ExecPlan transcribes registry content; it does not override or compete with it.
- **`code-reviewer` subagent** reads diffs as before. The ExecPlan itself is also reviewable; the reviewer can call out a missing section, an external link, a checklist outside `Progress`, etc.

### 10. Compatibility with Claude Code session state

ExecPlans are persistent files in the repo. Claude Code's in-session affordances — `TaskCreate` todos, `superpowers:writing-plans` scratch, `superpowers:executing-plans` checkpoints — coexist with ExecPlans as ephemeral session state.

The relationship:

- The ExecPlan's `Progress` section is the *persistent* record. `TaskCreate` todos are the *session-local* version. When a session ends, the ExecPlan's `Progress` is what survives; todos do not.
- `superpowers:writing-plans` skill output may be used to *draft* the initial twelve-section skeleton inside a worktree, but the committed file must conform to this spec's section list and discipline rules.
- `superpowers:executing-plans` may be used to drive multi-task execution against the ExecPlan, but the ExecPlan is the authoritative file; the skill is the harness around it.

There is no conflict; the layers serve different durations.

---

## Artifacts to ship

The implementation plan that derives from this spec creates the following:

- **`docs/decisions/0012-adopt-exec-plan-methodology.md`** — the ADR that records this decision, cites the OpenAI Cookbook article as external provenance, and binds the rule IDs below.
- **`.claude/rules/exec-plans.md`** — the rule file, with the five rule IDs above (`EXEC-PLAN-SELF-CONTAINED`, `EXEC-PLAN-LIVING-DOCUMENT`, `EXEC-PLAN-OBSERVABLE-OUTCOME`, `EXEC-PLAN-MANDATORY-SECTIONS`, `EXEC-PLAN-FORMAT-DISCIPLINE`), each with Forbidden / Allowed / Cite blocks in the same format as `.claude/rules/harness-loop.md`.
- **`docs/process/exec-plans.md`** — the canonical loop. Mirrors what OpenAI calls `PLANS.md`: when to open an ExecPlan, how to author one, how to keep it living, when to close it. Includes the twelve-section skeleton template as an embedded fenced block.
- **`docs/exec-plans/README.md`** — the folder index. Lists every ExecPlan with status, derived-from plan, and `done` date. Mirrors the structure of `docs/plans/README.md`.
- **`docs/exec-plans/.gitkeep`** — folder marker so the folder exists with no ExecPlans yet.
- **`docs/registry/architecture.yaml::rules`** — five new entries (the five rule IDs above), each with `status: active`, `file: .claude/rules/exec-plans.md`, `cite_adr: ADR-0012`, and a one-line `purpose`.
- **`AGENTS.md`** — three insertions:
  - `§Before acting — required reading` gains item 9: "`docs/process/exec-plans.md` — the canonical loop for ExecPlans (the artifact a coding agent reads to execute multi-session implementation work). Binds the `EXEC-PLAN-*` rules. ADR-0012."
  - `§Global rules` gains: "ExecPlans are the format for execution work. When implementation of a Plan begins, the executing role opens `docs/exec-plans/EXEC-NNN-<title>.md` with the twelve mandatory sections. Full rule: `.claude/rules/exec-plans.md`. Canonical loop: `docs/process/exec-plans.md`. ADR-0012."
  - `§File conventions` gains `docs/exec-plans/` to the list of doc folders.
- **`CLAUDE.md`** — one insertion: `exec-plans.md — ExecPlans under \`docs/exec-plans/\` (ADR-0012).` added to the bulleted list of `.claude/rules/` files. (CLAUDE.md compatibility: same shape as the existing entries, no behavioural divergence from AGENTS.md, AGENTS.md remains the source of truth.)
- **`docs/plans/README.md`** — one-line discoverability anchor added under the existing Lifecycle section: `Execution of these plans is tracked separately in ExecPlans under \`docs/exec-plans/\` — see \`docs/process/exec-plans.md\` and ADR-0012.` This is the only allowed edit to `docs/plans/README.md` in this spec; the existing lifecycle, transitions, and index format remain untouched.

The implementation plan adds **no** ExecPlans yet — the first ExecPlan (`EXEC-001-implement-player-and-camera.md`, deriving from PLAN-012) is the deliverable of a *subsequent* plan, not this one.

---

## Acceptance criteria

This spec is implemented correctly when all of the following are observable in the repo:

- `docs/decisions/0012-adopt-exec-plan-methodology.md` exists with `status: accepted` and a `related:` frontmatter line that names, at minimum, ADR-0011 (the staged-forcing precedent the ADR inherits from). The ADR may cite additional decisions in `related:` if its body load-bearingly draws on them; what it does **not** do is cite plans, since the existing ADR convention (e.g., ADR-0011 `related: [ADR-0003, ADR-0007, ADR-0008, ADR-0009]`) is ADRs-only.
- `.claude/rules/exec-plans.md` exists with the five rule IDs (`EXEC-PLAN-SELF-CONTAINED`, `EXEC-PLAN-LIVING-DOCUMENT`, `EXEC-PLAN-OBSERVABLE-OUTCOME`, `EXEC-PLAN-MANDATORY-SECTIONS`, `EXEC-PLAN-FORMAT-DISCIPLINE`), each containing Forbidden / Allowed / Cite blocks in the format used by `.claude/rules/harness-loop.md`.
- `docs/process/exec-plans.md` exists with the twelve-section skeleton template as a fenced block and the canonical loop described in prose.
- `docs/exec-plans/` exists with a `README.md` that explains the folder's purpose, links to `docs/process/exec-plans.md`, and contains an empty index table.
- `docs/registry/architecture.yaml::rules` contains five new entries (one per rule ID above) with `status: active`, all citing `ADR-0012`.
- `AGENTS.md` carries the three insertions described in §Artifacts. Grep checks (anchored against stable section-header strings, not against unrelated paths): `grep -n 'ExecPlan' AGENTS.md` returns at least three matches; the first match's line number is *greater* than the line number returned by `grep -n '## Before acting' AGENTS.md` (the first ExecPlan reference lands inside the §Before acting — required reading list, which is the first major section after the preamble).
- `CLAUDE.md` carries the one insertion described in §Artifacts. Grep check: `grep -n 'exec-plans.md' CLAUDE.md` returns exactly one match inside the `.claude/rules/` list block.
- `docs/plans/README.md` carries the one-line discoverability anchor described in §Artifacts. Grep check: `grep -n 'docs/exec-plans' docs/plans/README.md` returns at least one match.
- `scripts/audit-md.py` runs clean against the new files (no orphans, no broken refs).

---

## Out of scope

Deliberately not in this spec:

- Migrating any of the 15 existing plans to ExecPlan format.
- Creating `EXEC-001-implement-player-and-camera.md` (that is a *subsequent* implementation plan once PLAN-012 begins).
- Authoring a linter that mechanically enforces the five `EXEC-PLAN-*` rules. The rules are enforced by `code-reviewer` discipline until a follow-up plan adds the linter. Same staged-forcing pattern as ADR-0011 (rule first, mechanical surface later).
- Changing the existing `.claude/rules/` files. They keep their current text.
- Restructuring `docs/plans/README.md`. The one-line cross-reference is the *only* edit allowed by this spec; the plan-folder split discussed earlier in design conversation (game-plans vs process-plans) is abandoned in favour of this ExecPlan model.
- Adopting OpenAI's "PLANS.md" as a literal filename. The same content lives at `docs/process/exec-plans.md`, consistent with this repo's `docs/process/` convention.

---

## Open questions

The following decisions are surfaced rather than dodged. Each carries a resolution; none of them block this spec from being implemented.

1. **Plan/ExecPlan scope divergence — does the originating Plan stay `done` or become `superseded`?**
   If the ExecPlan ships strictly what the Plan promised, both end `done`. If the ExecPlan's `Outcomes & Retrospective` reports deferred or descoped items, the originating Plan is marked `superseded` and a follow-up Plan captures the new scope. *Resolution: bound by ADR-0012, derived from `docs/plans/README.md` line 26 (`superseded` is the existing off-ramp for "a later plan replaced this one"). No new lifecycle state needed.*

2. **`Outcomes & Retrospective` while `proposed` / `active` — placeholder body required?**
   `EXEC-PLAN-MANDATORY-SECTIONS` requires the heading at every status; `EXEC-PLAN-LIVING-DOCUMENT` says the section is updated *during* execution. A `proposed` ExecPlan therefore carries the heading plus the placeholder line `_To be written at done._`; an `active` ExecPlan may already have partial content. *Resolution: answered inline at §6 (`proposed` semantics) and §4 (`MANDATORY-SECTIONS` accepts placeholder bodies).*

3. **Authoring surface — is there an `/exec-plan-new` skill?**
   Not in this spec. ExecPlans are hand-authored from the skeleton template embedded in `docs/process/exec-plans.md`. `superpowers:writing-plans` may be used as a drafting aid, but the committed file conforms to this spec's rules regardless of how it was drafted. *Resolution: deferred to a follow-up plan (mirrors the staged-forcing pattern of ADR-0011 — methodology lands first, mechanical scaffold later).*

4. **Free-standing ExecPlans — must every ExecPlan derive from a Plan?**
   The dominant flow is Plan → ExecPlan (§8). However, exceptional execution work (a security-driven patch, an incident response, a single-session refactor that does not warrant a Plan) may need an ExecPlan without an originating Plan. *Resolution: `derives_from:` is required when an originating Plan exists; absent when the ExecPlan is free-standing. The canonical loop in `docs/process/exec-plans.md` will recommend that free-standing ExecPlans cite the trigger (issue link, incident report, user-request transcript) in their `Context and Orientation` so the audit trail is preserved.*

---

## References

- OpenAI Cookbook, "Codex Exec Plans" — `https://developers.openai.com/cookbook/articles/codex_exec_plans`. The source methodology. Cited as external provenance in ADR-0012 only; never load-bearing inside an ExecPlan body.
- ADR-0011 — `docs/decisions/0011-harness-engineering-methodology.md`. The precedent for staged-forcing (rule first, mechanical surface later) and for the harness-loop pattern that ExecPlans inherit at session close.
- `docs/process/harness-engineering.md`. The canonical loop ExecPlans plug into for review and runtime-probe.
- PLAN-012 — `docs/plans/012-player-controls-and-camera.md`. The current `active` plan that will be the first to spawn an ExecPlan (`EXEC-001-implement-player-and-camera.md`) when implementation begins.
