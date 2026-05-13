---
id: PLAN-013-harness-methodology
type: plan
status: done
date: 2026-05-12
related: [ADR-0011, ADR-0003, ADR-0007, ADR-0008, ADR-0009, PLAN-014, PLAN-015, PLAN-016]
owners: [systems-designer]
---

# PLAN-013 — Adopt harness-engineering methodology before first gameplay code lands

## Context

The project is at a pre-code moment: 10 ADRs, 6 scoped rule files, a stable-ID registry, canonical loops for asset-design and level-design, 12 plans authored (6 done, 1 active, 5 proposed), and no C# under `src/Assets/_Project/Scripts/**` yet. Three industry articles published in the last twelve months converge on what to scaffold before the first system lands: OpenAI's "Harness engineering" (Feb 2026), Martin Fowler's "Harness engineering for coding agents" (2025), and Anthropic's "Harness design for long-running application development."

The shared lessons: harness = everything around the model; feedforward and feedback must both fire or the loop decays; the steering loop ("if an issue happens twice, improve the controls") is the discipline that compounds; separating the generator from the evaluator is the single strongest reliability lever; the application itself must be legible to the agent for the evaluator to verify work; the repo is the system of record — what the agent can't read in-context effectively does not exist.

This repo already implements much of the scaffolding the articles recommend (see ADR-0011 §Context for the full mapping). The gaps that matter now:

- The evaluator (`code-reviewer`) exists but is invoked by hand. Skipping it is one keystroke.
- The agent will have no way to read Unity runtime output once gameplay C# lands.
- Recurring observations have no promotion path to durable rules or linters.

The pre-code moment is the right time to bake the discipline in. After this plan, every plan from `plan 008` (Unity bootstrap) onward is written **under** the methodology rather than retrofitted against it.

## Decision

Author the methodology as documentation; defer the mechanical-forcing implementations to follow-up plans. Adopt three harness-engineering disciplines:

- **A. `HARNESS-LOOP-REVIEW-BEFORE-COMPLETION`** — gameplay and level diffs gated by the matching `/review-*` skill; asset diffs remain user-driven via the existing `SessionStart` + `/art-approval-queue` surface.
- **B. `HARNESS-LOOP-RUNTIME-PROBE-BEFORE-COMPLETION`** — gameplay changes must reference a runtime-probe artifact before claiming done; artifact shape TBD by PLAN-016-spike (manual Play-Mode ritual in the interim).
- **D. `HARNESS-LOOP-PROMOTE-RECURRING-FEEDBACK`** — recurring observations promoted to a rule, a linter, or an ADR before the session closes.

Full rationale: `docs/decisions/0011-harness-engineering-methodology.md`. Canonical loop: `docs/process/harness-engineering.md`. Rule definitions: `.claude/rules/harness-loop.md`.

## Owners

- `systems-designer` — owns the ADR, the canonical loop doc, and the registry updates.
- `code-reviewer` — audits the artifacts at landing time.

No code is written by this plan. The three follow-up plans (014/015/016-spike) own the mechanical surfaces.

## Tasks

- [x] Write `docs/decisions/0011-harness-engineering-methodology.md` (ADR-0011).
- [x] Write `docs/process/harness-engineering.md` (canonical loop).
- [x] Write `.claude/rules/harness-loop.md` (three rules: review, runtime-probe, promotion).
- [x] Add `rules:` top-level section to `docs/registry/architecture.yaml`; register the three new `rule_id`s.
- [x] Update `AGENTS.md` — one line under `§Global rules`, one line under `§Required reading`.
- [x] Update `CLAUDE.md` — one-line pointer to the new rule file.
- [x] Update `.claude/rules/README.md` — add `harness-loop.md` to the rule-file table; backfill the missing rows for `asset-design.md` and `level-design.md` (out-of-scope drift caught in transit).
- [x] Write `docs/registry/review-log.md` skeleton (empty append-only header).
- [x] Write `docs/plans/014-enforced-review-loop.md` stub at `status: proposed`.
- [x] Write `docs/plans/015-promote-feedback-skill.md` stub at `status: proposed`.
- [x] Write `docs/plans/016-spike-runtime-probe.md` stub at `status: proposed`.
- [x] Update `docs/plans/README.md` — add the four new plan index rows and update the execution-order note.

