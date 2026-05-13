# Review log

Append-only audit trail of explicit skips of the `HARNESS-LOOP-REVIEW-BEFORE-COMPLETION` rule. Each entry records a session that closed without running the matching `/review-*` skill, with the reason and the diff scope, so skips remain visible to the next reviewer.

Format: one row per skip. Newest at the top. ISO 8601 timestamps. Diff scope is the routing key from `.claude/rules/harness-loop.md` (`gameplay-code` | `level-design` | `both`). Reviewer decision is the last `/review-*` output that ran in the session, if any (`clean` | `fix-list` | `none`).

Maintained by:

- Until PLAN-014 lands: written by the user (or by the agent on the user's explicit instruction) when a session closes with a deliberate skip.
- After PLAN-014 lands: written by `scripts/harness/review-router.py` when invoked with `LASTBREATH_SKIP_REVIEW=1`.

Rule that owns this file: `HARNESS-LOOP-REVIEW-BEFORE-COMPLETION` in `.claude/rules/harness-loop.md`. ADR: 0011.

---

| Timestamp (UTC) | Diff scope | Reason | Reviewer decision | Skipped by |
|---|---|---|---|---|

<!-- Append new entries below this comment. Newest first. -->
