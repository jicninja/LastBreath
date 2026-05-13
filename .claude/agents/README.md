# .claude/agents/

Role definitions used by Claude Code, Codex, and Gemini. The role table from `AGENTS.md` is the source of truth; this file is an index.

## Roles

| File | Reads | May modify | Does NOT touch |
|---|---|---|---|
| `game-designer.md` | GDD, registry | `docs/gdd/**`, `docs/registry/architecture.yaml` (`pillars`, `mechanics`, `scenes` only) | SDD, TDD, code |
| `systems-designer.md` | GDD, SDD, registry | `docs/sdd/**`, `docs/registry/**` | TDD, code |
| `gameplay-programmer.md` | SDD, TDD, registry, engine-reference, `docs/process/unity-patterns.md` | `src/**`, `docs/tdd/**` | GDD, SDD |
| `unity-specialist.md` | TDD, engine-reference | `src/**` (Unity config, prefabs, .asmdef), `docs/engine-reference/unity/VERSION.md` (only when package versions move) | gameplay logic, design docs |
| `level-designer.md` | GDD scene flow, SDD `§EnvironmentSystem`, registry, `docs/process/level-design.md`, `docs/process/unity-mcp.md`, `docs/process/blender-mcp.md` `§4` | `docs/levels/**`, `src/Assets/Scenes/**.unity` composition, `src/Assets/_Project/Prefabs/Level/**`, `src/Assets/_Project/Config/Levels/**`, `src/Assets/_Project/Art/**` only via `Import Approved Assets` MenuItem, `docs/registry/architecture.yaml` (`scenes` and `layouts` only) | gameplay code, engine config, design intent, narrative copy, `blender-mcp` author verbs, `art/**` |
| `asset-designer.md` | GDD scene/prop intent, registry (`art_assets:`), `docs/process/asset-design.md`, `docs/process/blender-mcp.md`, `docs/decisions/0008-asset-pipeline.md` | `art/**`, `docs/registry/architecture.yaml` (`art_assets:` only) | `.unity`, `docs/levels/**`, `src/Assets/_Project/Art/**`, code, design docs, narrative, `manifest.approved: true` |
| `qa-tester.md` | everything | `docs/plans/**` (test plans/results), `docs/qa/bug-reports/**`, `tests/**` | systems |
| `narrative-director.md` | GDD | `docs/gdd/**` (narrative only), `src/Assets/_Project/Localization/**` (strings only, when it exists) | mechanics, systems, code outside localization |
| `code-reviewer.md` | rules, registry, plans, `docs/process/unity-patterns.md`, `.claude/rules/level-design.md`, `.claude/rules/asset-design.md`, the diff | nothing (read-only) | all writes |

## Adding a role

Open a plan in `docs/plans/`. New roles must be enumerable here and in the boundary table in `AGENTS.md`.
