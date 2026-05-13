---
id: PLAN-015-promote-feedback-skill
type: plan
status: proposed
date: 2026-05-12
related: [ADR-0011, PLAN-013, PLAN-014]
owners: [systems-designer]
---

# PLAN-015 — Implement `/promote-feedback` skill (D)

## Context

ADR-0011 §D adopts `HARNESS-LOOP-PROMOTE-RECURRING-FEEDBACK` as binding methodology. Today the agent chooses a promotion path (rule / linter / ADR) by discipline. This plan provides the scaffolding, the `rule_id` allocator, and the optional linter-stub generator.

## Scope

- New skill `/promote-feedback` under `.claude/skills/promote-feedback/SKILL.md`:
  - Input: a freeform description of the recurring observation, optional `--from-reviewer` flag to scan the most recent `code-reviewer` output, optional `--scope` flag (`gameplay-code | level-design | asset-design | test-standards | design-docs | harness-loop`).
  - Asks the user which promotion path applies.
  - For rule promotion: invokes `scripts/allocate-rule-id.py` for a collision-safe ID, appends a Forbidden / Allowed / Cite block to the chosen rule file, updates `architecture.yaml::rules`.
  - For linter promotion: invokes `scripts/scaffold-linter.py`, scaffolds `scripts/check-<rule-id-kebab>.py` matching the existing check script shape (exit 0/1/2), and (with user confirmation) wires the script into `scripts/git-hooks/pre-commit` or the `SessionStart` hook.
  - For ADR promotion: opens a draft at `docs/decisions/NNNN-<title>.md` matching the existing ADR template.
- `scripts/allocate-rule-id.py`:
  - Reads `architecture.yaml::rules` and every `.claude/rules/*.md`, scans for existing IDs in the `{DOMAIN}-{NAME}` form.
  - Given a scope + a free-text observation, suggests a `rule_id` and verifies it does not collide.
- `scripts/scaffold-linter.py`:
  - Given a `rule_id` and a scope, writes `scripts/check-<rule-id-kebab>.py` from the template.
  - Asks where the script should fire (`pre-commit` blocking | `SessionStart` advisory) and updates `.claude/settings.json` or `scripts/git-hooks/pre-commit` accordingly.

## Out of scope

- A "doc-gardening" recurring agent (gap C from the brainstorm). Future plan.
- Auto-detecting recurring observations from session transcripts. The skill is human-invoked; PLAN-014's `Stop` hook produces the data, this plan turns the data into rules.

## Runtime verification

This is harness tooling, not gameplay. Verification:

- Fake a rule-promotion run end-to-end against a scratch copy of `architecture.yaml` and `.claude/rules/`; assert the new ID is registered and the rule block is appended.
- Fake a linter-promotion run; assert the new `check-*.py` script exists and the hook chain is updated.
- Fake an ADR-promotion run; assert the draft file exists at the next available `NNNN`.

## Acceptance

- [ ] `.claude/skills/promote-feedback/SKILL.md` exists and is discoverable in the skills listing.
- [ ] `scripts/allocate-rule-id.py` exists and passes its smoke fixtures.
- [ ] `scripts/scaffold-linter.py` exists and passes its smoke fixtures.
- [ ] The skill's three paths each have at least one end-to-end fixture test.
- [ ] `docs/process/harness-engineering.md` §5 stage 3 marked complete.

## Dependencies

PLAN-013 (rule definitions). Should land after PLAN-014 so the `Stop` hook is the source of recurring observations the skill promotes. Not strictly blocking — the skill can be used by hand before PLAN-014 ships.
