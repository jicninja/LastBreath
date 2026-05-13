---
id: PLAN-014-enforced-review-loop
type: plan
status: proposed
date: 2026-05-12
related: [ADR-0011, PLAN-013, PLAN-015]
owners: [systems-designer, gameplay-programmer]
---

# PLAN-014 — Implement the enforced review loop (A)

## Context

ADR-0011 §A adopts `HARNESS-LOOP-REVIEW-BEFORE-COMPLETION` as binding methodology. Today the rule is enforced by agent discipline only — the agent invokes `/review-gameplay` or `/review-level` at the end of a session by remembering to. Skipping the review is one keystroke. This plan replaces the discipline with mechanical forcing.

## Scope

- Add a `Stop` hook in `.claude/settings.json` that runs `scripts/harness/review-router.py`.
- Implement `scripts/harness/review-router.py`:
  - Inspect the staged + working-tree diff against the routing table in ADR-0011 §A.
  - If the diff touches gameplay scope, refuse to "finish" until `/review-gameplay` ran in this session's transcript with a clean return.
  - If the diff touches level scope, the same for `/review-level`.
  - Honour `LASTBREATH_SKIP_REVIEW=1` as the explicit user override. On skip, append a row to `docs/registry/review-log.md` (ISO timestamp, diff scope, reason from the env var, last reviewer decision if any).
- Update `docs/process/harness-engineering.md` §5 to mark stage 2 complete.
- Add an EditMode-style integration smoke (Python, since the hook lives in the Python layer) that fakes a gameplay diff and verifies the router refuses to terminate without a review citation.

## Out of scope

- Asset-design review routing — explicitly excluded by ADR-0011 §A.
- Auto-dispatching the review subagent. The hook **demands** the review; the agent runs it. This preserves the user's ability to direct attention.
- Quality dashboard, doc-gardening agent. Future plans.

## Runtime verification

The hook itself runs in the Python / harness layer, not in Unity. Verification is:

- The integration smoke fakes a gameplay diff, runs the hook, and asserts the hook returns a non-zero status.
- A subsequent run that also includes a `/review-gameplay` clean citation in the transcript returns zero.
- The skip path with `LASTBREATH_SKIP_REVIEW=1` returns zero and writes the expected row to `review-log.md`.

## Acceptance

- [ ] `scripts/harness/review-router.py` exists, exits 0 on clean, 1 on missing review, 2 on infrastructure error.
- [ ] `.claude/settings.json` wires the script to the `Stop` hook.
- [ ] `docs/registry/review-log.md` has the first real entry (this plan's own skip-test fixture or a real skip).
- [ ] `docs/process/harness-engineering.md` §5 stage 2 marked complete.
- [ ] Integration smoke passes.

## Dependencies

PLAN-013 (this plan reads its rule definitions). Should not start until PLAN-008 (Unity bootstrap) ships, so the routing table can be tested against a real `src/Assets/_Project/Scripts/**` diff.
