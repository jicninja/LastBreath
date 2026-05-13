---
name: scaffold-system
user-invocable: true
description: Scaffold a new system that has no player-facing mechanic — writes SDD/TDD/test stubs and prints a YAML block for architecture.yaml. Use for HUD, audio, environment, orchestration systems. Refuses to overwrite. Never auto-edits the registry. Does not touch docs/plans/ or docs/specs/.
---

# scaffold-system skill

## Purpose

Sibling to `scaffold-mechanic`, for systems that **do not** have a player-facing mechanic in the GDD — presentation, orchestration, and infrastructure systems (e.g., `SYS-HUD`, `SYS-AUDIO`, `SYS-LIGHTVFX`, `SYS-ENVIRONMENT`, `SYS-GAME`, `SYS-INTERACTOR`, `SYS-OBJECTIVE`).

Produces SDD doc, TDD doc, EditMode test stub, and a registry YAML block. **Skips the GDD output** because there is no mechanic prose to write.

**Out of scope:** does not generate plan stubs, does not write into `docs/specs/`, does not edit `docs/registry/architecture.yaml`. Plans are deliberate; the registry edit is a deliberate paste.

## When to use this vs `scaffold-mechanic`

- Use `scaffold-mechanic` when the system is the implementation of a player-facing mechanic listed in the GDD (any active `MECH-*` entry in `docs/registry/architecture.yaml`). Output includes a GDD mechanic doc.
- Use `scaffold-system` when the system has no GDD mechanic counterpart. Output skips GDD; everything else is the same shape as `scaffold-mechanic`.

If you are unsure: read `docs/process/adding-a-mechanic.md` §1 (decision tree). If the player has no verb against it and it has no rules of its own, it is a system, not a mechanic.

## Args

- `name` (PascalCase, required) — e.g., `Hud`. Becomes `SYS-HUD`, `HudController`, `HudConfig`, etc.
- `publishes` (list of `EVT-*` IDs, default `[]`).
- `subscribes` (list of `EVT-*` IDs, default `[]`).
- `kind` (`presentation` | `orchestration` | `infrastructure`, default `presentation`).

## Behaviour

1. Read `docs/process/adding-a-mechanic.md` (the contract — section structure is the same; only the GDD output is omitted here).
2. Validate: `name` matches `^[A-Z][a-zA-Z0-9]+$`; every event in `publishes` and `subscribes` either exists in `architecture.yaml` or is namespaced under this system (new events need a registry entry the user pastes); no system with this `name` exists (active or deprecated) in `architecture.yaml`.
3. Write these files (refuse to overwrite if any exist; abort with the conflicting paths listed):
   - `docs/sdd/systems/<name-kebab>.md` (from `templates/sdd-system.md`)
   - `docs/tdd/classes/<Name>System.md` (from `templates/tdd-class.md`)
   - `tests/EditMode/<Name>SystemTests.cs` (from `templates/edit-mode-test.cs`)
4. Print the registry YAML block to chat (rendered from `templates/registry-block.yaml`); the user pastes it into `architecture.yaml`.

## Failure modes

- Conflict (target exists): abort, no partial writes.
- Duplicate system name (active or deprecated): abort.
- Unknown event in `publishes`/`subscribes` that is not declared as new: abort.

## Constraints

- Never auto-edits `docs/registry/architecture.yaml`.
- Never overwrites existing files.
- Never references project-specific mechanic names in the templates (the source doc is project-agnostic by design).
- Read-only on the registry. Write-only on the four target paths above (when the targets don't exist).
