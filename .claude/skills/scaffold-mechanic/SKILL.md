---
name: scaffold-mechanic
user-invocable: true
description: Scaffold a new mechanic — writes GDD/SDD/TDD/test stubs and prints a YAML block for architecture.yaml. Refuses to overwrite. Never auto-edits the registry. Does not touch docs/plans/ or docs/superpowers/.
---

# scaffold-mechanic skill

## Purpose

Materialise the recipe in `docs/process/adding-a-mechanic.md` for a new mechanic. Produces all stub files in one shot. The recipe is the contract; this skill is the faster path through it.

**Out of scope:** this skill does not generate plan stubs (`docs/plans/`) and does not write into `docs/superpowers/`. Plans are authored deliberately via the `superpowers:writing-plans` skill when (and only when) the change actually warrants one.

## Args

- `name` (PascalCase, required) — e.g., `Vision`. Becomes `MECH-VISION`, `SYS-VISION`, `VisionSystem`, etc.
- `pillars` (list of existing PILLAR-NN IDs, required) — must already exist as `status: active` in `docs/registry/architecture.yaml`.
- `kind` (`experience` | `production`, default `experience`).

## Behaviour

1. Read `docs/process/adding-a-mechanic.md` (the contract).
2. Validate: `name` matches `^[A-Z][a-zA-Z0-9]+$`; every pillar in `pillars` is present and active in `architecture.yaml`; no mechanic with this `name` exists (active or deprecated) in `architecture.yaml`.
3. Write these files (refuse to overwrite if any exist; abort with the conflicting paths listed):
   - `docs/gdd/mechanics/<name-kebab>.md` (from `templates/gdd-mechanic.md`)
   - `docs/sdd/systems/<name-kebab>.md` (from `templates/sdd-system.md`)
   - `docs/tdd/classes/<Name>System.md` (from `templates/tdd-class.md`)
   - `tests/EditMode/<Name>SystemTests.cs` (from `templates/edit-mode-test.cs`)
4. Print the registry YAML block to chat (rendered from `templates/registry-block.yaml`); the user pastes it into `architecture.yaml`. **The skill does not edit `architecture.yaml`.**

## Failure modes

- Conflict (target exists): abort, no partial writes.
- Unknown / inactive pillar: abort.
- Duplicate mechanic name (active or deprecated): abort.

## Constraints

- Never auto-edits `docs/registry/architecture.yaml`.
- Never overwrites existing files.
- Never references game-specific terms in the templates.
