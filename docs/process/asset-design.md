---
id: PROCESS-ASSET-DESIGN
type: reference
layer: process
status: active
related: [ADR-0008, PROCESS-LEVEL-DESIGN, PROCESS-BLENDER-MCP, PLAN-006]
---

# Asset design — the Blender-side loop

Canonical workflow for producing a 3D asset and shipping it to Unity. Read end-to-end the first time, then jump to the section you need.

Decisions: `docs/decisions/0008-asset-pipeline.md`. Authoring surface: `docs/process/blender-mcp.md`. Rules: `.claude/rules/asset-design.md`.

## 1. Roles and scope

- `asset-designer` owns: `art/**` (staging) and `blender-mcp` authoring.
- `level-designer` owns: `src/Assets/_Project/Art/**` once an asset is imported, via the `Import Approved Assets` MenuItem. Read-only `blender-mcp` access for sanity checks.
- Only the user (human) approves: writes `approved: true` in a manifest. Agents propose; the human decides.

If a session needs new gameplay code (a custom asset behaviour, a new component), the asset-designer stops, opens a plan in `docs/plans/`, and resumes after the gameplay-programmer ships the behaviour. Asset-design sessions never touch `src/Assets/_Project/Scripts/**`.

## 2. ID convention

| Layer | Prefix | Example | Casing |
|-------|--------|---------|--------|
| Art asset | `ART-` | `ART-CORRIDOR-PANEL-01` | UPPERCASE, English, hyphens |

`ART-*` IDs are registered in `docs/registry/architecture.yaml` under `art_assets:` with `status: active | deprecated`. They are immutable once published.

## 3. Folder layout

```
art/
  incoming/
    <asset-kebab>/
      manifest.yaml
      <asset-kebab>.glb               # canonical export
      <asset-kebab>.blend             # optional, if hand_authored_user
      recipe.py                       # optional, if execute_blender_code
      screenshots/
        preview-front.png
        preview-3q.png
```

```
src/Assets/
  _Project/
    Art/
      <Category>/
        <AssetName>/
          <asset-kebab>.glb           # copy of art/<asset>/<asset>.glb at approval time
          (Unity will produce .meta files automatically)
```

Naming:

- Asset folder: kebab-case, matches `manifest.name` and `<asset-kebab>.glb`.
- Asset ID: `ART-<SCOPE>-<NAME>` (`ART-CORRIDOR-PANEL-01`, `ART-CABIN-BREATHING-STATION`). The scope token matches the layout it primarily serves; reusable assets use a neutral scope (`ART-PROP-CHAIR`).
- Unity category: PascalCase (`Props`, `Architecture`, `Lights`, `SetPieces`). Declared per asset in `manifest.target_unity_path`.

## 4. The session loop

```
goal stated  →  blender-mcp iterate (Claude + user, Blender open)  →  user validates
                                                                          ↓
                                                            still iterating?
                                                                          ↓
                                                                   user happy
                                                                          ↓
                                                            end-of-session snapshot
                                                                          ↓
                                                                   commit bundle to staging
                                                                          ↓
                                                            human approval (separate step, /art-approval-queue)
                                                                          ↓
                                                            level-designer imports via MenuItem
```

Steps:

1. **State the goal.** One sentence at the top of the new manifest's `purpose:` field. (`Modular panel for the maintenance room — three states (intact, damaged, dark)`.)
2. **Iterate via `blender-mcp`.** Use the verbs in `docs/process/blender-mcp.md` `§3` (asset-designer scope). For Polyhaven sourcing, `download_polyhaven_asset` then optional `execute_blender_code` for tweaks. For hand-authored, the user models in Blender and the MCP only exports / records. For recipes, the MCP runs `execute_blender_code` with the script committed alongside.
3. **Snapshot.** When the user is satisfied:
    1. `scene.save()` in Blender.
    2. Export `.glb` to `art/<asset-kebab>/<asset-kebab>.glb`. Use Blender's glTF exporter; include lights and animations only if the asset declares them in the manifest.
    3. Capture two viewport screenshots: `screenshots/preview-front.png` and `screenshots/preview-3q.png`. Frame the asset against a neutral background; the user reviews these in `/art-approval-queue`.
    4. Write the `manifest.yaml` from the schema in `§5` with `approved: pending`. The `imported_hash` field stays empty until approval.
4. **Commit the staging bundle.** Stage the `.glb`, `.blend` (if present), `recipe.py` (if present), screenshots, and `manifest.yaml`. One commit per asset (or one per coherent batch of related assets — e.g., a set of three panel variants).
5. **Hand off.** The asset is now pending in staging. The SessionStart hook will surface it next session. The user runs `/art-approval-queue` when ready.

## 5. Manifest schema

`art/<asset-kebab>/manifest.yaml`:

