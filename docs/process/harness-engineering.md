---
id: PROCESS-HARNESS-ENGINEERING
type: reference
layer: process
status: active
related: [ADR-0011, ADR-0003, ADR-0007, ADR-0008, ADR-0009]
---

# Harness engineering — the steering loop

Canonical workflow for keeping the agent's output reliable as code starts landing. Read end-to-end the first time, then jump to the section you need.

Decision: `docs/decisions/0011-harness-engineering-methodology.md`. Rules: `.claude/rules/harness-loop.md`. The three follow-up plans that turn each loop from agent-discipline into mechanical forcing: PLAN-014 (enforced review), PLAN-015 (`/promote-feedback` skill), PLAN-016-spike (Unity runtime probe).

## 1. Purpose

A harness is everything around the model: guides that steer it before it acts, sensors that catch it after, and the loop that closes between them. Three sources converge on the load-bearing claims:

- "Agent = Model + Harness." (Fowler)
- "Every component in a harness encodes an assumption about what the model can't do on its own." (Anthropic)
- "The discipline shows up more in the scaffolding rather than the code." (OpenAI)

This project already has the **feedforward** layer (`AGENTS.md`, `.claude/rules/`, `docs/process/`, ADRs, registry IDs) and a strong **computational sensor** layer (`scripts/check-*.py`, pre-commit hook chain, `SessionStart` drift checks). What it does not yet have is the **inferential sensor** in the loop — `code-reviewer` exists but is invoked by hand — nor a **runtime-introspection surface** for the Unity game once gameplay code lands, nor a **promotion path** that closes the steering loop when an observation repeats. ADR-0011 names these three gaps and adopts them as binding methodology before the first gameplay code arrives. This doc is the canonical loop that the rules in `.claude/rules/harness-loop.md` reference.

## 2. Glossary alignment

The articles use different vocabulary than this repo. Mapping for clarity:

