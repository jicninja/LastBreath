# docs/decisions/

Architecture Decision Records (ADRs). Distinct from plans.

## Plan vs ADR

- A **plan** says: "Here is the work we will do next, broken into steps."
- An **ADR** says: "Here is a decision we made, the alternatives we rejected, and the reason. Read this when you wonder *why* something is the way it is."

Plans rot fast (they describe future work). ADRs age slowly (they describe a moment of choice that shaped the codebase). Most code questions are "what should I do?" → plan. Most archaeology questions are "why is this here?" → ADR.

## Format

Numbered sequentially: `NNNN-<short-name>.md`. Short content (≤80 lines). Each ADR has these sections:

```markdown
---
id: ADR-NNNN-<short-name>
type: decision
status: accepted     # proposed | accepted | superseded | deprecated
date: YYYY-MM-DD
related: [<plan or spec ID>]
---

# ADR NNNN: <one-line title>

## Context
Why this decision needed to be made. What was the situation, what were the constraints?

## Decision
What we chose. One paragraph, sometimes a short list.

## Alternatives considered
The two or three other options we weighed, and the specific reason each was rejected.

## Consequences
What this decision makes easy. What it makes hard. What we accept losing.

## Notes
Optional. Links, follow-up plans, related ADRs.
```

## When to write an ADR

Write one when you make a decision that:
- Has multiple defensible alternatives.
- Will be hard to reverse later.
- Is non-obvious from reading the code.
- You would want to remember the *why* of in 6 months.

Do **not** write ADRs for:
- Code that documents itself.
- Style choices already enforced by rules in `.claude/rules/`.
- Choices forced by external constraints (engine version, package availability) — note those in `docs/engine-reference/` instead.

## Lifecycle

- `proposed` — drafted, under discussion.
- `accepted` — chosen and in effect.
- `superseded` — a later ADR replaced it. Add `superseded_by: ADR-NNNN`.
- `deprecated` — the choice was wrong and is no longer in effect. Note the corrective action.

ADRs are append-only history. Never edit an `accepted` ADR's decision; if it changes, write a new ADR that supersedes it.

## Numbering

- Always increment from the highest existing `NNNN`. Never reuse numbers.
- Numbering is global across all ADRs regardless of status.