## Acceptance

- [x] `scripts/audit-md.py --quiet` returns 0 (no orphans introduced; no broken refs).
- [x] `scripts/check-runtime-versions.py --quiet` returns 0 or `skip` (tooling block untouched).
- [x] `AGENTS.md` stays under 150 lines after the additions (currently 134 lines).
- [x] Every new `rule_id` (`HARNESS-LOOP-REVIEW-BEFORE-COMPLETION`, `HARNESS-LOOP-RUNTIME-PROBE-BEFORE-COMPLETION`, `HARNESS-LOOP-PROMOTE-RECURRING-FEEDBACK`) is present in `architecture.yaml::rules` with `status: active`.
- [x] Cross-references resolve: every cite in the new rule file points to a section that exists in the ADR or the process doc; every section in the process doc is referenced from the rule file or the ADR. (Verified via `audit-md.py` clean broken-refs count.)
- [x] `/review-gameplay` (advisory) loads the new rule file without error on its next run. **Deferred validation**: this plan's diff is documentation-only and falls outside the gameplay / level routing scopes; per `HARNESS-LOOP-REVIEW-BEFORE-COMPLETION` §Allowed, the skill does not need to run for this diff. The first invocation **under** the new methodology will be the next gameplay or level plan (PLAN-008, PLAN-009, or PLAN-012).

## Runtime verification

Not applicable to this plan — there is no runtime behaviour to verify (documentation-only diff). The `HARNESS-LOOP-RUNTIME-PROBE-BEFORE-COMPLETION` rule explicitly allows this when the change does not alter runtime behaviour. The first plan that **does** alter runtime behaviour (plan 008 Unity bootstrap, or whichever lands first) will be the first one to fill its `## Runtime verification` section under the new methodology.

## Out of scope

- No `Stop` hook (PLAN-014).
- No `/promote-feedback` skill (PLAN-015).
- No Unity runtime probe (PLAN-016-spike + follow-up plan).
- No quality dashboard, no doc-gardening agent. Revisit after PLAN-014 has produced reviewer-decision data to grade.
- No backfill of existing rule_ids (`ASSET-DESIGN-*`, `LEVEL-DESIGN-*`, `GAMEPLAY-CODE-*`, …) into the new `rules:` registry section. Backfilling is its own housekeeping plan.
- No changes to existing review skills (`/review-gameplay`, `/review-level`, `/review-asset`). PLAN-014 changes **when** they run; this plan changes **what context they read** (the new rule file is auto-discovered).

## Follow-ups (queued, not executed by this plan)

- **PLAN-014** — Implement the enforced review loop. `Stop` hook routes by diff path; `scripts/harness/review-router.py` selects `/review-gameplay` or `/review-level`; explicit skip path via `LASTBREATH_SKIP_REVIEW=1` env var logged to `docs/registry/review-log.md`.
- **PLAN-015** — Implement the `/promote-feedback` skill. Three-path promotion (rule / linter / ADR); `scripts/allocate-rule-id.py` for collision-safe ID allocation; optional `scripts/scaffold-linter.py` for the mechanical-check stub.
- **PLAN-016-spike** — Unity runtime-probe feasibility. 0.5–1 day timeboxed spike: inventory `unity-mcp` verbs for Play Mode lifecycle + Console reads; outcome documented in `docs/specs/016-runtime-probe-spike.md`; full implementation plan opens after.

## Notes

- The asset-design loop is intentionally **not** routed through the new review hook. ADR-0011 §A makes the exclusion explicit. The existing `SessionStart` pending-approval surface plus `/art-approval-queue` plus `/review-asset` (manual) already covers asset-design forcing.
- The `rules:` block added to `architecture.yaml` is **new**. Subsequent rule families register their `rule_id`s there; this plan populates it only with the four `HARNESS-LOOP-*` IDs. Backfilling existing rule families is a separate housekeeping plan, not this one.
- The methodology binds future plan writers (and the agent that writes plans on their behalf): every gameplay plan from this point includes a `## Runtime verification` section. Existing proposed plans (008/009/010/011/012) will pick the section up the next time they are touched.
