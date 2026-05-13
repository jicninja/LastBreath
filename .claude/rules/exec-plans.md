# Rules — ExecPlans

Rules scoped to the *ExecPlan* artifact: any markdown file under `docs/exec-plans/` whose frontmatter declares `type: exec-plan`. ExecPlans are self-contained execution documents that a coding agent reads to deliver a working feature or system change end-to-end; they live alongside the existing `docs/plans/` plans but follow different invariants. Owned jointly by every authoring role that initiates an ExecPlan (`gameplay-programmer`, `level-designer`, `asset-designer`, `systems-designer`) and audited by `code-reviewer`.

Rationale: ADR-0012. Canonical loop: `docs/process/exec-plans.md`. Source methodology: OpenAI Cookbook, "Codex Exec Plans" (2026). The five rules below are enforced today by **agent discipline** and `code-reviewer` audit. The matching mechanical surface (a `scripts/check-exec-plan.py` linter wired into pre-commit and `SessionStart`) is queued as a follow-up plan, mirroring the staged-forcing pattern of ADR-0011. Until that plan lands, drift is detected by the reviewer reading the ExecPlan diff.

The five rules separate cleanly into three philosophical invariants (carried verbatim from OpenAI) and two mechanical structural rules:

- Philosophical: `EXEC-PLAN-SELF-CONTAINED`, `EXEC-PLAN-LIVING-DOCUMENT`, `EXEC-PLAN-OBSERVABLE-OUTCOME`.
- Mechanical: `EXEC-PLAN-MANDATORY-SECTIONS`, `EXEC-PLAN-FORMAT-DISCIPLINE`.

## `EXEC-PLAN-SELF-CONTAINED`

An ExecPlan reads end-to-end without any external file. A fresh coding agent (or human novice) with only the current working tree and the single ExecPlan file must be able to execute the work end-to-end. Internal-repo IDs may be cited only if they are transcribed inline in `Context and Orientation` with enough detail for that fresh agent to act on them (see `docs/process/exec-plans.md` §5 for the worked-example test of "enough detail"). External links (blog posts, vendor docs, third-party articles) are forbidden in the body; if their content matters, paraphrase it inline in the agent's own words.

Forbidden:

- Citing an internal-repo ID (`PLAN-NNN`, `ADR-NNNN`, `SYS-*`, `EVT-*`, `CFG-*`, `LAYOUT-*`, …) without an inline definition in `Context and Orientation`.
- One-line glosses that substitute for an inline definition. `"SYS-OXYGEN is the oxygen system"` does not satisfy the rule even if `SYS-OXYGEN` is registered. The inline definition is roughly the registry entry's purpose line plus the SDD's invariants plus the TDD's class signature, paraphrased into one paragraph.
- Bare cross-references (`"as defined previously"`, `"see ADR-0011"`, `"per the SDD"`) without copying the relevant excerpt.
- External URLs in the body that are load-bearing. The OpenAI Cookbook article that motivated this methodology, Unity manuals, vendor blog posts, GitHub issues — paraphrase inline; cite the source only as provenance, never as the referenced content itself.
- Adding a field to `Context and Orientation` that is shorter than the registry entry it transcribes.

Allowed:

- Citing an internal ID anywhere in the body provided `Context and Orientation` carries a sufficient inline definition (purpose + invariants + class signature for systems; purpose + payload for events; purpose + fields for configs).
- Artifact paths committed under the repo (`docs/levels/<scene>/img/*.png`, `src/Assets/_Editor/RuntimeReports/*.json`, `docs/plans/<plan>/runtime-probe.md`) as load-bearing references. They are the runtime-probe contract from `HARNESS-LOOP-RUNTIME-PROBE-BEFORE-COMPLETION` (ADR-0011) and inlining a screenshot or a JSON report into the ExecPlan body makes it less, not more, self-contained.
- External URLs as provenance footnotes (e.g., a Cinemachine 3 release-notes link cited to explain why a specific damping value was chosen, with the relevant fact paraphrased inline).

