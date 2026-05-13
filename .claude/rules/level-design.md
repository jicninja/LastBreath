# Rules — Level Design

Applies to changes under `docs/levels/**`, `src/Assets/Scenes/**.unity`, `src/Assets/_Project/Prefabs/Level/**`, and `src/Assets/_Project/Config/Levels/**`. Owned by the `level-designer` role.

Rationale: ADR-0007. Canonical loop: `docs/process/level-design.md`. Authoring surface: `docs/process/unity-mcp.md`.

## `LEVEL-DESIGN-NO-DIRECT-UNITY-EDIT-WITHOUT-SPEC`

Every commit that changes `src/Assets/Scenes/**.unity` must also change the matching `docs/levels/<scene>/<scene>.layout.yaml`. The two are coupled: the `.unity` is the executable artifact, the YAML is the audit artifact, and they ship together.

Forbidden:

- A commit that modifies a `.unity` file without a corresponding spec diff.
- A commit that modifies the spec without a corresponding `.unity` diff (except when only fixing whitespace/comments in the YAML, which is rare because the YAML is generated).

Allowed:

- A commit that touches neither — pure docs work under `docs/levels/<scene>/README.md` or `sessions/`.

Cite: ADR-0007 `§Decision`; `docs/process/level-design.md` `§4`.

## `LEVEL-DESIGN-SPEC-IS-IDEMPOTENT`

`ApplySpec(DumpSpec(scene)) == scene` (modulo the non-load-bearing GUID noise `LevelSpec.ApplySpec` documents). Enforced by the EditMode test `LevelSpec_RoundtripsScene_IsIdempotent`.

Forbidden:

- Hand-editing a `.layout.yaml` to add fields the dumper does not produce. The YAML is generated; manual additions either get overwritten next session or break round-trip.
- Hand-editing a `.unity` file outside Unity (or outside the MCP). Use the editor.

Cite: ADR-0007 `§Decision`; `docs/process/level-design.md` `§7`.

## `LEVEL-DESIGN-LAYOUT-ID-REGISTERED`

Every `LAYOUT-*` referenced in a `.layout.yaml` must exist in `docs/registry/architecture.yaml` under `layouts:` with `status: active`. Reviewer fails the commit otherwise.

Forbidden:

- Inventing a `LAYOUT-*` ID in a spec without adding the registry entry first.
- Referencing a `LAYOUT-*` with `status: deprecated`.

Allowed:

- Adding a new `LAYOUT-*` entry to `architecture.yaml` in the same commit as the spec that first references it.

Cite: `AGENTS.md` `§Global rules` (Stable IDs); ADR-0007 `§Decision` (ID space).

## `LEVEL-DESIGN-NO-LOOSE-MAGIC`

Interactables, presence triggers, zone triggers, and gates wired into the scene reference asset objects, never string literals.

Forbidden:

- A `FlagSetter` or `FlagGate` configured with a string `flagId` instead of a `FlagDefinition` reference.
- A `PresenceEventTrigger` configured with a string event id instead of a `PresenceEventDefinition` reference.
- An `ObjectiveSystem`-bound interactable configured with a string objective id instead of an `ObjectiveDefinition` reference.

Allowed:

- The same MonoBehaviours wired through their inspector slots to the matching `.asset` files in `src/Assets/_Project/Config/`.

Cite: ADR-0004 `§Decision` (identity via `FlagDefinition`); SDD `§FlagSystem`, `§PresenceDirector`, `§ObjectiveSystem`.

## `LEVEL-DESIGN-INVARIANTS-PASS`

`LevelSpec.ValidateScene(scenePath)` returns no errors for every committed scene under `src/Assets/Scenes/**.unity`. Enforced by the EditMode test `LevelSpec_ValidateScene_PassesForCommittedLevels`.

Default invariants (per `docs/process/level-design.md` `§7`):

- Every `EnvironmentZoneTrigger` is non-overlapping with peer zone triggers.
- At least one trigger flips a `FlagDefinition` with `isSavePoint: true`.
- Every interactable references a `FlagDefinition` registered in `CFG-FLAG`.
- The objective node is reachable from `PlayerSpawn` along the navigable surface.

Cite: ADR-0007 `§Decision`; `docs/process/level-design.md` `§7`.

## `LEVEL-DESIGN-NO-GAMEPLAY-CODE`

