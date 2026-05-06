---
id: PROCESS-KICKOFF-PROMPTS
type: reference
layer: process
status: active
related: [PROCESS-ADD-MECHANIC, PROCESS-UNITY-PATTERNS]
---

# Kickoff Prompts

Paste-ready prompts for the most common workflows in this repo. Copy the block, edit the placeholders, send.

Each prompt assumes you have just read `AGENTS.md` and the active plan (if any). If you have not, run the **Resume a session** prompt first.

---

## 1. Resume a session

> Use at the start of every working session that does not begin with a brand-new task.

```
Read AGENTS.md, list active plans (`grep -l "status: active" docs/plans/*.md`),
read the most recent active plan end-to-end, and `git log --oneline | head -10`.
Summarise: where I left off, what's next, what's blocked.
Do not modify any file.
```

---

## 2. Bootstrap Unity project (Phase 0, plan 004)

> One-time. Authors plan 004 and executes it. Touches Unity package versions, asmdef boundaries, URP setup.

```
We are starting plan 004: bootstrap-unity-project. Per
`docs/superpowers/specs/2026-05-05-ai-augmented-workflow-design.md` and
the workflow in `docs/process/kickoff-prompts.md`, follow this flow:

1. Invoke `superpowers:brainstorming`. Topic: bootstrap the Unity project
   under `src/` per `docs/process/unity-patterns.md` Section 1, pinned to
   the versions in `docs/engine-reference/unity/VERSION.md`. No gameplay
   code in scope — just foundation.
2. Hand the approved spec to `superpowers:writing-plans`.
3. Hand the approved plan to `superpowers:subagent-driven-development`.
4. Each task ends with a `code-reviewer` strict-mode dispatch.

Owner role: `unity-specialist`. The `gameplay-programmer` does not touch
this plan. Read `unity-patterns.md` Section 1 and `engine-reference/unity/`
before brainstorming. Surface only on destructive or contract-changing
decisions.
```

---

## 3. Implement an already-registered system (Phase 1, per system)

> Use once for each `SYS-*` ID in `docs/registry/architecture.yaml`. Replace `<SYS-ID>` and `<SystemName>`.

```
We are implementing <SYS-ID> (<SystemName>). Read these in order:
1. `docs/registry/architecture.yaml` — confirm the system's classes, events,
   publishes/subscribes.
2. `docs/sdd/last-breath-poc-sdd.md#<systemname>` — system contract.
3. `docs/tdd/last-breath-poc-tdd.md#<systemname>` — reference code shape.
4. `.claude/rules/gameplay-code.md` and `test-standards.md`.
5. `docs/process/unity-patterns.md` — invoke the `unity-patterns` skill for
   the relevant sections (at minimum: monobehaviour-split, event-symmetry,
   testability).

Workflow:
- If the system has a player-facing mechanic and no per-system docs yet:
  run `/scaffold-mechanic --name <SystemName> --pillars '[<PILLAR-IDs>]'`.
- If the system is presentation/orchestration (no mechanic):
  run `/scaffold-system --name <SystemName>`.
- Open a small plan at `docs/plans/NNN-implement-<systemname>.md` with the
  affected files, test plan, and acceptance.
- TDD: red → green → refactor. EditMode test on the plain-C# logic class.
- Dispatch `code-reviewer` in strict mode after the green commit.

Surface only if the SDD contract is unclear or you need a contract change.
```

---

## 4. Add a brand-new mechanic (not yet in registry)

> Use when the GDD or design discussion produces a new mechanic the registry doesn't know about.

```
We're adding a new mechanic: <Name>, mapped to pillars [<PILLAR-IDs>].

Steps:
1. Read `docs/process/adding-a-mechanic.md` end-to-end.
2. Run `/scaffold-mechanic --name <Name> --pillars '[<PILLAR-IDs>]'`. The
   skill produces GDD/SDD/TDD/test stubs and prints a registry YAML block.
3. Paste the YAML block into `docs/registry/architecture.yaml`. The skill
   does not edit the registry.
4. `game-designer` fills the GDD section.
5. `systems-designer` fills the SDD section.
6. `gameplay-programmer` fills the TDD section and implements the system,
   following the workflow in kickoff-prompts §3.

Each role dispatches `code-reviewer` at the end of its slice.
```

---

## 5. Sandbox spike

> Use when you want to try something without ceremony. Lives in `src/Assets/_Sandbox/**`. Bypasses most rules per `.claude/rules/prototype-code.md`.

```
Sandbox spike: <one-line goal>.

Constraints:
- Work only under `src/Assets/_Sandbox/<topic>-spike/`.
- Header comment required: "// Sandbox: <topic>-spike — <YYYY-MM-DD>"
  followed by the goal and a delete-on-promotion note.
- No reference from `_Project/`. Sandbox is isolated.
- No tests required. No reviewer dispatch required.
- Two-week shelf life: delete or promote.

Do not open a plan. Do not touch the registry. Do not modify GDD/SDD/TDD.
```

---

## 6. Promote a sandbox spike to `_Project/`

> When a spike proves the design and earns a promotion. Promotion follows full ceremony.

```
Promote sandbox spike at `src/Assets/_Sandbox/<topic>-spike/` to `_Project/`.

Workflow:
1. Read `docs/process/promoting-a-prototype.md` (if it exists) or the
   "Still-firm rules" in `.claude/rules/prototype-code.md`.
2. Open plan `docs/plans/NNN-promote-<topic>.md` with: source files,
   target paths in `_Project/`, registry entries to add, tests to write.
3. The promotion is NOT an `_Sandbox/ → _Project/` copy. The code is
   re-implemented to the gameplay-code.md standard, with EditMode tests
   for any formula and full reviewer pass.
4. Delete the sandbox copy in the same plan's final commit.
5. Mark plan `status: done` with the new system's stable IDs.
```

---

## 7. Run the reviewer manually

> When you want to audit a change without waiting for the gameplay-programmer to auto-dispatch.

```
/review-gameplay
```

With scope:

```
/review-gameplay --plan 003 --strict
```

Or against a specific git range:

```
/review-gameplay --range main..HEAD
```

Returns the structured `status` / `violations` / `registry_drift` /
`plan_adherence` block. Read it. If `issues_found`, fix and re-run.

---

## 8. Open a plan from a clear spec

> When you already have a spec and just need the plan. Skips brainstorming.

```
Author plan NNN at `docs/plans/NNN-<feature-name>.md` from spec
`docs/superpowers/specs/<spec-file>.md`. Use `superpowers:writing-plans`.
The plan must follow `docs/plans/README.md` conventions (numbering,
lifecycle states) and the structure of `docs/plans/002-*.md`. Each task
ends in one commit. Run the plan-document-reviewer loop. Then surface
to me for approval before execution.
```

---

## 9. Open a spec from scratch (uncertainty present)

> When the design isn't settled. Goes through brainstorming first.

```
Brainstorm and spec: <topic in one sentence>. Constraints from this repo:
- Solo-dev PoC, Unity URP, ~3–5 minutes of gameplay.
- Match conventions in AGENTS.md and `.claude/rules/`.
- Reuse existing IDs from `docs/registry/architecture.yaml` where possible.
- Out of scope: <list what we're not doing>.

Use `superpowers:brainstorming`. Surface to me at every section gate.
The output spec lives in `docs/superpowers/specs/YYYY-MM-DD-<topic>.md`.
```

---

## 10. Pause / resume / abandon a plan

> Per `docs/plans/README.md` lifecycle.

Pause:

```
Pause plan NNN. Set `status: paused` at the top of the plan file.
Append a brief "Paused at: <date>, last completed task: Task X"
note. Commit. Surface a one-paragraph handoff for whoever resumes
(could be a future me).
```

Resume:

```
Resume plan NNN. Read the plan, the pause note, and the last commit
on this plan's scope. Set `status: active`. Continue from the first
unchecked step. Dispatch `code-reviewer` after the next commit lands.
```

Abandon:

```
Abandon plan NNN. Set `status: abandoned`. Append a "Reason for
abandonment" section explaining what changed and where the work
went instead. Commit. Do not delete the file.
```

---

## How to extend this doc

When you find yourself constructing a similar prompt twice in a session, add it here with a one-line "when to use" headline. The library grows by use, not by prediction.