| Article term | This repo's term |
|---|---|
| Guide (Fowler) | Rule in `.claude/rules/`, canonical loop in `docs/process/`, ADR in `docs/decisions/` |
| Computational sensor (Fowler) | Validator script in `scripts/` (`check-art-sync.py`, `check-runtime-versions.py`, …) |
| Inferential sensor (Fowler) | `code-reviewer` subagent + `/review-gameplay`, `/review-level`, `/review-asset` |
| Generator (Anthropic) | `gameplay-programmer`, `level-designer`, `asset-designer` |
| Evaluator (Anthropic) | `code-reviewer` (read-only) and `qa-tester` |
| Planner (Anthropic) | `systems-designer`, `game-designer`; the plan files in `docs/plans/` |
| Ralph Wiggum loop (OpenAI) | The bounce-until-clean cycle between a generator and `code-reviewer` |
| Doc-gardening agent (OpenAI) | Not implemented (see PLAN-014's discussion of post-loop quality work) |

## 3. The three loops

Three rule families in `.claude/rules/harness-loop.md`. Each one names a moment of completion and the artifact that proves the moment was reached.

### 3.A — Review loop (`HARNESS-LOOP-REVIEW-BEFORE-COMPLETION`)

**When it fires.** A session about to close that produced a diff touching one or more of:

- `src/Assets/_Project/Scripts/**` → routes to `/review-gameplay`
- `src/Assets/Scenes/**.unity`, `src/Assets/_Project/Prefabs/Level/**`, `src/Assets/_Project/Config/Levels/**`, `docs/levels/**` → routes to `/review-level`

A diff that spans both scopes routes through both review skills sequentially.

**What "clean" means.** The reviewer either returns "clean" (no rule violations, no `block` notes) or returns a fix list. On a fix list, the generator addresses each item and the loop re-runs. The loop terminates on `clean` or on an explicit user skip recorded in `docs/registry/review-log.md`.

**Skip path.** The user (not the agent) writes a one-line entry to `docs/registry/review-log.md` with the ISO timestamp, the diff scope, the reason, and the reviewer's last decision (if any). Skips exist; they are visible.

**Asset-design diffs are not routed.** Per ADR-0011 §A, asset diffs go through the existing `/art-approval-queue` + (optionally) `/review-asset`. This loop is scoped to gameplay and level.

**Until PLAN-014 lands.** The agent invokes `/review-*` by discipline at the end of the session. The session's commit message names the review that ran. `code-reviewer` checks for the citation in the next session's audit.

**After PLAN-014 lands.** A `Stop` hook in `.claude/settings.json` runs `scripts/harness/review-router.py`, which inspects the staged + working-tree diff against the routing table above and refuses to "finish" until the matching review skill has run with a clean return. The override remains the explicit skip-log entry.

### 3.B — Runtime-probe loop (`HARNESS-LOOP-RUNTIME-PROBE-BEFORE-COMPLETION`)

**When it fires.** A gameplay change about to be claimed "done" — that is, a session that produced a diff under `src/Assets/_Project/Scripts/**` *and* expects the change to alter runtime behaviour (a new system, a tuned formula, a wired interactable, a new event publisher).

**What the artifact is, until PLAN-016-spike.** A manual ritual:

1. The user enters Play Mode against the target scene (or, if no Unity project exists yet, against the smoke scene the active plan names).
2. The console is observed for the duration of the smoke path. Zero errors and zero warnings unrelated to the change is the bar.
3. The end-state of the relevant systems is captured (a screenshot, a brief paragraph, or a copy of the inspector values for the affected components).
4. The artifact is committed under `docs/levels/<scene>/img/runtime-probe-<plan>-<NNN>.png` or `docs/plans/<plan>/runtime-probe.md` and cited from the plan's acceptance section.

**What the artifact will be, after PLAN-016-spike.** Depending on the spike outcome, one of:

- A `/play-and-observe` skill that drives Play Mode via `unity-mcp`, captures Console output, frame budget samples, and end-state, and writes a JSON to `src/Assets/_Editor/RuntimeReports/<timestamp>.json` consumable by the agent.
- An Editor MenuItem `Tools/Last Breath/Runtime Probe/Run Smoke` invoked via `unity-mcp.execute_menu_item`, producing the same JSON.

The plan whose work is being verified cites the JSON path in its acceptance.

**Plan-template consequence.** Every gameplay plan written from ADR-0011's adoption onward includes a `## Runtime verification` section that names the smoke path. This is a planning-time constraint, not a runtime-time constraint — the plan declares what "running" means before the agent starts writing C#.

### 3.D — Promotion loop (`HARNESS-LOOP-PROMOTE-RECURRING-FEEDBACK`)

**When it fires.** Twice. The first surfacing of an observation is noted (in a session log, a code-review comment, a user remark). The second surfacing triggers the promotion: the observation is now a pattern, and the next session closes only after the observation lives in a durable surface.

**The three promotion paths.**

- **Rule promotion.** The observation becomes a `Forbidden / Allowed / Cite` block in the appropriate `.claude/rules/<scope>.md`. A new `rule_id` is allocated following the `{DOMAIN}-{NAME-IN-UPPER-KEBAB}` convention. The `rule_id` is registered in `architecture.yaml::rules` with `status: active`, a one-line `purpose`, and a `cite_adr` field if the rule has architectural backing. `code-reviewer` picks the rule up on its next pass.
- **Linter promotion.** If the rule is mechanically checkable (a path constraint, a string-literal ban, a schema requirement), scaffold `scripts/check-<rule-id-kebab>.py` with the same shape as the existing `check-*.py` scripts: exit 0 on clean, 1 on violation, 2 on infrastructure error. Add the script to the `pre-commit` hook chain when the violation would block, or to the `SessionStart` hook when the violation is advisory.
- **ADR promotion.** If the observation is a design decision rather than a coding constraint (a new role boundary, a new MCP allowlist, a new tooling pin), open `docs/decisions/NNNN-<title>.md` following the existing ADR format. Rules and linters may then derive from the ADR.

**`rule_id` allocation.** Until PLAN-015 ships the `/promote-feedback` skill, allocation is by inspection: read `architecture.yaml::rules` and the existing `.claude/rules/*.md` files, pick the next `{DOMAIN}-{NAME}` that does not collide. The skill will provide a deterministic allocator at `scripts/allocate-rule-id.py`.

**Linter wiring.** A new mechanical check is added to `scripts/git-hooks/pre-commit` only when the rule's violations should block the commit; otherwise the check fires from `SessionStart` and reports advisory. ADR-0003's "soft enforcement" stance applies — pre-commit blocking is reserved for rules with concrete user pain behind them (the asset pipeline is the precedent).

**Until PLAN-015 lands.** The agent chooses a promotion path by discipline before closing a session that surfaced a recurring observation. The session log (or the plan's notes) names the promotion: "Promoted to rule `RULE-ID` / linter `script.py` / ADR-NNNN."

## 4. The end-of-session ritual

Adapt the existing `level-design-session` and `asset-design-session` rituals to add the harness checks. Every session ends in this order:

1. **Diff scan.** What did this session change? Group by path: gameplay code, level composition, asset staging, docs only.
2. **Run the matching `/review-*` skill** for each gameplay or level scope touched. Wait for `clean`. If the reviewer returns a fix list, address it and re-run; loop until `clean` or until the user records a skip in `docs/registry/review-log.md`.
3. **Capture the runtime probe** if the session changed gameplay behaviour. Until PLAN-016-spike, this is the manual Play-Mode ritual described in §3.B. Commit the artifact alongside the rest of the change.
4. **Promote recurring observations.** If the session surfaced an observation that has now repeated, choose a promotion path (rule, linter, ADR) and execute it before the session closes. Note the promotion in the session log or the plan's notes.
5. **Update the session log** (for level-design and asset-design loops, the existing `sessions/session-NNNN.md` or the manifest's `notes:` field). For gameplay-code sessions, the plan's progress section is the session log.
6. **Commit the bundle.** One commit per coherent change. The commit message names the review skill that ran, the runtime-probe artifact (if any), and the promotion target (if any).

This is the same shape as `docs/process/level-design.md` §4 and `docs/process/asset-design.md` §4, extended with the three harness checks. The existing session-loop skills (`level-design-session`, `asset-design-session`) will incorporate the review and runtime-probe steps as part of PLAN-014's rollout.

## 5. Adoption stages

The methodology rolls out in four stages. The first is this ADR; the rest are follow-up plans.

| Stage | Trigger | Surface |
|---|---|---|
| 1. Methodology adopted (this plan, PLAN-013) | ADR-0011 + rule file + canonical loop committed | Agent discipline; `code-reviewer` audits session logs and plan acceptances. |
| 2. Enforced review loop (PLAN-014) | `Stop` hook + `scripts/harness/review-router.py` shipped | Mechanical forcing on session close; explicit skip via `docs/registry/review-log.md`. |
| 3. Promotion skill (PLAN-015) | `/promote-feedback` skill + `scripts/allocate-rule-id.py` shipped | Mechanical scaffolding for rule and linter promotion. |
| 4. Runtime probe (PLAN-016-spike → follow-up plan) | Spike outcome documented; full plan opened | `/play-and-observe` skill or Editor MenuItem + JSON probe artifact. |

The order matters. Stage 2 produces the data (recurring reviewer observations) that stage 3 promotes. Stage 4 is the heaviest investment and is gated on a spike because the cost depends on what `unity-mcp` already exposes.

## 6. Steering the harness itself

Per Anthropic: "every component in a harness encodes an assumption about what the model can't do on its own, and those assumptions are worth stress testing." When the model used to drive sessions changes (a Claude version bump, a swap to Codex or Gemini, a Sonnet→Opus rotation), the next plan that touches the harness runs the steering check:

1. Pick one forcing component (a hook, a rule, a sensor).
2. Disable it for one session.
3. Observe whether the output quality drops.
4. Decide whether the component is still load-bearing.

Components whose absence no longer hurts are retired (their rule_id moves to `status: deprecated` and the entry stays; the hook is removed from `.claude/settings.json`). Components whose absence hurts more than before are reinforced (move from advisory to blocking, add tests, surface more aggressively).

This is the steering loop applied to the harness itself. The articles agree on the principle but only Anthropic frames it as a recurring discipline; this ADR adopts it as a project-level rule.

## 7. What this process is NOT for

- **Not a quality dashboard.** ADR-0011 explicitly defers the "harness-coverage metric" idea Fowler calls out as a research gap and OpenAI implements as `QUALITY_SCORE.md`. Premature dashboards report on noise. Revisit after PLAN-014 has produced enough reviewer-decision data to grade.
- **Not a doc-gardening agent.** `scripts/audit-md.py` already detects orphans and broken refs on demand. A recurring doc-gardener is a future investment, plausibly after the project has more docs than scripts can catch by inspection.
- **Not a replacement for plans.** Plans are still where multi-class or multi-doc changes are designed before code lands. The harness loop runs **around** the work the plan describes, not instead of it.
- **Not an asset-design forcing surface.** The asset loop has its own forcing (`SessionStart` pending-approval count, `/art-approval-queue`). ADR-0011 §A explicitly excludes asset diffs from the review-loop routing.

## 8. Acceptance checklist for an ADR-0011 plan-of-record

What `code-reviewer` looks for on the methodology-adoption diff (PLAN-013).

- [ ] `docs/decisions/0011-harness-engineering-methodology.md` exists with the standard ADR frontmatter and the seven sections of the existing ADR format.
- [ ] `docs/process/harness-engineering.md` (this file) exists with the canonical loop layout matching the existing process docs.
- [ ] `.claude/rules/harness-loop.md` exists with three rules: `HARNESS-LOOP-REVIEW-BEFORE-COMPLETION`, `HARNESS-LOOP-RUNTIME-PROBE-BEFORE-COMPLETION`, `HARNESS-LOOP-PROMOTE-RECURRING-FEEDBACK`. Each has Forbidden / Allowed / Cite blocks.
- [ ] `docs/registry/architecture.yaml` has a `rules:` top-level section that registers the three new `rule_id`s with `status: active`.
- [ ] `AGENTS.md` adds a one-line entry under `§Global rules` and a one-line entry under `§Required reading`. The file stays under ~150 lines.
- [ ] `CLAUDE.md` adds a one-line pointer to `.claude/rules/harness-loop.md` (ADR-0011).
- [ ] `.claude/rules/README.md` adds `harness-loop.md` to the rules-file table.
- [ ] `docs/plans/README.md` indexes PLAN-013 (this plan, `done`) and PLAN-014 / PLAN-015 / PLAN-016-spike (`proposed`).
- [ ] `docs/registry/review-log.md` is created as an empty append-only header.
- [ ] `scripts/audit-md.py --quiet` returns 0.
- [ ] `scripts/check-runtime-versions.py --quiet` still returns 0 (or `skip`).
