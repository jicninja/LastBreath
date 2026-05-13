# Rules — Harness loop

Cross-cutting rules scoped by **moment of completion**, not by path. The other rule files in `.claude/rules/` are scoped by where you are writing (gameplay, level, asset, tests, design docs); these rules are scoped by when you are about to declare a change "done." Owned jointly by every authoring role (`gameplay-programmer`, `level-designer`, `asset-designer`) and audited by `code-reviewer`.

Rationale: ADR-0011. Canonical loop: `docs/process/harness-engineering.md`. Industry references: OpenAI "Harness engineering" (2026-02), Martin Fowler "Harness engineering for coding agents" (2025), Anthropic "Harness design for long-running application development."

The three rules below are enforced today by **agent discipline** and `code-reviewer` audit. The matching mechanical surfaces ship in PLAN-014 (`Stop`-hook router), PLAN-015 (`/promote-feedback` skill), and PLAN-016-spike (Unity runtime probe). Until those land, the discipline lives in the agent and the citations live in the commit messages.

## `HARNESS-LOOP-REVIEW-BEFORE-COMPLETION`

A change is not considered complete until the matching `/review-*` skill has run and returned clean (or the user has explicitly recorded a skip note in `docs/registry/review-log.md`). Routing by diff path:

- Diff touches `src/Assets/_Project/Scripts/**` → `/review-gameplay` must run.
- Diff touches `src/Assets/Scenes/**.unity`, `src/Assets/_Project/Prefabs/Level/**`, `src/Assets/_Project/Config/Levels/**`, or `docs/levels/**` → `/review-level` must run.
- Diff spans both scopes → both review skills run sequentially.
- Diff touches only `art/**`, `src/Assets/_Project/Art/**`, or asset-pipeline configs → **out of scope of this rule**; the asset-design loop has its own forcing surface (`SessionStart` hook + `/art-approval-queue`). The user may still invoke `/review-asset` manually.

Forbidden:

- Claiming a gameplay or level change "done", merging it, closing the session, or moving the plan from `active` to `done` without invoking the matching `/review-*` skill in this session's transcript.
- Bypassing the review with a skip that is not recorded in `docs/registry/review-log.md` with the ISO timestamp, the diff scope, the reason, and the reviewer's last decision (if any).
- Citing a `/review-*` run from a previous session as if it applied to the current diff. Each session that produces a gameplay or level diff runs its own review pass.

Allowed:

- A session whose diff is documentation-only and falls outside the routed scopes (e.g., a `docs/process/*.md` edit, a `docs/decisions/NNNN-*.md` edit) closes without invoking `/review-*`. The reviewer reads docs diffs without requiring the skill dispatch.
- An explicit user skip with a `review-log.md` entry. The skip log exists so skips are visible; using it is allowed.
- A multi-step session that runs `/review-gameplay` mid-session against a partial diff, addresses the fix list, and runs again at the end. The end-of-session run is the load-bearing one for this rule.

Cite: ADR-0011 §A; `docs/process/harness-engineering.md` §3.A.

## `HARNESS-LOOP-RUNTIME-PROBE-BEFORE-COMPLETION`

A gameplay change is not considered complete until a runtime-probe artifact records the change executing without console errors against the target acceptance criteria.

Until PLAN-016-spike resolves the automated probe shape, the artifact is the manual Play-Mode ritual documented in `docs/process/harness-engineering.md` §3.B: enter Play Mode against the target scene, observe the console for the smoke path, capture end-state, commit the screenshot or note under `docs/levels/<scene>/img/runtime-probe-*.png` or `docs/plans/<plan>/runtime-probe.md`, and cite it from the plan's acceptance section.

After PLAN-016-spike's follow-up plan ships, the artifact is the JSON report at `src/Assets/_Editor/RuntimeReports/<timestamp>.json` produced by `/play-and-observe` (or by an Editor MenuItem driven from `unity-mcp`, depending on the spike outcome).

Forbidden:

- Marking a gameplay plan `done` without a runtime-probe artifact referenced from its acceptance section.
- Opening a new gameplay plan that lacks a `## Runtime verification` section. The plan must declare the smoke path **before** the agent starts writing C#.
- Citing a runtime-probe artifact from a previous, unrelated session as if it covered the current change. Each gameplay change produces its own probe artifact.
- Skipping the probe because "the change is small / cosmetic." Cosmetic gameplay changes are the failure mode Anthropic's article specifically calls out — stubs that appear functional in static review.

Allowed:

- A gameplay plan whose only change is a comment, a docstring, or a `[SerializeField]` tooltip refactor. These do not alter runtime behaviour; the rule does not apply.
- The `## Runtime verification` section may name a smoke path that is manual today and automated after PLAN-016-spike's follow-up plan. The section is required; its exact contents follow the tooling stage.
- A plan that explicitly defers runtime verification to a later integration plan, **provided** the deferral is named in the plan's acceptance section ("Runtime verification is covered by PLAN-NNN's integration smoke") and the later plan exists.

Cite: ADR-0011 §B; `docs/process/harness-engineering.md` §3.B.

## `HARNESS-LOOP-PROMOTE-RECURRING-FEEDBACK`

When the same observation surfaces twice (the second time by `code-reviewer`, the user, `qa-tester`, or any other agent), it must be promoted before the current session closes. The three promotion paths:

- **Rule promotion** — append a new rule with a stable `rule_id` to the appropriate `.claude/rules/<scope>.md`, allocate the `rule_id` following the `{DOMAIN}-{NAME-IN-UPPER-KEBAB}` convention, register it in `architecture.yaml::rules` with `status: active` and a one-line `purpose`, and cite the relevant ADR if one exists.
- **Linter promotion** — when the rule is mechanically checkable, scaffold `scripts/check-<rule-id-kebab>.py` matching the existing `check-*.py` exit-code convention (0 clean / 1 violation / 2 infrastructure error). Wire it into `scripts/git-hooks/pre-commit` if violations should block; into `SessionStart` if advisory.
- **ADR promotion** — when the observation is a design decision rather than a coding constraint, open `docs/decisions/NNNN-<title>.md` following the existing ADR format. Rules and linters may then derive from the ADR.

Forbidden:

- Closing a session that surfaced a recurring observation without choosing a promotion path. "We should remember to do X next time" is not a promotion.
- Promoting to a `rule_id` that collides with an existing one in `architecture.yaml::rules`. Allocation is deterministic by inspection until PLAN-015 ships the allocator script.
- Promoting to a linter without wiring it into either `pre-commit` (blocking) or `SessionStart` (advisory). A linter that no surface invokes is shelfware.
- Treating the second surfacing as "the same as the first" and not counting it. The discipline is: first surfacing is noted, second surfacing is the trigger.

Allowed:

- Promoting in either of two granularities: a single new rule or a new ADR plus a derived rule. Either is a valid path; the choice depends on whether the observation is a coding constraint (rule) or a decision (ADR).
- Deferring the linter scaffolding to a follow-up plan when the rule is genuinely useful but the mechanical check is non-trivial (parser-level, AST-level). The rule lands now; the linter lands in the named plan; the session that did the promotion names both.
- A promotion that turns an advisory rule into a blocking one (move the check from `SessionStart` to `pre-commit`) when the observation count justifies the escalation. This is itself a steering-loop event.

Cite: ADR-0011 §D; `docs/process/harness-engineering.md` §3.D.
