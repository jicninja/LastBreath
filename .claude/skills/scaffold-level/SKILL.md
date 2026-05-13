---
name: scaffold-level
user-invocable: true
description: Scaffold a new level — writes a scene README, a layout.yaml skeleton, image and session folders, and an EditMode invariants test stub, then prints YAML blocks for architecture.yaml. Refuses to overwrite. Never auto-edits the registry. Does not touch docs/plans/ or docs/specs/.
---

# scaffold-level skill

## Purpose

Materialise the recipe in `docs/process/level-design.md` for a new scene. Produces all stub files in one shot so the `level-designer` can open a session immediately.

**Out of scope:** this skill does not generate plan stubs (`docs/plans/`) and does not write into `docs/specs/`. Plans are authored deliberately via `superpowers:writing-plans` when (and only when) the change warrants one (e.g., first bring-up of a scene that has no `.unity` yet).

## Args

- `scene_id` (required) — must already exist in `docs/registry/architecture.yaml` under `scenes:` with `status: active`. Example: `SCENE-CORREDOR-C7`.
- `name_kebab` (required) — folder name under `docs/levels/`. Example: `corredor-c7`. Must match `^[a-z][a-z0-9-]+$`.
- `scene_name` (required, PascalCase) — the Unity scene file name (no extension). Example: `CorridorC7`. Used in test class names and the printed registry block.
- `layouts` (required, list of one or more identifiers) — the `LAYOUT-*` sub-sections this scene declares. Provide just the suffix part; the skill prefixes `LAYOUT-` and the scene token. Example for `SCENE-CORREDOR-C7`: `[CABIN, CORRIDOR, MAINTENANCE, AIRLOCK, EXTERIOR, ANTENNA, RETURN]` → produces `LAYOUT-C7-CABIN`, `LAYOUT-C7-CORRIDOR`, etc.
- `layout_token` (optional) — the abbreviation inserted between `LAYOUT-` and the suffix. Defaults to the trailing token of `scene_id` after the final `-` (so `SCENE-CORREDOR-C7` → `C7`).

## Behaviour

1. Read `docs/process/level-design.md` (the contract) and `docs/registry/architecture.yaml`.
2. Validate:
   - `scene_id` exists in `architecture.yaml` under `scenes:` with `status: active`.
   - `name_kebab` matches the regex.
   - `scene_name` matches `^[A-Z][A-Za-z0-9]+$`.
   - For each entry in `layouts`, the resulting `LAYOUT-<token>-<entry>` is **not** already present in `architecture.yaml` (active or deprecated). If any is, abort.
   - The folder `docs/levels/<name_kebab>/` does not already contain `README.md` or `<name_kebab>.layout.yaml`. If it does, abort with the conflicting paths listed.
3. Write these files (refuse to overwrite if any exist; abort with the conflicting paths listed):
   - `docs/levels/<name_kebab>/README.md` (from `templates/scene-readme.md`)
   - `docs/levels/<name_kebab>/<name_kebab>.layout.yaml` (from `templates/layout.yaml`)
   - `docs/levels/<name_kebab>/img/.gitkeep`
   - `docs/levels/<name_kebab>/sessions/.gitkeep`
   - `src/Assets/_Project/Tests/EditMode/Levels/<scene_name>InvariantsTests.cs` (from `templates/edit-mode-invariants-test.cs`)
4. Print the registry YAML block to chat (rendered from `templates/registry-block.yaml`); the user pastes it into `architecture.yaml`. **The skill does not edit `architecture.yaml`.**

## Failure modes

- Conflict (target exists): abort, no partial writes.
- Unknown / deprecated `scene_id`: abort.
- Duplicate `LAYOUT-*` (active or deprecated) in the registry: abort.
- Malformed `name_kebab` or `scene_name`: abort.

## Constraints

- Never auto-edits `docs/registry/architecture.yaml`.
- Never overwrites existing files.
- Never references game-specific terms in the templates beyond the canonical glossary (`oxygen`, `agitation`, `presence`, `interior`, `exterior`, `airlock`, `corridor`).
- Never writes into `docs/plans/` or `docs/specs/`.
- Never creates `.unity`, `.prefab`, or `.asset` files. The Unity-side artefacts are created by the `level-designer` in a session via `unity-mcp` (or by `LevelSpec.ApplySpec` once the spec is non-empty).

## See also

- `docs/process/level-design.md` — the canonical loop.
- `docs/process/unity-mcp.md` — the authoring surface used after this skill runs.
- `.claude/agents/level-designer.md` — the role that operates on the stubs this skill writes.
- `.claude/skills/scaffold-mechanic/`, `.claude/skills/scaffold-system/` — sibling scaffolds, same constraints model.
