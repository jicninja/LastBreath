---
name: asset-design-session
user-invocable: true
description: Run an asset-design session end-to-end — verify blender-mcp is connected, iterate via the asset-designer scope of blender-mcp, then perform the snapshot ritual (export .glb, capture screenshots, write manifest with approved: pending, commit to staging). Enforces the order from docs/process/asset-design.md §4.
---

# asset-design-session skill

## Purpose

Codifies the Blender-side session loop from `docs/process/asset-design.md` `§4` so every session ships a schema-correct manifest + a `.glb` + screenshots in the right order. The order is rigid; the Blender iteration in the middle is free.

## Args

- `art_id` (required) — the `ART-*` ID being authored. Must exist in `docs/registry/architecture.yaml` under `art_assets:`.
- `goal` (required) — one sentence describing the session's intent. Becomes the commit message subject.
- `phase` (optional, default `auto`) — `start | iterate | snapshot | auto`.

## Behaviour

### Phase `start`

1. Resolve `name_kebab` from `art_id` by looking up `art_assets:` in `architecture.yaml` (the `manifest` field points at `art/<name_kebab>/manifest.yaml`). Abort if the asset has not been scaffolded — direct the user to `scaffold-asset`.
2. Verify `blender-mcp` is connected:
    - Call `get_scene_info` (read-only) as a no-op probe.
    - If it fails, surface the error and stop. Do not write any files.
3. Read the manifest. Confirm `approved: pending`. If `approved: true` and `imported_at != null`, the asset is already shipped — direct the user at a new asset id or at iterating via a new manifest revision.
4. Read the relevant context: the GDD scene or the layout README (`docs/levels/<scene>/README.md`) that motivates this asset.
5. Print to the user: the manifest path, the source (polyhaven | execute_blender_code | hand_authored_user), the target_unity_path, the goal.

### Phase `iterate`

Free iteration via `blender-mcp` within the asset-designer scope (`docs/process/blender-mcp.md` `§4`). The skill does not script this phase. Allowed verbs depend on the manifest's `source`:

- `source: polyhaven` → use `download_polyhaven_asset` first, then `execute_blender_code` for tweaks.
- `source: execute_blender_code` → run `recipe.py` via `execute_blender_code`. Iterate on the recipe file directly (Write/Edit) if the user requests changes.
- `source: hand_authored_user` → the user models. The skill only opens the right `.blend` and waits.

The skill resumes when the user signals satisfaction.

### Phase `snapshot`

Rigid order. If any step fails, surface and stop — do not skip or reorder.

1. **Save the Blender scene.** Call the appropriate `execute_blender_code` snippet (`bpy.ops.wm.save_mainfile()`) or, for hand-authored assets, ask the user to save in the Blender UI.
2. **Export the `.glb`.** Call `execute_blender_code` with `bpy.ops.export_scene.gltf(filepath=..., export_format='GLB', ...)`. Honour `manifest.exports[0].contains` — enable `KHR_lights_punctual` if `lights` is listed, enable `export_animations` if `animations` is listed.
3. **Capture screenshots.** Frame the asset for the front view (`bpy.context.scene.camera` aligned to +Y), call `get_viewport_screenshot` → `screenshots/preview-front.png`. Frame for the 3/4 view (rotate camera 45°), capture → `screenshots/preview-3q.png`.
4. **Update the manifest.** Edit the manifest in place to reflect the actual exports:
    - `exports[*].contains` matches what the glTF actually carries (the export step's flags).
    - `notes` absorbs any open questions the user raised mid-iteration.
    - Leave `approved: pending`. The skill **never** writes `approved: true`.
5. **Stage the commit bundle.** List the files to stage:
    - `art/<name_kebab>/<name_kebab>.glb`
    - `art/<name_kebab>/<name_kebab>.blend` (if hand-authored or `bpy.ops.wm.save_mainfile()` was called)
    - `art/<name_kebab>/recipe.py` (if updated)
    - `art/<name_kebab>/screenshots/preview-front.png` and `preview-3q.png`
    - `art/<name_kebab>/manifest.yaml`
   Do not commit on the user's behalf — the user reviews the diff and commits.
6. **Hand off.** Print the next step: "Asset staged. Run `/art-approval-queue` to review and approve (or reject)."

### Phase `auto`

Read the manifest. If `manifest.exports[0].path` does not exist on disk, resume from `iterate` (we haven't produced the `.glb` yet). If the `.glb` exists but no screenshots, resume from `snapshot` starting at step 3. If everything is in place but the manifest is still `approved: pending`, the session is closed — direct the user at `/art-approval-queue`.

## Failure modes

- `blender-mcp` not connected: surface and stop. Never substitute YAML edits for actual exports.
- Asset has not been scaffolded: surface and direct to `scaffold-asset`.
- Disallowed `source` (Sketchfab, Hyper3D, etc.): surface and point at ADR-0008. Do not invoke the verb.
- Manifest already `approved: true`: surface and direct at iterating via a new `ART-*` revision (or simply skip — the asset is shipped).

## Constraints

- Never edits `src/Assets/_Project/Art/**`, `src/Assets/Scenes/**`, `docs/levels/**`, or `src/Assets/_Project/Scripts/**`.
- Never sets `approved: true`. The forcing function for approval is `/art-approval-queue` + the human.
- Never commits on the user's behalf.
- Never calls a `blender-mcp` verb outside the asset-designer scope of `docs/process/blender-mcp.md` `§4`.

## See also

- `docs/process/asset-design.md` — the canonical loop this skill enforces.
- `docs/process/blender-mcp.md` — the verbs the iterate phase uses.
- `.claude/agents/asset-designer.md` — the role that invokes this skill.
- `.claude/skills/scaffold-asset/` — sibling skill for first-time asset bring-up.
- `.claude/skills/art-approval-queue/` — sibling skill the user runs after this one.
- `.claude/skills/review-asset/` — sibling skill dispatched at the end of every session.
