# Blender — Version & Tooling

> This file is the contract for asset-design work (ADR-0008) and the companion to `docs/engine-reference/mcp/VERSIONS.md` (which pins the `blender-mcp` server). Every value below is exact, not a range. Bumping any line requires a new plan in `docs/plans/`.

## Target (pinned)

| Setting | Value |
|---|---|
| **Blender** | `5.1.0` |
| **Track** | stable (not alpha / beta / RC) |
| **Renderer used for previews** | Eevee Next |
| **Color management** | AgX (default in 4.x+); never Filmic for committed previews |
| **Unit system** | Metric, 1 unit = 1 metre |
| **Y-up convention on glTF export** | Yes (Unity-friendly axes) |

If Blender 5.1 is not the upstream stable release at bootstrap time, the `asset-designer` falls back to the latest stable in the 4.x LTS line **and updates the row above with the fallback version + a `fallback_from: 5.1.0` note** before continuing. The bump back to 5.1 is plan-gated.

## Bundled exporters & importers (pinned)

| Tool | Version | Why |
|---|---|---|
| **glTF 2.0 (`io_scene_gltf2`)** | bundled with Blender 5.1 | Canonical export format per ADR-0008 §Export format. `.glb` is the only committed binary. |
| **OBJ / FBX exporters** | bundled, **not used** | Listed for completeness. Asset-design commits ship `.glb` only. |

The glTF exporter version is the one shipped inside Blender 5.1; do not install an out-of-tree replacement.

## Export settings (pinned)

Asset-design exports `.glb` with the following non-default settings:

| Setting | Value |
|---|---|
| Format | glTF Binary (`.glb`) |
| Include → Selected Objects | yes (the `asset-designer` selects before export) |
| Transform → +Y Up | yes |
| Geometry → Apply Modifiers | yes |
| Geometry → UVs | yes |
| Geometry → Normals | yes |
| Geometry → Tangents | yes |
| Geometry → Vertex Colors | yes |
| Materials → Materials | Export |
| Materials → Images | Automatic |
| Compression → Draco | **off** (Unity's glTFast importer plays better with uncompressed for the PoC) |
| Animation | enabled only if the asset has an action |
| Punctual Lights (KHR_lights_punctual) | enabled (ADR-0008 calls this out explicitly) |

If a future asset needs Draco compression or different normal handling, that asset is preceded by a manifest `notes:` line and (if recurring) a follow-up ADR.

## Companion add-on (`blender-mcp`)

The `blender-mcp` add-on is the MCP authoring surface for the `asset-designer` role. The version pin lives in `docs/engine-reference/mcp/VERSIONS.md`. Compatibility:

| Blender | `blender-mcp` revision |
|---|---|
| `5.1.0` | see `docs/engine-reference/mcp/VERSIONS.md::blender_mcp.pin` |
| `4.x LTS` (fallback) | same; the upstream add-on supports both 4.x and 5.x as of this pin |

## Rules

- **Pin exact versions.** No "latest", no ranges. The fallback to 4.x LTS is itself a pinned version, not "whatever 4.x is current".
- **One renderer for previews.** Eevee Next. Cycles is allowed for hand-authored stills but not for the two committed `screenshots/preview-*.png` per asset (ADR-0008 §Authoring artefact).
- **No add-on additions without a plan.** Adding any third-party Blender add-on (even free) requires a plan; the add-on becomes a transitive dependency of every asset that uses it.
- **Bump in lockstep with `blender-mcp`.** A Blender bump that breaks the add-on's compatibility table is a paired bump — write the plan against both.

## How to confirm the installed version

```bash
blender --version
# Expected first line: "Blender 5.1.0"
```

Inside Blender:

```
About Blender → version line matches.
Edit → Preferences → Get Extensions → Repositories → blender-mcp commit matches docs/engine-reference/mcp/VERSIONS.md.
```

The drift script `scripts/check-runtime-versions.py` does **not** invoke Blender (it has no headless mode contract here); the version match is human-verified at bootstrap and re-verified by the `asset-designer` at the start of every authoring session.

## Bumping policy

When a new Blender release lands, the `asset-designer` opens a plan with these checkpoints:

1. Read upstream release notes (specifically: glTF exporter changes, Python API breaks, Eevee Next behaviour).
2. Test one trivial asset round-trip: `download_polyhaven_asset` → `.glb` export → Unity glTF import → no visual diff.
3. Test one `execute_blender_code` recipe round-trip: re-run a committed recipe, verify deterministic output.
4. Bump this file's version row.
5. Bump `architecture.yaml::tooling.blender.version` in lockstep.
6. Bump `docs/engine-reference/mcp/VERSIONS.md::blender_mcp.compatible_blender` if the matrix changes.
7. Commit.

If any check fails, the bump plan converts into a "stay on `<current>` because `<reason>`" decision and ships an ADR amendment.
