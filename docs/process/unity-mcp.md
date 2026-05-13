---
id: PROCESS-UNITY-MCP
type: reference
layer: process
status: active
related: [ADR-0007, PROCESS-LEVEL-DESIGN]
---

# Unity MCP — setup and usage

The `unity-mcp` server is the bridge between Claude (as `level-designer`) and the Unity editor. It is the authoring surface for level design (ADR-0007). Other roles do not drive it.

## 1. Which Unity-MCP

This project uses [Justin P Barnett's `unity-mcp`](https://github.com/justinpbarnett/unity-mcp). Pin a specific commit in the install instructions below once Wave B of the level-design plan lands; for now, follow the upstream README.

If a future ADR replaces this MCP with a different implementation, the `LevelSpec` verbs (`Dump Spec`, `Apply Spec`, `Validate`) and the spec format remain stable — only the install instructions in this doc change.

## 2. Installation

> The Unity project does not exist yet. This section is the canonical instructions for when it does. Until Wave B lands, every command below assumes the project root is at `src/`.

1. Install the `unity-mcp` Unity package into the project. Follow the upstream repo's "Install the package" section.
2. Install the Python bridge (`uv` or `pipx` works). The upstream repo names the entry-point `unity-mcp-bridge`.
3. Register the MCP in `.mcp.json` at the repo root:
    ```json
    {
      "mcpServers": {
        "unity-mcp": {
          "command": "unity-mcp-bridge",
          "args": [],
          "env": {
            "UNITY_PROJECT_PATH": "${workspaceFolder}/src"
          }
        }
      }
    }
    ```
4. Open the Unity project in the editor. The MCP bridge connects to Unity over a local socket; the editor must be running for any MCP verb to succeed.
5. Restart the assistant so the new MCP server is picked up.

## 3. Capability matrix

These are the verbs the `level-designer` uses. The upstream MCP exposes more — this section lists the ones this project relies on. If you need a verb that is not here, add it (with a one-line justification) before using it.

| Verb (informal) | What it does | Used in |
|---|---|---|
| `scene.open(path)` | Opens a scene asset in the editor. | Start of every session. |
| `scene.save()` | Saves the open scene to disk. | After each meaningful change. |
| `node.create(parent, name, type)` | Adds a GameObject under `parent`. | Iteration. |
| `node.delete(path)` | Removes a node. | Iteration. |
| `node.set_transform(path, pos, rot, scale)` | Moves/rotates/scales a node. | Iteration. |
| `node.add_component(path, type)` | Attaches a component. | Iteration. |
| `node.set_field(path, component, field, value)` | Sets an inspector field. Used to wire `FlagDefinition` and `PresenceEventDefinition` refs. | Iteration. |
| `prefab.instantiate(path, parent, name)` | Drops a prefab instance into the scene. | Iteration. |
| `viewport.screenshot(path, width, height)` | Saves the current scene-view or game-view to a PNG. | Snapshot step. |
| `menu.invoke("LastBreath/Level/Dump Spec")` | Runs the snapshot dumper. | Snapshot step. |
| `menu.invoke("LastBreath/Level/Apply Spec")` | Runs the idempotency rebuild. | Snapshot step. |
| `menu.invoke("LastBreath/Level/Validate")` | Runs the invariants check. | Snapshot step. |
| `play.start()` / `play.stop()` | Enters / exits Play Mode. | Smoke-testing the level after a session. |

## 4. Verbs we deliberately do NOT use

- **`shell.exec` or arbitrary script eval**, even if exposed. Level-design sessions stay inside the editor; arbitrary shell defeats the audit trail.
- **`project.set_setting`** or anything that touches `src/ProjectSettings/`. That is `unity-specialist` territory; opening a plan is required.
- **`asset.create_script`** to create new C# files. Gameplay code lives under `gameplay-programmer`; the level-designer hands off via the session log.

## 5. Known gotchas

- **Editor must be running and have focus.** The bridge is a socket to a running Unity instance; if the editor is closed or compiling, MCP calls fail. The session loop expects an open editor; close it only after the snapshot is committed.
- **Recompilations interrupt the session.** Modifying a C# file under `src/Assets/_Project/Scripts/**` triggers a recompile, which suspends the bridge until Unity finishes. Level-design sessions should not touch scripts; if a session needs new gameplay code, stop and hand off.
- **`scene.save()` writes the `.unity` immediately.** Any change made through MCP between two saves is uncommitted on disk. The snapshot step calls `scene.save()` first, then `DumpSpec`.
- **Prefab edits propagate.** Editing a prefab in place affects every scene that uses it. The level-designer avoids editing prefabs from inside a scene; prefab changes go through `prefab.instantiate` + override, not in-place edit.
- **Coordinate frame.** This project's scenes are 3D with a side-on camera (per the GDD). Place spawn markers, prefabs, and triggers on the X/Z plane; Y is gravity.
- **Screenshot paths.** Always commit screenshots under `docs/levels/<scene>/img/`, never under `src/Assets/`. Files under `src/Assets/` are tracked by Unity as importable assets and require a `.meta` companion.

## 6. Capability requests for the gameplay-programmer

Other roles must read this matrix before asking the level-designer to do something. Specifically:

- The `game-designer` can request a layout (e.g., "place the breathing station near the airlock") because the matrix supports `prefab.instantiate` + `node.set_transform`.
- The `game-designer` cannot request a new interactable type via this MCP. That request goes to `gameplay-programmer` as a plan.
- The `qa-tester` can request a screenshot of any committed scene by name; the level-designer reopens the scene, captures, commits the image.

## 7. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| MCP verbs return "Unity not connected". | Editor is closed, compiling, or not focused. | Open Unity, wait for compile to finish, retry. |
| `DumpSpec` succeeds but the YAML is empty. | The active scene is not the one the level-designer thought. | Run `scene.open(<scene_path>)` first; re-dump. |
| `ApplySpec` produces a scene that differs from the source. | A non-load-bearing GUID drift, or an unsupported component field. | Compare diffs with `git diff --stat`; if it is just GUIDs, accept it. If a real field is missing, file a bug — `DumpSpec` is incomplete. |
| `viewport.screenshot` saves a black image. | Scene view has no camera framing. | Frame the view in Unity first, then capture. |

## 8. Future: alternative MCPs

If the upstream `unity-mcp` is abandoned or proves unstable, replace it with a different Unity-MCP server. Update this doc with the new install instructions and capability matrix. The `LevelSpec` verbs and the `.layout.yaml` format are MCP-agnostic by design.
