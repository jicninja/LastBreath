---
id: PROCESS-SESSION-PROTOCOL
type: reference
layer: process
status: active
related: [PROCESS-KICKOFF-PROMPTS]
---

# Session Protocol

How a working session starts. Read this if you have been away >1 day or are starting cold.

## Starting cold

Run these in order. Each takes <30 seconds.

1. **Read `AGENTS.md`** end-to-end. It is the source of truth; the rest of the docs are downstream of it.
2. **Check active plans:**
   ```bash
   grep -l "^status: active" docs/plans/*.md
   ```
   If exactly one is active, read it. If multiple, you have a mess — only one or two should be active at once (per `docs/plans/README.md`). Pause the lowest-priority ones before starting new work.
3. **Check paused plans:**
   ```bash
   grep -l "^status: paused" docs/plans/*.md
   ```
   Read each pause note; decide whether to resume one of them or start fresh.
4. **Read the last 10 commits:**
   ```bash
   git log --oneline | head -10
   ```
   Recognise where you left off. If commit subjects don't match the active plan's scope, something is wrong — investigate before continuing.
5. **Dirty tree?**
   ```bash
   git status
   ```
   If anything is uncommitted, decide: was it mid-task work that should commit now, or a debugging artefact that should be discarded?

## Picking the right agent for the next move

| You are about to … | Dispatch |
|---|---|
| Touch a GDD section (mechanic prose, scene flow) | `game-designer` |
| Touch an SDD section (system contract, events, invariants) | `systems-designer` |
| Touch a TDD section or write C# under `_Project/` | `gameplay-programmer` |
| Touch Unity config (URP asset, asmdef, packages, project settings) | `unity-specialist` |
| Touch a test under `tests/` or write a test plan | `qa-tester` |
| Touch narrative copy (audio logs, panels, HUD strings) | `narrative-director` |
| Audit an existing diff against rules | `code-reviewer` (via `/review-gameplay`) |
| Ideate or design something genuinely new | `superpowers:brainstorming` |
| Materialise an approved design as a plan | `superpowers:writing-plans` |
| Execute an approved plan | `superpowers:subagent-driven-development` |

If the change crosses two boundaries, **leave a plan first** and let each role consume it. Do not bulldoze across roles in one session.

## Ceremony scale

Match the ceremony to the change. Three buckets:

**Tiny** (<5 minutes, single file, no contract change):
- No plan, no spec.
- Edit, dispatch `code-reviewer` (advisory mode is fine), commit.

**Small** (one mechanic or one system, follows established pattern):
- Open a plan (`docs/plans/NNN-<short-name>.md`).
- Use `/scaffold-mechanic` or `/scaffold-system` if the docs/test stubs don't exist yet.
- TDD red → green → refactor.
- `code-reviewer` strict mode.

**Big** (cross-cutting, structural, novel design):
- `superpowers:brainstorming` → spec → plan → subagent-driven-development.
- This is what plans 002 and 003 looked like.

The cost of an under-ceremonied big change shows up later as drift; the cost of an over-ceremonied tiny change is just minutes wasted. **When in doubt, lean lighter** — the reviewer catches drift before it ships.

## Interrupting a session cleanly

If you need to stop mid-task:

1. Commit whatever is in a green state. Don't leave broken intermediate state in the working tree.
2. Update the active plan's `status:` to `paused`.
3. Append a brief pause note to the plan: date, the last task you completed, and one paragraph for whoever resumes.
4. Commit the plan update.

Resuming uses the kickoff prompt in `docs/process/kickoff-prompts.md` §10.

## Parallelism policy

Maximise parallel subagent dispatch — but only where it's safe.

**Always parallel** (send multiple `Agent` calls in one message):
- Read-only research / exploration agents.
- `code-reviewer` against multiple diffs or plans.
- Spec / plan review subagents.
- The `audit-project` skill's internal checks.
- Loading multiple sections of `unity-patterns.md` for different topics.

**Always sequential by default** (one at a time):
- Implementer subagents that commit to `main`. They race on the git index and produce broken commit history. The `subagent-driven-development` skill forbids parallel implementers for this reason.

**Parallel implementers via worktrees** (only when scope is genuinely disjoint and the speed-up is worth the ceremony):
- Use `superpowers:using-git-worktrees` to give each implementer an isolated worktree.
- Controller merges results once each worktree is green.
- Worth it when: tasks span different `.asmdef` boundaries, different top-level docs folders, or different rule files. Not worth it for: any pair that touches `architecture.yaml`, the same agent file, or any shared registry artefact.

**Heuristic:** if two tasks both touch any single file, they are not disjoint — sequence them. When in doubt, sequence.

The default for this project is **parallel for read-only, sequential for write-on-main**. Worktree-based parallel implementation is opt-in per plan.

## What never happens in a session

- Direct edits to `docs/registry/architecture.yaml` from `gameplay-programmer` (use `systems-designer` or paste a `scaffold-*` skill's output).
- Bypassing `code-reviewer` after a code change (= "failure to ship" per `gameplay-programmer.md`).
- Mixing two systems' work in one commit. Each commit is one logical unit.
- Marking a task complete because "it works on my machine" — verification commands in the plan must pass.
- Editing a `done` plan to add new work. Open a new plan; reference the old one if needed.
