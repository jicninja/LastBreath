---
id: PROCESS-BLENDER-MCP
type: reference
layer: process
status: active
related: [ADR-0008, PROCESS-ASSET-DESIGN, PROCESS-LEVEL-DESIGN]
---

# Blender MCP — setup, capability matrix, and role allowlists

The `blender-mcp` server is the bridge between Claude (as `asset-designer`) and the Blender editor. The `level-designer` is granted a strict read-only subset for sanity checks across the two tools.

Decisions: `docs/decisions/0008-asset-pipeline.md`. Canonical loop: `docs/process/asset-design.md`. Role files: `.claude/agents/asset-designer.md`, `.claude/agents/level-designer.md`.

## 1. Which Blender-MCP

This project uses the `blender-mcp` server already wired into the Claude environment (the upstream `BlenderMCP` Python addon + MCP bridge). Specific install steps land in Wave B of plan 006; the schema and capability matrix below are stable across implementations of "Blender as MCP".

If a future ADR replaces this MCP with a different implementation, the `manifest.yaml` schema and the role allowlists stay; only the verb names below change.

## 2. Installation (Wave B)

> The Unity project does not exist yet. Blender-MCP install lands alongside the first real asset-design session. Until then, this section is the canonical instructions for when it does.

1. Install the Blender addon from the upstream `blender-mcp` repo and enable it in `Edit > Preferences > Add-ons`.
2. Start Blender. The addon exposes a local socket the MCP bridge attaches to.
3. Register the MCP server in `.mcp.json` at the repo root:
    ```json
    {
      "mcpServers": {
        "blender-mcp": {
          "command": "blender-mcp-bridge",
          "args": []
        }
      }
    }
    ```
4. Restart the assistant so the new MCP server is picked up.

## 3. Full capability matrix

These are the verbs `blender-mcp` exposes (as of the version this project pins). Verbs marked **author** mutate state; verbs marked **read** do not.

| Verb | Kind | What it does |
|---|---|---|
| `get_scene_info` | read | Returns the active scene's hierarchy and object list. |
| `get_object_info` | read | Returns transform + mesh + material data for a named object. |
| `get_viewport_screenshot` | read | Captures the current viewport to a PNG. |
| `execute_blender_code` | author | Runs arbitrary Python (`bpy.*`) inside Blender. The dangerous verb. |
| `download_polyhaven_asset` | author | Pulls a Polyhaven asset into the scene. |
| `download_sketchfab_model` | author | Pulls a Sketchfab model. (Not allowed by ADR-0008 yet.) |
| `generate_hyper3d_model_via_text` | author | AI-generates a model from text. (Not allowed by ADR-0008 yet.) |
| `generate_hyper3d_model_via_images` | author | AI-generates a model from images. (Not allowed by ADR-0008 yet.) |
| `generate_hunyuan3d_model` | author | AI-generates a model via Hunyuan3D. (Not allowed by ADR-0008 yet.) |
| `import_generated_asset` | author | Imports a generative result into the active scene. |
| `import_generated_asset_hunyuan` | author | Same, Hunyuan-specific. |
| `set_texture` | author | Applies a texture to a material slot. |
| `poll_hunyuan_job_status` | read | Polls a Hunyuan generation job. |
| `poll_rodin_job_status` | read | Polls a Hyper3D Rodin generation job. |
| `get_hunyuan3d_status` | read | Returns Hunyuan service status. |
| `get_hyper3d_status` | read | Returns Hyper3D service status. |
| `get_polyhaven_categories` | read | Lists Polyhaven categories. |
| `get_polyhaven_status` | read | Returns Polyhaven addon status. |
| `get_sketchfab_model_preview` | read | Returns a Sketchfab preview. |
| `get_sketchfab_status` | read | Returns Sketchfab addon status. |
| `search_polyhaven_assets` | read | Searches Polyhaven. |
| `search_sketchfab_models` | read | Searches Sketchfab. |

## 4. Role allowlists

The reviewer enforces these allowlists via the rules `ASSET-DESIGN-*` and `LEVEL-DESIGN-BLENDER-READ-ONLY`.

### `asset-designer` (full allowlist, ADR-0008-allowed subset)