```yaml
id: ART-<SCOPE>-<NAME>
name: <asset-kebab>
purpose: <one line>

source: polyhaven | execute_blender_code | hand_authored_user
license: CC0 | CC-BY-4.0 | custom-<repo> | hand_authored
provenance:
  # populated according to source
  polyhaven_id: <id>                # if source: polyhaven
  recipe_path: art/<asset-kebab>/recipe.py   # if source: execute_blender_code
  hand_authored_by: <user>          # if source: hand_authored_user

exports:
  - format: glb
    path: art/<asset-kebab>/<asset-kebab>.glb
    contains: [mesh, materials, lights, rig]   # subset of: mesh, materials, lights, rig, animations

screenshots:
  - art/<asset-kebab>/screenshots/preview-front.png
  - art/<asset-kebab>/screenshots/preview-3q.png

approved: pending          # pending | true | false
approved_at: null          # ISO timestamp
approved_by: null          # user identifier

imported_hash: null        # sha256 of the .glb at approval time
imported_at: null          # ISO timestamp when the level-designer imported it
target_unity_path: src/Assets/_Project/Art/<Category>/<AssetName>/<asset-kebab>.glb
target_unity_guid: null    # populated by the importer after first import

importer_settings:
  scale_factor: 1.0
  generate_lights: true
  import_animations: false
  generate_colliders: false

notes: |
  Free text. Open questions, known caveats, references.
```

Rules:

- `id` is immutable. A new revision of the same asset reuses the id; the manifest's `imported_hash` changes when re-approved.
- `source`, `license`, and `provenance` are the audit triple. The reviewer fails the commit if any is missing.
- `imported_hash` is populated by `/art-approval-queue` at approval time, **not** at export time. This is the contract: hash-at-approval == hash-at-import-time.
- `target_unity_path` is set by the asset-designer at the manifest's creation. The MenuItem honours it; it does not invent paths.

## 6. Approval (the user's hand on the steering wheel)

The user is the only approver. Two surfaces:

1. **SessionStart hook.** Surfaces pending count automatically. If the count is `> 0`, the system reminder asks the user to run `/art-approval-queue`.
2. **`/art-approval-queue`.** Lists pending manifests with screenshots, provenance, and notes. For each, the user chooses:
    - `approve` — sets `approved: true`, `approved_at: <now>`, `imported_hash: sha256(.glb)`. Saves the manifest.
    - `reject` — sets `approved: false`. The asset stays in staging marked rejected; the asset-designer either iterates and re-submits, or deletes it.
    - `request-iteration` — leaves `approved: pending` but appends a note. The asset-designer reads notes next session.

The user **never** edits `src/Assets/_Project/Art/` directly. Even if the file lands by mistake, the reviewer flags `ASSET-DESIGN-NO-UNAPPROVED-IN-ASSETS`.

## 7. Import (level-designer's verb)

When `approved: true` and `imported_at: null`, the asset is ready to land in Unity. The level-designer runs `[MenuItem("LastBreath/Art/Import Approved Assets")]` (implemented in Wave B). The importer:

1. Scans `art/*/manifest.yaml`.
2. For each `approved: true && imported_at == null`:
    - Verifies `sha256(<glb>) == manifest.imported_hash`. If not, abort with a clear error — the file changed after approval.
    - Creates the target directory under `src/Assets/_Project/Art/<Category>/<AssetName>/`.
    - Copies the `.glb` to `manifest.target_unity_path`.
    - Configures `AssetImporter.GetAtPath(...)` from `manifest.importer_settings`.
    - Writes `imported_at` and `target_unity_guid` back to the manifest.
3. Logs each asset processed. Idempotent: a second run is a no-op.

The level-designer can now reference the asset from a `.layout.yaml` (by `target_unity_path`).

## 8. Sync verification

Two layers; see `docs/decisions/0008-asset-pipeline.md` `§Decision`.

- **Layer A (Python, user-invoked).** `/verify-art-sync` → `scripts/check-art-sync.py`. Hash + cross-reference. Fast, no Unity needed.
- **Layer B (Unity MenuItem, Wave B).** `/verify-art-sync --deep` → invokes `LastBreath/Art/Verify Sync`. Adds importer-setting verification.

Run before commit. The reviewer enforces clean sync via `ASSET-DESIGN-SYNC-PARITY`.

## 9. Session log

Asset-design sessions do **not** require a separate `session-NNNN.md`. The manifest is the session log: its `notes` field absorbs "what landed / what got rejected / open questions" in prose. Keeping a separate log doubles the work without adding audit value (Blender doesn't have the same compositional iteration depth as scene authoring).

The commit message carries the session intent in one paragraph.

## 10. What this process is NOT for

- Editing `.unity` or `.layout.yaml` — that is `level-designer`.
- Writing C# — that is `gameplay-programmer`.
- Tuning balance numbers — that is `game-designer`.
- Approving assets — that is the user. Agents propose; the human decides.

## 11. Acceptance checklist for an asset-design commit

What `code-reviewer` will look for on an `art/**` diff. The change is not mergeable until every box is ticked.

- [ ] `art/<asset-kebab>/manifest.yaml` exists with all mandatory fields (`id`, `name`, `purpose`, `source`, `license`, `provenance`, `exports`, `screenshots`, `approved`).
- [ ] `id` is registered in `docs/registry/architecture.yaml` under `art_assets:` with `status: active`.
- [ ] `source` is one of `polyhaven | execute_blender_code | hand_authored_user`. Other sources need a follow-up ADR.
- [ ] `license` is non-empty.
- [ ] `provenance` carries the source-specific fields.
- [ ] `<asset-kebab>.glb` exists and the screenshots exist.
- [ ] No file is added under `src/Assets/_Project/Art/` in this commit (that comes via the MenuItem, in a separate commit).
- [ ] Canonical glossary in prose (`asset-designer`, `asset manifest`, `staging area`, `approval gate`, `art asset`, `provenance`).
- [ ] ASCII identifiers in file paths.