A level-design commit does not change `src/Assets/_Project/Scripts/**`. Level-design and gameplay-code changes belong to different roles and different plans.

Forbidden:

- Touching `.cs` files under `src/Assets/_Project/Scripts/**` in a commit whose primary change is a `.unity` or `.layout.yaml`.

Allowed:

- A cross-role plan that explicitly groups a gameplay-code change with a level-design change, citing both roles in the plan's "Owners" section.

Cite: `AGENTS.md` `§Roles`; ADR-0007 `§Decision` (role separation).

## `LEVEL-DESIGN-USES-APPROVED-ART-ONLY`

Every mesh, prefab, or material path that a `*.layout.yaml` references under `src/Assets/_Project/Art/` resolves to an asset whose `art/<asset>/manifest.yaml` has `approved: true` and `imported_at != null`. The reviewer cross-checks via `scripts/check-art-sync.py`; a failed check is a `LEVEL-DESIGN-USES-APPROVED-ART-ONLY` violation.

Forbidden:

- A layout reference to a file under `src/Assets/_Project/Art/` whose manifest is `approved: pending` or `approved: false`.
- A layout reference to a path under `src/Assets/_Project/Art/` that has no manifest at all (file dropped into Unity outside the import gate).

Allowed:

- A layout pending an asset can leave the reference field empty (`prefab: null`) and add a note to the next session log. The reviewer flags an empty reference as `non_blocking_notes` rather than a violation, expecting the asset-design loop to catch up.

Cite: ADR-0008 `§Decision` (Import gate); `.claude/rules/asset-design.md` `ASSET-DESIGN-SYNC-PARITY`.

## `LEVEL-DESIGN-BLENDER-READ-ONLY`

The `level-designer` may call only the **read-only** subset of `blender-mcp` listed in `docs/process/blender-mcp.md` `§4` under "level-designer (read-only subset)". Author verbs are reserved for the `asset-designer`.

Allowed verbs for `level-designer`:

- `get_scene_info`, `get_object_info`, `get_viewport_screenshot`.
- `*_status`, `poll_*`.
- `search_polyhaven_assets`, `get_polyhaven_categories`, `get_sketchfab_model_preview`, `search_sketchfab_models`.

Forbidden verbs for `level-designer`:

- `execute_blender_code` — even an "innocent, read-only" Python snippet. Hard ban; no exceptions.
- `download_polyhaven_asset`, `download_sketchfab_model`, `generate_*_model_*`, `import_generated_asset*`, `set_texture`.

If a level-design session needs Blender authoring (the asset is wrong, needs to grow, needs a material tweak), stop, write a hand-off line in the session log naming the asset and the change, and resume after the asset-designer ships a new revision.

Cite: ADR-0008 `§Decision` (Roles); `docs/process/blender-mcp.md` `§4`.

## `LEVEL-DESIGN-SESSION-LOG-PRESENT`

Every commit that changes `src/Assets/Scenes/**.unity` or `docs/levels/<scene>/<scene>.layout.yaml` adds a session log under `docs/levels/<scene>/sessions/session-NNNN.md` with the four sections from `docs/process/level-design.md` `§6` (Goal, What landed, What got rejected, Open questions).

Forbidden:

- A scene-modifying commit with no session log.
- A session log missing one of the four mandatory sections.

Allowed:

- A commit that bundles multiple atomic changes from the same iteration session into one `session-NNNN.md` (a session can span several MCP iterations as long as the snapshot ritual runs once at the end).

Cite: ADR-0007 `§Consequences`; `docs/process/level-design.md` `§6`.

## `LEVEL-DESIGN-PREFAB-DISCIPLINE`

Every GameObject that appears more than once in a committed scene, or that any system instantiates at runtime, lives as a prefab under `src/Assets/_Project/Prefabs/<Category>/`. In `.unity` scene YAML, every such instance carries `m_PrefabInstance` and a non-zero `m_CorrespondingSourceObject` — the prefab connection is intact.

Forbidden:

- A committed scene that contains a flat GameObject hierarchy where a prefab would naturally apply (three corridor panels written inline instead of three prefab instances).
- Calling `PrefabUtility.UnpackPrefabInstance(...)` against a committed scene. The "unpack" operation in the editor is a working-tree affordance, not a commit-tree state.
- Adding a new component to a prefab instance in a scene when the same component should live on the prefab itself (the scene becomes the source of truth instead of the prefab).