- All **read** verbs.
- `execute_blender_code` (author, full).
- `download_polyhaven_asset`, `set_texture`.
- `import_generated_asset*` only when the source it imports is one of the three ADR-0008-allowed sources (Polyhaven, hand_authored_user, recipe).

Forbidden for `asset-designer` until a follow-up ADR adds them:

- `download_sketchfab_model` — licence tracking not yet specified.
- `generate_hyper3d_model_*`, `generate_hunyuan3d_model` — provenance/cost fields not yet specified.

### `level-designer` (read-only subset)

The level-designer uses Blender only to verify what an imported asset *should* look like vs what Unity shows. Allowed verbs:

- `get_scene_info`, `get_object_info` — inspect hierarchy and per-object data.
- `get_viewport_screenshot` — capture a Blender viewport for visual comparison.
- All `*_status` and `poll_*` verbs — passive checks.
- `search_polyhaven_assets`, `search_sketchfab_models`, `get_sketchfab_model_preview`, `get_polyhaven_categories` — browsing, no download.

Forbidden for `level-designer`:

- `execute_blender_code` — even an "innocent" Python snippet can mutate state. Hard ban; no exceptions, no "I promise it's read-only".
- `download_polyhaven_asset`, `download_sketchfab_model`, `generate_*`, `import_generated_asset*`, `set_texture` — these are author verbs.

If a level-designer needs to author in Blender, they hand off to the asset-designer via a note in the session log — they do **not** call author verbs themselves.

## 5. Forbidden patterns (regardless of role)

- **`bpy.ops.wm.quit_blender`** — kills the editor, breaks the MCP. Even the asset-designer must not call this.
- **Mass deletions without backup.** Any `execute_blender_code` that calls `bpy.ops.object.delete()` over more than ten objects must first call `scene.save()` so the deletion is recoverable from disk.
- **Reading or writing outside the repo.** The MCP can touch the filesystem; restrict every file path to inside the repo (`art/**` for writes, anywhere readable for reads of references the user provides).

## 6. Known gotchas

- **Blender must be running.** The bridge is a socket to a running Blender instance; if Blender is closed, the MCP fails.
- **`execute_blender_code` is sticky.** Side effects persist across calls. Treat the Blender scene as the state; the MCP is the way to mutate it but the source of truth for "what is the asset right now?" is the running editor.
- **glTF exporter quirks.** Lights need `KHR_lights_punctual` extension enabled in the exporter settings. Skinned animations need the rig in rest pose at frame 1 or Unity imports them wrong. Document any exporter setting in the manifest's `notes` field so re-exports are reproducible.
- **Polyhaven addon must be enabled** before `download_polyhaven_asset` works. The hook script does not check this; the asset-designer asks via `get_polyhaven_status` first.
- **Screenshots are viewport-only.** They capture whatever the user (or the MCP via `bpy.context.scene.camera`) frames. The asset-designer must frame the asset deliberately before calling `get_viewport_screenshot`, or it captures whatever is on screen.

## 7. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `get_scene_info` returns "Blender not connected". | Editor closed or addon disabled. | Open Blender, enable the addon, retry. |
| `download_polyhaven_asset` returns "Polyhaven addon not enabled". | Self-explanatory. | Enable in `Edit > Preferences > Add-ons`, retry. |
| `.glb` export missing lights despite the asset having them. | `KHR_lights_punctual` not enabled in exporter. | Update the recipe / asset-designer call to set the export flag; re-export. |
| `set_texture` succeeds but Unity shows no texture after import. | Image was packed externally and not embedded in the `.glb`. | Pack with `bpy.ops.file.pack_all()` before export, re-export. |
| `verify-art-sync` reports hash drift right after export. | Manifest `imported_hash` was set before the final export. | Re-approve via `/art-approval-queue` (it recomputes the hash). |

## 8. Future capabilities

Sketchfab + AI-generative sourcing are intentionally gated. Adding them requires:

1. A follow-up ADR that defines the licence and cost-tracking fields the manifest needs.
2. An update to this doc moving the verbs from "forbidden" to "asset-designer allowed".
3. An update to `.claude/rules/asset-design.md` adding the corresponding provenance rules.

Do not enable these verbs ad-hoc inside a session.
