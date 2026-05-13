---
name: scaffold-asset
user-invocable: true
description: Scaffold a new asset staging folder — writes art/<asset>/manifest.yaml, screenshots/.gitkeep, and a placeholder recipe.py (if source=execute_blender_code). Idempotently appends the art_assets entry to docs/registry/architecture.yaml via scripts/add-art-asset-to-registry.py. Refuses to overwrite manifests. Does not touch .unity or layout.yaml.
---

# scaffold-asset skill

## Purpose

Materialise the recipe in `docs/process/asset-design.md` for a new art asset. Produces a schema-correct manifest stub so the asset-designer can open a Blender session immediately and so the reviewer can find every mandatory field.

**Out of scope:** this skill does not run Blender, does not download Polyhaven assets, does not produce a `.glb`. It only writes the staging skeleton.

## Args

- `id` (required) — the `ART-*` ID. Example: `ART-CORRIDOR-PANEL-01`. Must match `^ART-[A-Z0-9-]+$`.
- `name_kebab` (required) — the folder name under `art/`. Example: `corridor-panel-01`. Must match `^[a-z][a-z0-9-]+$`.
- `purpose` (required) — one-line description of what the asset is for. Becomes `manifest.purpose`.
- `source` (required) — one of `polyhaven | execute_blender_code | hand_authored_user`. Other values are rejected (ADR-0008 gate).
- `license` (required) — `CC0`, `custom-<repo>`, `hand_authored`, or another value justified later in `manifest.notes`.
- `provenance_value` (required) — the source-specific provenance value: Polyhaven id, or the user identifier, or `recipe.py` (for execute_blender_code; the skill creates a placeholder recipe).
- `target_unity_path` (required) — where the importer should put the asset. Example: `src/Assets/_Project/Art/Props/CorridorPanel01/corridor-panel-01.glb`.

## Behaviour

1. Read `docs/process/asset-design.md` and `docs/registry/architecture.yaml`.
2. Validate:
    - `id` matches the regex and is not already present in `architecture.yaml` under `art_assets:` (active or deprecated).
    - `name_kebab` matches the regex.
    - `source` is one of the three ADR-0008-allowed values.
    - `license` is non-empty.
    - `provenance_value` is non-empty.
    - `target_unity_path` starts with `src/Assets/_Project/Art/` and ends with `.glb`.
    - The folder `art/<name_kebab>/` does not already contain a `manifest.yaml`. If it does, abort with the conflicting path listed.
3. Write these files (refuse to overwrite if any exist):
    - `art/<name_kebab>/manifest.yaml` from `templates/manifest.yaml`.
    - `art/<name_kebab>/screenshots/.gitkeep`.
    - If `source: execute_blender_code`: `art/<name_kebab>/recipe.py` from `templates/recipe.py` (a stub the asset-designer fills in).
4. Append the registry entry by running:

    ```
    python3 scripts/add-art-asset-to-registry.py \
        --id <ART_ID> \
        --name <name_kebab> \
        --source <source> \
        --license <license> \
        --manifest art/<name_kebab>/manifest.yaml
    ```

    Behaviour:
    - Exit 0 with "replaced_empty" or "appended" → registry updated; report the change to the user.
    - Exit 0 with "already present" → idempotent re-run; mention it but do nothing extra.
    - Exit 1 with "art_assets: section not found in a recognised shape" → the script prints the YAML block to stderr; surface it to the user for manual paste, do not retry.
    - Exit 2 → infrastructure error (missing pyyaml, registry file missing); halt and surface the error.

    Never edit `docs/registry/architecture.yaml` with `Edit`/`Write` directly — always go through the helper script so the format stays mechanical and idempotent.
5. Run `python3 scripts/check-manifest-schema.py --asset <ART_ID>` as a self-check. The fresh manifest is `approved: pending` with placeholder screenshots and an empty `.glb`, so schema violations at this stage are real bugs in the template or in the args — surface them immediately.

## Failure modes

- Conflict (target exists): abort, no partial writes.
- Unknown / disallowed `source`: abort, point at ADR-0008.
- Duplicate `ART-*` ID in the registry: abort.
- Malformed args: abort.

## Constraints

- Edits `docs/registry/architecture.yaml` **only** via `scripts/add-art-asset-to-registry.py`. Never with `Edit`/`Write` directly.
- Never overwrites existing manifests or asset files.
- Never writes outside `art/<name_kebab>/` (except the registry append above).
- Never produces a `.glb` — that comes from a real Blender session via `asset-design-session`.
- Never sets `approved: true`. The skill writes `approved: pending`; only the user changes that via `/art-approval-queue`.

## See also

- `docs/process/asset-design.md` — the canonical loop.
- `docs/process/blender-mcp.md` — the authoring surface used after this skill runs.
- `.claude/agents/asset-designer.md` — the role that operates on the stubs this skill writes.
- `.claude/skills/asset-design-session/` — sibling skill for running the Blender session itself.
- `.claude/skills/scaffold-level/`, `.claude/skills/scaffold-mechanic/`, `.claude/skills/scaffold-system/` — sibling scaffolds, same constraints model.
