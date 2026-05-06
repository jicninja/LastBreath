---
id: PLAN-003-document-and-prompt-scaffolding
type: plan
status: done
done_date: 2026-05-05
related: [PLAN-002]
---

# Plan 003: Document and Prompt Scaffolding

> Pre-Phase-0 documentation bundle. Reduces friction before Unity bootstrap (plan 004) and Phase 1 system implementation begins.

## Goal

Ship the documentation, skills, and per-role prompt scaffolding that make every subsequent plan faster to start. Pure docs + one new skill, no application code.

## Scope (8 items: A–H)

- **A**. `docs/process/kickoff-prompts.md` — copy-paste prompts library.
- **B**. `docs/process/session-protocol.md` — how a working session starts.
- **C**. `.claude/skills/scaffold-system/` — sibling to `scaffold-mechanic` for systems without a player-facing mechanic (HUD, audio, environment, etc.).
- **D**. `docs/decisions/` — ADR folder + 3 backfilled ADRs (language policy, MonoBehaviour split, soft-reviewer enforcement).
- **E**. `docs/registry/glossary.md` — extend with event terminology and role names.
- **F**. `docs/engine-reference/unity/VERSION.md` — lock to exact Unity LTS + URP versions.
- **G**. `docs/plans/README.md` — add `paused` + `superseded` lifecycle states.
- **H**. Each `.claude/agents/*.md` — add `## How to dispatch me` section with canonical kickoff prompt.

## Out of scope

- Unity project itself (`src/`) — that's plan 004.
- Game-specific content (mechanic GDDs, system SDDs).
- CI / hooks / batchmode tests.

## Affected files

New:
- `docs/process/kickoff-prompts.md`
- `docs/process/session-protocol.md`
- `.claude/skills/scaffold-system/SKILL.md`
- `.claude/skills/scaffold-system/templates/sdd-system.md`
- `.claude/skills/scaffold-system/templates/tdd-class.md`
- `.claude/skills/scaffold-system/templates/edit-mode-test.cs`
- `.claude/skills/scaffold-system/templates/registry-block.yaml`
- `docs/decisions/README.md`
- `docs/decisions/0001-language-policy-english-only.md`
- `docs/decisions/0002-monobehaviour-vs-plain-csharp-split.md`
- `docs/decisions/0003-soft-reviewer-enforcement.md`

Modified:
- `docs/registry/glossary.md`
- `docs/engine-reference/unity/VERSION.md`
- `docs/plans/README.md`
- `.claude/agents/game-designer.md`
- `.claude/agents/systems-designer.md`
- `.claude/agents/gameplay-programmer.md`
- `.claude/agents/unity-specialist.md`
- `.claude/agents/qa-tester.md`
- `.claude/agents/narrative-director.md`
- `.claude/agents/code-reviewer.md`

## Implementation order

1. A + B (process docs)
2. C (scaffold-system skill)
3. D (ADR folder + 3 ADRs)
4. E + F + G (registry/version/lifecycle polish)
5. H (per-role dispatch sections)
6. Verify + mark done

Each chunk = one commit.

## Acceptance

- [ ] All 11 new files exist with non-stub content.
- [ ] All 7 modified files contain the new sections.
- [ ] `scaffold-system` SKILL.md is read-only enforced (no Edit/Write tools granted) and refuses to overwrite.
- [ ] Genericity grep passes: `! grep -ri "oxygen|agitation|presence|flashlight" .claude/skills/scaffold-system/`.
- [ ] `docs/plans/README.md` documents `paused` and `superseded` states.
- [ ] `VERSION.md` names exact Unity LTS + URP versions, not ranges.
- [ ] Each `.claude/agents/*.md` has a `## How to dispatch me` section with a paste-ready prompt.