Term-of-art discipline rides on this rule (advisory, not separately enforced): every term that has an entry in `docs/registry/glossary.md` is inline-paraphrased the first time the ExecPlan uses it. Terms outside the glossary are defined in the agent's own words near first use. The reviewer flags egregious omissions as `EXEC-PLAN-SELF-CONTAINED` violations.

Cite: ADR-0012 §A; `docs/process/exec-plans.md` §5; OpenAI Cookbook, "Codex Exec Plans" (2026) — *"Treat the reader as a complete beginner to this repository: they have only the current working tree and the single ExecPlan file you provide."*

## `EXEC-PLAN-LIVING-DOCUMENT`

While the ExecPlan is `active`, the four mutable sections (`Progress`, `Surprises & Discoveries`, `Decision Log`, `Outcomes & Retrospective`) are updated *during* execution, at every commit that changes the underlying work. They are not written retroactively. Once the ExecPlan reaches `done`, the entire file becomes immutable except to mark `superseded`.

The mutability is load-bearing: the four sections together form the *execution record*. A `done` ExecPlan whose `Decision Log` is empty or whose `Surprises & Discoveries` was written in one pass at the end has lied about what happened.

Forbidden:

- Marking an ExecPlan `done` while its `Decision Log` is empty, its `Outcomes & Retrospective` is still the placeholder line, or its `Progress` has unchecked items that did land in the diff (forgot to tick) or checked items that did not land (jumped the gun).
- Editing a `done` ExecPlan to add, remove, or reword content in any section other than the frontmatter `superseded_by:` field.
- Batching `Progress`, `Surprises & Discoveries`, or `Decision Log` updates at the end of a multi-commit session. The four sections are updated *with the commit that produced the change*, not after.
- A commit on an `active` ExecPlan that changes substantive work in the repo but leaves the ExecPlan's four mutable sections untouched (the commit is invisible from the ExecPlan's perspective).

Allowed:

- Editing the eight immutable sections (Purpose / Context and Orientation / Plan of Work / Concrete Steps / Validation and Acceptance / Idempotence and Recovery / Artifacts and Notes / Interfaces and Dependencies) while `active` to correct errors or refine prose. The audit trail is git history, not in-document strikethroughs.
- Moving an `active` ExecPlan to `paused` and resuming later. `docs/plans/README.md` §Pause and resume applies verbatim; the frontmatter gains a `Paused at: <date>, last completed task: Task X` note and a one-paragraph handoff for whoever resumes. "Task X" references the last completed `Progress` checklist line by its `(timestamp)` prefix.
- Superseding a `done` ExecPlan with a later one. The earlier ExecPlan gains `superseded_by: EXEC-NNN` in its frontmatter and a link at the top of the body; the later ExecPlan declares `supersedes: EXEC-MMM`.

Cite: ADR-0012 §B; `docs/process/exec-plans.md` §4; OpenAI Cookbook, "Codex Exec Plans" (2026) — *"Every ExecPlan is a living document."*

## `EXEC-PLAN-OBSERVABLE-OUTCOME`

The `Validation and Acceptance` section is written as *observable behaviour*, not as *code presence*. An acceptance line that names a method, a class, or a test file is a violation; an acceptance line that names a runtime state, a user-visible output, or an observable side-effect is valid. The rule inherits from Anthropic's "stubs that appear functional in static review" observation: code presence is not behaviour, and ExecPlans are not done until behaviour is observed.

Forbidden:

- Acceptance lines of the form `"implement <method>"`, `"add <class>"`, `"write <test>"`, `"compile clean"`, `"the file <path> exists"`. These describe the artifact, not the behaviour.
- Acceptance phrased as a TODO list (`"finish the X system"`).
- Acceptance that defers verification (`"will be tested in a future plan"`, `"runtime smoke deferred"`). The runtime-probe artifact is mandatory per `HARNESS-LOOP-RUNTIME-PROBE-BEFORE-COMPLETION`; the ExecPlan cites the artifact in `Validation and Acceptance`.

Allowed:

- `"After holding `space` for 3 seconds in `SCENE-CORREDOR-C7`, the oxygen HUD bar fills to 100% and `EVT-oxygen-refilled` fires exactly once."`
- `"Entering Play Mode against `SCENE-CORREDOR-C7` produces zero console errors over 30 seconds of idle; the runtime-probe artifact at `docs/levels/corridor-c7/img/runtime-probe-EXEC-001-001.png` shows the player spawned at `PlayerSpawn` with the oxygen bar at 100%."`
- `"Running `LastBreath/Level/Validate Scene` against `SCENE-CORREDOR-C7` returns zero invariant errors. Screenshot of the report committed at `docs/levels/corridor-c7/img/validate-EXEC-001-001.png`."`

Cite: ADR-0012 §C; `docs/process/exec-plans.md` §3; OpenAI Cookbook, "Codex Exec Plans" (2026) — *"Every ExecPlan must produce a demonstrably working behavior, not merely code changes."*

## `EXEC-PLAN-MANDATORY-SECTIONS`

Every ExecPlan, at every status (`proposed`, `active`, `done`, `paused`, `abandoned`, `superseded`), has all twelve top-level headings present and in the order below. Headings match these names verbatim:

1. `## Purpose / Big Picture`
2. `## Progress`
3. `## Surprises & Discoveries`
4. `## Decision Log`
5. `## Outcomes & Retrospective`
6. `## Context and Orientation`
7. `## Plan of Work`
8. `## Concrete Steps`
9. `## Validation and Acceptance`
10. `## Idempotence and Recovery`
11. `## Artifacts and Notes`
12. `## Interfaces and Dependencies`

A `proposed` ExecPlan may have a `Progress` section with only the heading and no checklist items; it may have an `Outcomes & Retrospective` section with only the heading and the placeholder line `_To be written at done._`. What it may not do is omit, rename, or reorder any of the twelve. Subsections under each top-level heading are allowed and not constrained.

Forbidden:

- Omitting any of the twelve top-level headings.
- Renaming a heading (`"Plan"` instead of `"Plan of Work"`, `"Steps"` instead of `"Concrete Steps"`).
- Reordering the twelve. The order matches OpenAI's prescribed skeleton and is part of why an agent trained on that vocabulary recognises the surface.
- Adding a thirteenth top-level heading. Additional content is allowed only as subsections under one of the twelve.
- Leaving the body of a mandatory section entirely empty (no heading-only sections — even a placeholder line is required).

Allowed:

- Subsections under any of the twelve (`### Context and Orientation — SYS-OXYGEN snapshot`).
- Placeholder bodies on `proposed` ExecPlans (`Progress` with the heading and no items; `Outcomes & Retrospective` with `_To be written at done._`).
- Reusing the skeleton template at the top of `docs/process/exec-plans.md` as the starting point for every new ExecPlan.

Cite: ADR-0012 §D; `docs/process/exec-plans.md` §3.

## `EXEC-PLAN-FORMAT-DISCIPLINE`

Three grep-able bans on the ExecPlan body. The bans make the ExecPlan a sequential narrative an agent reads top to bottom, not a referenceable artifact it has to jump around inside.

Forbidden:

- Checklists (`- [ ]`, `- [x]`) appearing in any section other than `Progress`. The reviewer greps `grep -n -- '- \[' docs/exec-plans/EXEC-NNN-*.md` and verifies every match is inside the `Progress` section.
- Tables (lines beginning with `|`) appearing in any section other than `Progress`. The reviewer greps `grep -nE '^\|' docs/exec-plans/EXEC-NNN-*.md` and verifies every match is inside `Progress`.
- Nested triple-backtick code fences. Each fenced block opens with ` ``` ` and closes with the next ` ``` ` at the same indentation; fences inside fences break the parse and obscure the narrative.

Allowed:

- Prose lists with `-` or `*` bullets in any section (they are not checklists).
- Inline code spans with single backticks everywhere.
- Flat code fences in `Concrete Steps`, `Artifacts and Notes`, and elsewhere — provided no fence is nested.
- Tables in `Progress` (the rule does not ban tables there; `Progress` is the carve-out section for both checklists and tables).

Cite: ADR-0012 §E; `docs/process/exec-plans.md` §3 and §6.
