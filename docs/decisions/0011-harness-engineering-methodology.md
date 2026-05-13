---
id: ADR-0011-harness-engineering-methodology
type: decision
status: accepted
date: 2026-05-12
related: [ADR-0003, ADR-0007, ADR-0008, ADR-0009]
---

# ADR 0011: Harness-engineering methodology — review, runtime probe, and promotion as binding discipline

## Context

The repo has reached a particular shape: 10 ADRs, 6 scoped rule files, a stable-ID registry covering 9 ID classes, canonical process loops for asset-design and level-design, and a dozen plans of which 6 are `done` and 5 `proposed` (one `active`). What it does **not** have yet is C# under `src/Assets/_Project/Scripts/**`. The Unity project itself is bootstrap-pending (plan 008). The asset pipeline is in Wave A. Gameplay systems are designed in SDD and TDD but not implemented.

This pre-code moment is unusual and short-lived. Three recent industry articles converge on what to bake in *before* the first system lands:

- **OpenAI — "Harness engineering: leveraging Codex in an agent-first world"** (2026-02-11). A 7-engineer team built and shipped ~1M LoC across ~1,500 PRs over five months with zero hand-written code, starting from an empty git repository. Their core lesson: "the discipline shows up more in the scaffolding rather than the code." `AGENTS.md` is kept to ~100 lines as a table-of-contents; `docs/` is the system of record; plans are first-class artifacts; agent-to-agent review (a "Ralph Wiggum loop" of reviewer subagents iterating until clean) replaces human review on most PRs; recurring "doc-gardening" agents open fix-up PRs against drift; "golden principles" are enforced by custom linters whose error messages inject remediation context for the next agent run.
- **Martin Fowler — "Harness engineering for coding agents"** (2025). Formalises two axes of control: feedforward (guides) vs feedback (sensors), and computational (deterministic) vs inferential (LLM-as-judge). The article's load-bearing claim: "Separately, you get either an agent that keeps repeating the same mistakes (feedback-only) or an agent that encodes rules but never finds out whether they worked (feed-forward-only)." Names the **steering loop**: "Whenever an issue happens multiple times, the feedforward and feedback controls should be improved to make the issue less probable to occur in the future."
- **Anthropic — "Harness design for long-running application development"**. A planner / generator / evaluator separation outperformed solo agents on complex multi-hour builds. "Separating the agent doing the work from the agent judging it proves to be a strong lever." Context resets with file-based handoffs beat compaction. The evaluator drove the running application via Playwright MCP to catch integration bugs the generator missed in static review. The umbrella principle: "Every component in a harness encodes an assumption about what the model can't do on its own."

This repo already implements much of the recommended scaffolding:

- ✅ `AGENTS.md` as a map (under ~150 lines); `docs/` as the system of record; stable-ID registry in `architecture.yaml`.
- ✅ Generator / evaluator separation already in place: `gameplay-programmer` and `level-designer` author; `code-reviewer` is read-only.
- ✅ Plans as first-class artifacts in `docs/plans/`, with a lifecycle (`proposed | active | paused | done | superseded | abandoned`).
- ✅ Strong computational sensors: `check-art-sync.py`, `check-runtime-versions.py`, `check-manifest-schema.py`, `check-prefab-discipline.py`, `audit-md.py`. Pre-commit hook chain installed via `git config core.hooksPath scripts/git-hooks`.
- ✅ MCP boundaries with per-role allowlists (asset-designer has full `blender-mcp`; level-designer has the read-only subset).

The gaps that matter most given this project's stage:

- **The evaluator is not in the loop.** `/review-gameplay`, `/review-level`, `/review-asset` exist but are invoked by hand. Skipping them is one keystroke. This is Fowler's "feed-forward-only" failure in the making: rules without a sensor decay into shelfware. The agent-to-agent review loop that OpenAI relies on most heavily — and Anthropic's generator / evaluator separation — has the parts assembled here but the loop itself never runs unless a human types the slash command.
- **The agent cannot read its own gameplay output.** When gameplay C# lands, the agent will compose scenes via `unity-mcp` and write code via `Edit`, but it has no surface for entering Play Mode, capturing console errors, frame stats, or end-of-smoke state and verifying its change works. The Anthropic article's clearest lever — "the evaluator exercises running code, catching stubs that appear functional in static review" — has no equivalent here. The `unity-mcp` server is the authoring surface, not the runtime-introspection surface.
- **The steering loop has no skill.** When a `code-reviewer` comment or a recurring user observation surfaces a pattern, lifting it into a durable rule or linter happens by hand, by memory, when remembered. OpenAI's "when documentation falls short, we promote the rule into code" has no `/promote-feedback` here. Memory-based steering does not scale and the user has previously asked explicitly for agentic forcing over reminders (cf. ADR-0008 §Context item 2).