Allowed:

- One-off scene-only GameObjects (a unique light probe, an environment volume) that have no reuse value. These do not need a prefab.
- Scene-level overrides on prefab instances when they are visibly minimal (a transform, a single material slot). Anything broader belongs as a variant (see `LEVEL-DESIGN-VARIANTS-OVER-DUPLICATION`).

Cite: `docs/process/unity-patterns.md` `§14` (`UNITY-PATTERN-PREFAB-DISCIPLINE`).

## `LEVEL-DESIGN-VARIANTS-OVER-DUPLICATION`

A family of "same thing, different state/config" objects (intact / damaged / dark; common / rare / boss) is authored as a base prefab plus prefab variants. Variant `.prefab` YAML carries `m_VariantParent` pointing at the base; flat duplicates produced by `Duplicate` carry `m_VariantParent: {fileID: 0}` and are forbidden.

Forbidden:

- Two or more prefabs under the same `Prefabs/<Category>/` folder with near-identical hierarchies and `m_VariantParent: {fileID: 0}` on each. This is duplicate-and-modify, not variants.
- Renaming or moving a base prefab without updating dependent variants — the variant's `m_VariantParent` reference must remain valid (Unity rewrites it on rename inside the editor; do not hand-edit the YAML).

Allowed:

- Single base prefab with one or more `<Name>.<Suffix>.prefab` files where each variant declares a non-zero `m_VariantParent`.
- Two prefabs whose names look similar but whose hierarchies and purposes diverge (`CorridorPanel.prefab` and `CorridorWall.prefab`) — they are unrelated, not duplicate-and-modify.

Cite: `docs/process/unity-patterns.md` `§15` (`UNITY-PATTERN-VARIANTS`).

## `LEVEL-DESIGN-GPU-INSTANCING-ENABLED`

Every `.mat` under `src/Assets/_Project/Art/**/*.mat` whose shader supports it has `m_EnableInstancingVariants: 1` (the YAML form of "Enable GPU Instancing"). Per-renderer tweaks at runtime go through `MaterialPropertyBlock`, not through assigning `Renderer.material` (which clones the material and breaks instancing).

Forbidden:

- A material with `m_EnableInstancingVariants: 0` whose shader is on the "supports instancing" list (URP/Lit, URP/Unlit, URP/SimpleLit, Standard, Standard (Specular)) and which is referenced by more than one renderer in any committed scene or prefab.
- C# under `_Project/Scripts/` that assigns `_renderer.material.<anything>` for visual variation. Use `MaterialPropertyBlock`.

Allowed:

- `m_EnableInstancingVariants: 0` on a material whose shader does not support instancing (most particle/sprite shaders, third-party shaders without `#pragma multi_compile_instancing`). The opt-out is documented in the matching `art/<asset>/manifest.yaml` under `notes:`.
- `Renderer.sharedMaterial` reads anywhere; only writes via `.material` are flagged.

Cite: `docs/process/unity-patterns.md` `§16` (`UNITY-PATTERN-GPU-INSTANCING`).

## `LEVEL-DESIGN-TAGS-REGISTERED`

Every tag declared in `src/ProjectSettings/TagManager.asset` (beyond Unity's built-ins: `Untagged`, `Respawn`, `Finish`, `EditorOnly`, `MainCamera`, `Player`, `GameController`) has a matching entry in `docs/registry/architecture.yaml` under `tags:` with id `TAG-<NAME-IN-UPPER-KEBAB>`, status `active | deprecated`, and a one-line `purpose`.

Forbidden:

- Adding a tag to `TagManager.asset` without adding the registry entry in the same commit.
- Reusing a built-in tag (`Player`, `MainCamera`) for a different purpose. Add a new tag instead.
- Inventing a `TAG-*` id in a scene/prefab field without registering it. The level-designer cross-checks the new tag exists in the registry before referencing it.

Allowed:

- Unity's built-in tags (the 7 listed above) without registry entries — they are reserved by the engine.
- An empty `tags:` section in `architecture.yaml` while no project-specific tags exist yet. The level-designer adds the section header in the same PR as the first tag.

Cite: `docs/process/unity-patterns.md` `§17` (`UNITY-PATTERN-TAGS-AND-LAYERS`). Companion rule for C# usage: `.claude/rules/gameplay-code.md` (`GAMEPLAY-CODE-NO-TAG-STRING-LITERALS`).
