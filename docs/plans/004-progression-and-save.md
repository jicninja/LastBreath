---
id: PLAN-004-progression-and-save
type: plan
status: done
done_date: 2026-05-12
related: [ADR-0004, ADR-0005]
---

# Plan 004: Progression and Save documentation

> The PoC is shifting into a graphic-adventure shape (events unlock events, and the player must be able to save and resume mid-chain). This plan ships the design docs for three new systems — Flags, Narrative, Save — across GDD/SDD/TDD/registry. No application code yet.

## Goal

Land the design documentation for `SYS-FLAGS`, `SYS-NARRATIVE`, `SYS-SAVE` and update existing docs so the next implementation plan can be picked up by `gameplay-programmer` without further design work. The two ADRs that frame this plan (ADR-0004, ADR-0005) ship alongside it.

## Scope (7 items: A–G)

- **A**. GDD — add `§Progression model` section: flags vs. objectives, the unlock graph as a design concept, where save points live in narrative beats.
- **B**. `docs/registry/architecture.yaml` — register `SYS-FLAGS`, `SYS-NARRATIVE`, `SYS-SAVE`; configs `CFG-FLAG`, `CFG-NARRATIVE-CUE`; events `EVT-flag-changed`, `EVT-narrative-cue-fired`, `EVT-save-completed`, `EVT-save-restored`. Add the new `GameState.Loading` value as a note on `SYS-GAME`.
- **C**. SDD — add `FlagSystem`, `NarrativeDirector`, `SaveSystem` sections (Responsibility / Inputs / Outputs / Invariants / Acceptance). Add `Loading` to the `GameState` flow diagram. Update `§Communication matrix` to include new rows. Update `§Game State Flow`.
- **D**. SDD — extend existing `§Minimum checkpoint` to point at `SYS-SAVE`; note that the prior struct sketch is superseded by `SaveData` DTOs documented in TDD.
- **E**. TDD — add `FlagSystem`, `FlagDefinition`, `NarrativeDirector`, `NarrativeCueDefinition`, `SaveSystem`, `SaveData` (root DTO + per-system DTOs), `IPersistentInteractable`, `InteractableRegistry`, and the `ISaveable<TDto>` contract. Each with the public API surface (method signatures, public fields, events).
- **F**. Reviewer rules — add to `.claude/rules/gameplay-code.md`:
  - `FLAG-NO-SO-EVENT-CHANNEL` (references ADR-0004).
  - `SAVE-ONLY-SAVESYSTEM-TOUCHES-DISK` (references ADR-0005).
  - `SAVE-NO-EVENTS-DURING-LOADING` (references ADR-0005).
  Also update `.claude/agents/code-reviewer.md` rule index.
- **G**. `docs/registry/glossary.md` — define: flag, flag definition, narrative cue, save point, persistence id, loading state, DTO, saveable.

## Out of scope

- Any C# code under `src/`. The implementation plan is PLAN-005 (or later) and must be visual-first per the project's working preference.
- Actual `FlagDefinition` / `NarrativeCueDefinition` assets for `Corridor C-7`.
- UI/HUD changes (deferred until after implementation lands).
- Multi-slot save UI, save thumbnails, async/background save.
- Cross-scene save handling beyond recording `sceneName` in the DTO.

## Affected files

New (already shipped alongside this plan):
- `docs/decisions/0004-flag-and-narrative-event-model.md`
- `docs/decisions/0005-save-system-architecture.md`
- `docs/plans/004-progression-and-save.md`

Modified by this plan:
- `docs/gdd/last-breath-poc-gdd.md`
- `docs/sdd/last-breath-poc-sdd.md`
- `docs/tdd/last-breath-poc-tdd.md`
- `docs/registry/architecture.yaml`
- `docs/registry/glossary.md`
- `.claude/rules/gameplay-code.md`
- `.claude/agents/code-reviewer.md`
- `docs/plans/README.md` (index entry; done at plan creation).

## Implementation order

1. **A** (GDD progression model) — drives everything else.
2. **B** (registry IDs) — required before SDD/TDD can cite them by ID.
3. **C + D** (SDD sections + `Loading` state + checkpoint pointer).
4. **E** (TDD classes and `ISaveable<TDto>` contract).
5. **F** (reviewer rules + agent index).
6. **G** (glossary).
7. Verify acceptance + mark `done`.

Each chunk = one commit, in this order. Suggested subagents:
- A → `game-designer`
- B → manual (registry is sensitive; only the change-owner edits it)
- C, D → `systems-designer`
- E → `gameplay-programmer` (doc-only mode; no `src/` touches)
- F → `unity-specialist` (rules) + manual for the agent index
- G → `narrative-director` or manual

## Acceptance

- [ ] `architecture.yaml` contains `SYS-FLAGS`, `SYS-NARRATIVE`, `SYS-SAVE`, `CFG-FLAG`, `CFG-NARRATIVE-CUE`, `EVT-flag-changed`, `EVT-narrative-cue-fired`, `EVT-save-completed`, `EVT-save-restored`, all `status: active`.
- [ ] SDD `§Game State Flow` includes `Loading` and names `SaveSystem` as the only writer of disk.
- [ ] SDD `§Communication matrix` has rows for `FlagSystem`, `NarrativeDirector`, `SaveSystem`.
- [ ] SDD `§Minimum checkpoint` points at `SYS-SAVE` and notes the prior sketch is superseded.
- [ ] TDD declares `ISaveable<TDto>` once with the contract; every saveable system in the SDD names its DTO type.
- [ ] TDD declares `IPersistentInteractable` and `InteractableRegistry` with the registration lifecycle (`OnEnable` / `OnDisable`).
- [ ] `.claude/rules/gameplay-code.md` contains `FLAG-NO-SO-EVENT-CHANNEL`, `SAVE-ONLY-SAVESYSTEM-TOUCHES-DISK`, `SAVE-NO-EVENTS-DURING-LOADING`, each cross-referencing its ADR.
- [ ] `.claude/agents/code-reviewer.md` rule index lists the three new rule IDs.
- [ ] Glossary defines: flag, flag definition, narrative cue, save point, persistence id, loading state, DTO, saveable.
- [ ] No code under `src/Assets/_Project/**` was touched by this plan.
- [ ] `scripts/audit-md.py` (if present) passes; no orphan docs.

## Follow-up

A separate implementation plan (PLAN-005 or later) will instantiate the C# classes documented here. That plan **must** be visual-first per the project preference: first commit shows a flag flipping at runtime via a debug key in `Corridor C-7`, before any narrative cue or save plumbing lands. Subagent: `gameplay-programmer`. Execution mode: subagent-driven (per memory).