The pre-code moment is the right time to bake this discipline in. Authoring the methodology now means every plan written from this point — starting with `plan 008` (Unity bootstrap), continuing through `plan 012` (player controls) — is written **under** the discipline rather than retrofitted against it. Once gameplay C# starts landing, drift accumulates and retrofitting the harness costs more than authoring it.

Four authoring patterns were considered for this ADR:

- **Tooling-first.** Build the `Stop` hook, the `/play-and-observe` skill, and the `/promote-feedback` skill now, before there is gameplay code to harness. Rejected — the tools would be tested against an empty diff surface and the design would be guess-work. ADR-0009's "advisory drift script wired into SessionStart" is the precedent for the right shape: methodology first, tooling follows when the code arrives.
- **Methodology-first (chosen).** Author the ADR, the canonical loop doc, and the rule file now. Forcing is enforced by agent discipline (cited in plans) until the matching follow-up plans (014/015/016-spike) build the mechanical surfaces.
- **No-op / status quo.** Rely on the existing rule layer plus the user's discretion. Rejected — the user has already named this pattern as the failure mode ADR-0008 §Context item 2 was written to close.
- **Partial adoption (A only).** Adopt only the review loop now; defer runtime probe and promotion. Rejected because the three reinforce each other: a review pass without a runtime artifact misses Anthropic's "stubs that appear functional in static review" failure mode; a recurring observation surfaced by `code-reviewer` that has no promotion path becomes shelfware in conversation memory.

## Decision

Adopt **three harness-engineering disciplines as binding methodology**, codified as rules with stable IDs in `.claude/rules/harness-loop.md` and cross-referenced from `AGENTS.md`. The mechanical-forcing implementations are deferred to follow-up plans 014/015/016-spike; until those land, the rules are enforced by agent discipline and `code-reviewer` audit.

### A. `HARNESS-LOOP-REVIEW-BEFORE-COMPLETION`

A change is not considered complete until the matching `/review-*` skill has run and returned clean (or the user has explicitly recorded a skip note in `docs/registry/review-log.md`).

Routing by diff path:

- `src/Assets/_Project/Scripts/**` → `/review-gameplay`
- `src/Assets/Scenes/**.unity`, `src/Assets/_Project/Prefabs/Level/**`, `src/Assets/_Project/Config/Levels/**`, `docs/levels/**` → `/review-level`
- `art/**`, `src/Assets/_Project/Art/**` → **user-driven**, not forced by this ADR. The asset-design loop is the one ADR-0008 already binds; the user runs `/art-approval-queue` and optionally `/review-asset`. Forcing asset review through the same mechanism is out of scope of this ADR per the user's explicit choice.

Until PLAN-014 builds the `Stop`-hook router, the rule is enforced by agent discipline. After PLAN-014, the rule is enforced mechanically: the hook detects a gameplay or level diff and refuses to "finish" until the matching review skill has run.

### B. `HARNESS-LOOP-RUNTIME-PROBE-BEFORE-COMPLETION`

A gameplay change is not considered complete until a runtime-probe artifact records the change executing without console errors against the target acceptance criteria. The probe's exact shape is TBD by PLAN-016-spike.

The rule is **adopted now** so it shapes how every gameplay plan from this point is written: every gameplay plan must include a "Runtime verification" section naming the smoke path. Whether that section is filled by a manual `Play → check console → screenshot` ritual or by an automated `/play-and-observe` skill depends on PLAN-016-spike's outcome.

### D. `HARNESS-LOOP-PROMOTE-RECURRING-FEEDBACK`

When the same observation surfaces twice (the second time by `code-reviewer`, the user, `qa-tester`, or any other agent), it must be promoted before the current session closes. Promotion paths:

- **Rule promotion** — append a new rule with a stable `rule_id` to the appropriate `.claude/rules/<scope>.md`, cite an ADR, and register the `rule_id` in `architecture.yaml::rules`.
- **Linter promotion** — when mechanically checkable, scaffold a `scripts/check-<rule-id>.py`, wire it into `scripts/git-hooks/pre-commit`, and document the rule it enforces.
- **ADR promotion** — when the observation is a design decision rather than a coding constraint, open `docs/decisions/NNNN-<title>.md`.

Until PLAN-015 ships the `/promote-feedback` skill, this rule is enforced by agent discipline (the agent must remember to choose a path before closing). After PLAN-015, the skill provides the scaffolding plus the `rule_id` allocation.

