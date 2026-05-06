---
id: ADR-0003-soft-reviewer-enforcement
type: decision
status: accepted
date: 2026-05-05
related: [PLAN-002, SPEC-AI-WORKFLOW-2026-05-05]
---

# ADR 0003: Reviewer enforcement is soft (role-spec only, no hooks)

## Context

The `code-reviewer` subagent (added in plan 002) is supposed to run at the end of every gameplay change. The natural question is *how* to make sure it actually runs — what stops the `gameplay-programmer` from declaring done without dispatching the reviewer?

Two enforcement levels were on the table:

- **Soft:** the role spec in `.claude/agents/gameplay-programmer.md` requires the dispatch ("Failure to dispatch the reviewer = failure to ship"). Compliance depends on the agent honouring its own role contract.
- **Hard:** a `SessionEnd` hook (or PreToolUse hook on commit operations) configured in `.claude/settings.json` that scans the transcript for an unmatched "declaring done" without a preceding `code-reviewer` invocation, and blocks. Compliance is mechanical.

Hooks have a real cost: they need to be written, maintained, and reasoned about when they misbehave. They can produce confusing failure modes ("why is my commit blocked?") that take longer to diagnose than the bug they're catching. For a solo-dev PoC with no code yet, the hook is enforcement against a hypothetical attacker (a future agent or future-self that decides to skip review) for whom no historical evidence of misbehaviour exists.

## Decision

**Enforcement is soft for now. No hooks are configured.** The reviewer dispatch is required by `.claude/agents/gameplay-programmer.md` and by `docs/superpowers/specs/2026-05-05-ai-augmented-workflow-design.md` §5.5. The plan-adherence "no plan + multi-file change" rule is also soft: the reviewer flags it as a `warning`, and the calling agent must acknowledge the warning explicitly in its done-statement, but it does not block.

This decision is explicitly **revisitable**. After the first three Phase-1 plans (`SYS-OXYGEN`, `SYS-AGITATION`, `SYS-PRESENCE`) execute under soft enforcement, audit whether any of them shipped without a reviewer pass. If yes, harden to hooks. If no, soft enforcement is working and stays.

## Alternatives considered

- **Hooks now (hard enforcement).** *Rejected because* the cost of writing, debugging, and maintaining the hook outweighs the protection it provides at this stage of the project. Hooks are best added when there is evidence of the failure mode they prevent.
- **CI-based enforcement.** A GitHub Actions workflow that runs the reviewer over the diff and fails the merge. *Rejected for now because* (a) there is no Unity batch-mode build yet, (b) the project has no remote, (c) CI infra is its own non-trivial setup. Worth revisiting once Unity is up and the project has a remote.
- **Manual gate.** The user dispatches the reviewer themselves at the end of each task. *Rejected because* it puts the responsibility on the slowest, most distractable component (the human) instead of the agent that just finished the work.

## Consequences

- **Easy:** no hook infrastructure to maintain; the rule lives in one place (`gameplay-programmer.md`); changes to enforcement policy are one file edit.
- **Hard:** if the agent silently skips the dispatch, nothing catches it except the user's eyes. Mitigation: the user occasionally runs `/review-gameplay --strict` on the latest commit to verify reviewer output exists in the transcript.
- **Accepted loss:** the project relies on the agent's honesty about following its role spec. If that breaks, drift accumulates until the next manual review catches it.

## Notes

Revisit conditions:

1. **After 3 Phase-1 plans.** Audit reviewer-dispatch presence in the transcript history. If clean, stay soft.
2. **First time a reviewer-skip ships a regression.** Harden immediately.
3. **When CI lands.** Move enforcement there even if soft is working.

A future ADR (e.g., ADR-NNNN-harden-reviewer-enforcement) will supersede this one when those conditions are met.
