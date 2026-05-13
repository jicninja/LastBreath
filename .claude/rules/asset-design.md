# Rules — Asset Design

Applies to changes under `art/**`, `src/Assets/_Project/Art/**`, and the `art_assets:` section of `docs/registry/architecture.yaml`. Owned by the `asset-designer` role; the `level-designer` is responsible for `src/Assets/_Project/Art/**` via the `Import Approved Assets` MenuItem.

Rationale: ADR-0008. Canonical loop: `docs/process/asset-design.md`. Authoring surface: `docs/process/blender-mcp.md`.

## `ASSET-DESIGN-NO-UNAPPROVED-IN-ASSETS`

A file exists under `src/Assets/_Project/Art/**` only if it has a corresponding manifest in `art/` with `approved: true` and `imported_at != null`.

Forbidden:

- Dragging or copying a `.glb`, `.fbx`, `.png`, or any asset into `src/Assets/_Project/Art/` outside the `Import Approved Assets` MenuItem.
- A commit that adds a file under `src/Assets/_Project/Art/` without the matching manifest update (the importer should always update the manifest atomically).

Allowed:

- The MenuItem moving an approved file. The reviewer sees the manifest's `imported_at` and `target_unity_guid` go from `null` to populated, and the new file under `src/Assets/_Project/Art/`.

Cite: ADR-0008 `§Decision` (Import gate); `docs/process/asset-design.md` `§7`.

## `ASSET-DESIGN-MANIFEST-REQUIRED`

Every folder under `art/` contains a `manifest.yaml` with all mandatory fields populated: `id`, `name`, `purpose`, `source`, `license`, `provenance`, `exports`, `screenshots`, `approved`.

Forbidden:

- A folder in `art/` with no `manifest.yaml`.
- A `manifest.yaml` missing any mandatory field.
- A manifest with an `id` not registered in `docs/registry/architecture.yaml` under `art_assets:`.

Allowed:

- Empty `art/.gitkeep` (the folder marker, not an asset).

Cite: ADR-0008 `§Decision` (Authoring artefact); `docs/process/asset-design.md` `§5`.

## `ASSET-DESIGN-LICENSE-DOCUMENTED`

`manifest.license` is non-empty and references a recognised licence value: `CC0`, `CC-BY-4.0`, `custom-<repo>`, `hand_authored`, or another value justified in `manifest.notes`. The reviewer fails the commit if the field is empty or contains a placeholder string (`TODO`, `unknown`, etc.).

Forbidden:

- `license: ""` or `license: TODO`.
- A licence value that the legend in `docs/process/asset-design.md` `§5` does not document, without a justification in `notes`.

Cite: ADR-0008 `§Decision` (Sourcing); `docs/process/asset-design.md` `§5`.

## `ASSET-DESIGN-PROVENANCE-DOCUMENTED`

`manifest.provenance` carries the fields the declared `source` requires:

- `source: polyhaven` → `provenance.polyhaven_id` is set.
- `source: execute_blender_code` → `provenance.recipe_path` points at a committed file inside `art/<asset>/`.
- `source: hand_authored_user` → `provenance.hand_authored_by` is set.

Forbidden:

- A manifest that declares `source: polyhaven` without `polyhaven_id`.
- A manifest that declares `source: execute_blender_code` whose `recipe_path` does not exist on disk.
- A manifest that declares a `source` value not allowed by ADR-0008 (e.g., `sketchfab`, `hyper3d`) without an ADR that allows it.

Cite: ADR-0008 `§Decision` (Sourcing); `docs/process/asset-design.md` `§5`.

## `ASSET-DESIGN-STAGING-DOESNT-LEAK`

Paths under `art/` are referenced **only** from `manifest.yaml` and from this rules family. They are not referenced from `.unity`, `.prefab`, `.layout.yaml`, or any C# under `src/Assets/_Project/Scripts/**`.

Forbidden:

- A `.layout.yaml` that points a `prefab:` or `mesh:` field at `art/...`. Imports go through `src/Assets/_Project/Art/...`.
- A C# `[SerializeField]` path or `AssetDatabase.LoadAssetAtPath` that reaches into `art/`.

Cite: ADR-0008 `§Decision` (Import gate); `docs/process/asset-design.md` `§7`.

## `ASSET-DESIGN-NO-UNITY-EDITS`

An asset-design commit (a diff whose primary change is under `art/**`) does not change `src/Assets/Scenes/**.unity`, `docs/levels/**`, or `src/Assets/_Project/Scripts/**`.

Forbidden:

- The asset-designer modifying a scene or layout to "preview" the new asset. Previewing is the level-designer's job after import.
- A cross-cutting commit that bundles asset authoring with scene composition. Use two commits: one to ship the asset to staging, one to compose the scene after import.

Allowed:

- A cross-role plan in `docs/plans/` that explicitly groups both kinds of work, citing both roles in the plan's "Owners" section.

Cite: ADR-0008 `§Decision` (Roles); `AGENTS.md` `§Roles`.

## `ASSET-DESIGN-SYNC-PARITY`

Any commit that touches `art/**`, `src/Assets/_Project/Art/**`, or `docs/levels/**/*.layout.yaml` passes `scripts/check-art-sync.py` (Layer A). The reviewer runs the script and fails the commit if exit code != 0.

Cite: ADR-0008 `§Decision` (Sync verification); `docs/process/asset-design.md` `§8`.

## `ASSET-DESIGN-APPROVAL-IS-HUMAN-ONLY`

Only a human writes `approved: true` and `approved_by: <user>` into a manifest. Agents (including the `asset-designer`) never set these fields.

Forbidden:

- An asset-designer commit that introduces `manifest.approved: true`.
- A script or tool that sets `approved: true` non-interactively. `/art-approval-queue` is the only path, and it requires explicit user confirmation per asset.

Allowed:

- An agent setting `approved: false` after the user instructs it to discard the asset.
- An agent setting `approved: pending` (the default at creation time).

Cite: ADR-0008 `§Decision` (Approval gate); `docs/process/asset-design.md` `§6`.

## `ASSET-DESIGN-IMPORT-IS-MENUITEM-ONLY`

The only path that adds a file under `src/Assets/_Project/Art/` is the `Import Approved Assets` MenuItem (`src/Assets/_Editor/Art/ApprovedAssetImporter.cs`, Wave B). Manual drag-drop or `cp` into `src/Assets/_Project/Art/` is forbidden.

Forbidden:

- A commit that adds files under `src/Assets/_Project/Art/` without the matching manifest updates the MenuItem produces (`imported_at`, `target_unity_guid` written, hash verified).

Cite: ADR-0008 `§Decision` (Import gate); `docs/process/asset-design.md` `§7`.