### Steering convention

Per Anthropic's lesson: "every component in a harness encodes an assumption about what the model can't do on its own, and those assumptions are worth stress testing." When a new Claude / Codex / Gemini release lands, the next plan touching the harness must re-examine each forcing component by removing it once and measuring the cost. Components whose absence no longer hurts are retired. This is the steering loop applied to the harness itself.

## Alternatives considered

- **Tooling-first.** Reject; documented above. The pre-code moment is the wrong time to design tools against an empty surface.
- **No-op / status quo.** Reject; documented above. Memory-based steering is the failure mode this ADR closes.
- **Partial adoption (A only).** Reject; documented above. The three pillars reinforce each other.
- **Bundle gap C (quality dashboard + doc-gardening agent) into this ADR.** Reject for this round; revisit after PLAN-014 has run for several sessions and the review loop has produced enough observation data to grade. Premature dashboards report on noise. OpenAI's `QUALITY_SCORE.md` was an outcome of months of operation, not a kickoff artifact.
- **Force asset review through the same hook as gameplay and level.** Reject per user direction; the asset loop already has its own forcing surface (the `SessionStart` hook for pending approvals + `/art-approval-queue`) and the user has explicitly chosen to keep asset review manual.

## Consequences

- **Easy.** The methodology lands in three new files (`docs/decisions/0011-*.md`, `docs/process/harness-engineering.md`, `.claude/rules/harness-loop.md`) plus pointers in `AGENTS.md` and `CLAUDE.md`. Stable `rule_id`s are allocated in `architecture.yaml::rules`. Plans written from this point cite the rule IDs; the agent already reads `.claude/rules/**` at the start of every session.
- **Easy.** Every gameplay plan from `plan 008` onward inherits a "Runtime verification" section requirement. This is a one-line constraint in the rule file; the agent applies it without further infrastructure.
- **Hard.** Until PLAN-014 ships the `Stop`-hook router, every session closes by the agent invoking the correct `/review-*` skill **by discipline**. The discipline is enforced only by `code-reviewer` checking the session's commit messages and plan acceptance lists. Drift will happen; it is part of why PLAN-014 is queued.
- **Hard.** Until PLAN-016-spike resolves the Unity runtime-probe shape, the "Runtime verification" section in gameplay plans is filled by manual rituals (Play → console-clean → screenshots committed under the scene's `img/` folder, referenced from the session log). Acceptable for the early plans; bottleneck once the gameplay surface grows.
- **Accepted loss.** Memory-based promotion will leak some recurring observations until PLAN-015 ships `/promote-feedback`. The ADR commits to the discipline anyway; the cost is in the gap between adoption and tooling, not in the absence of either.
- **Mandatory acceptance** (no new tests in this ADR — the artifacts are documentation):
  - Every new rule_id (`HARNESS-LOOP-REVIEW-BEFORE-COMPLETION`, `HARNESS-LOOP-RUNTIME-PROBE-BEFORE-COMPLETION`, `HARNESS-LOOP-PROMOTE-RECURRING-FEEDBACK`) is registered in `architecture.yaml::rules` with `status: active`.
  - `scripts/audit-md.py --quiet` runs clean.
  - `AGENTS.md` stays under ~150 lines.
- **Mandatory rules** (`.claude/rules/harness-loop.md`):
  - `HARNESS-LOOP-REVIEW-BEFORE-COMPLETION`
  - `HARNESS-LOOP-RUNTIME-PROBE-BEFORE-COMPLETION`
  - `HARNESS-LOOP-PROMOTE-RECURRING-FEEDBACK`

## Notes

- The three follow-up plans (014/015/016-spike) are queued at `status: proposed` and stay there until the user prioritises them against `plan 008` (Unity bootstrap) and the existing chain.
- `docs/registry/review-log.md` is created as an append-only header by this ADR's plan; PLAN-014 starts writing to it.
- The `rules:` section added to `architecture.yaml` is a new top-level key; subsequent rule families (in any `.claude/rules/*.md`) will register their `rule_id`s there. Existing rule_ids (`ASSET-DESIGN-*`, `LEVEL-DESIGN-*`, `GAMEPLAY-CODE-*`, …) are **not** backfilled by this ADR — backfilling is a separate housekeeping plan; the registry's new section starts populated only by the four `HARNESS-LOOP-*` IDs.
- If the model used to drive sessions changes (Claude version bump, swap to Codex / Gemini), the next plan that touches the harness runs the steering check: remove one forcing component, observe whether quality drops, decide whether the component is still load-bearing.
