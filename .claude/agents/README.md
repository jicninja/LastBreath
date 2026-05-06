# .claude/agents/

Role definitions used by Claude Code, Codex, and Gemini. The role table from `AGENTS.md` is the source of truth; this file is an index.

## Roles

| File | Reads | May modify | Does NOT touch |
|---|---|---|---|
| `game-designer.md` | GDD, registry | `docs/gdd/**`, `docs/registry/architecture.yaml` (`pillars`, `mechanics`, `scenes` only) | SDD, TDD, code |
| `systems-designer.md` | GDD, SDD, registry | `docs/sdd/**`, `docs/registry/**` | TDD, code |
| `gameplay-programmer.md` | SDD, TDD, registry, engine-reference, `docs/process/unity-patterns.md` | `src/**`, `docs/tdd/**` | GDD, SDD |
| `unity-specialist.md` | TDD, engine-reference | `src/**` (Unity config, prefabs, .asmdef), `docs/engine-reference/unity/VERSION.md` (only when package versions move) | gameplay logic, design docs |
| `qa-tester.md` | everything | `docs/plans/**` (test plans/results), `docs/qa/bug-reports/**`, `tests/**` | systems |
| `narrative-director.md` | GDD | `docs/gdd/**` (narrative only), `src/Assets/_Project/Localization/**` (strings only, when it exists) | mechanics, systems, code outside localization |
| `code-reviewer.md` | rules, registry, plans, `docs/process/unity-patterns.md`, the diff | nothing (read-only) | all writes |

## Adding a role

Open a plan in `docs/plans/`. New roles must be enumerable here and in the boundary table in `AGENTS.md`.
