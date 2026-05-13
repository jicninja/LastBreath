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

## Index

Listed for indexing by `scripts/audit-md.py` and for quick navigation. Each ADR's body remains the source of truth; the one-line tag here is just a hook.

- [0001-language-policy-english-only.md](0001-language-policy-english-only.md) — English-only repo.
- [0002-monobehaviour-vs-plain-csharp-split.md](0002-monobehaviour-vs-plain-csharp-split.md) — MonoBehaviour vs plain-C# split.
- [0003-soft-reviewer-enforcement.md](0003-soft-reviewer-enforcement.md) — Soft reviewer enforcement model.
- [0004-flag-and-narrative-event-model.md](0004-flag-and-narrative-event-model.md) — Flag and narrative event model (no SO event channels).
- [0005-save-system-architecture.md](0005-save-system-architecture.md) — DTO-snapshot save / restore.
- [0006-transport-and-llm-policy.md](0006-transport-and-llm-policy.md) — LLM transport seam + availability gating.
- [0007-level-design-authoring-flow.md](0007-level-design-authoring-flow.md) — Level design: spec-after-snapshot via `unity-mcp`.
- [0008-asset-pipeline.md](0008-asset-pipeline.md) — Asset pipeline: Blender → staging → approval → Unity.
- [0009-runtime-and-tooling-versions.md](0009-runtime-and-tooling-versions.md) — Runtime and tooling version pins (Unity, packages, VContainer, UniTask).
- [0010-player-controls-camera-and-dof.md](0010-player-controls-camera-and-dof.md) — Player controls, billboard, side-rig camera with DOF.
