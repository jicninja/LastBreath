---
id: PLAN-009-levelspec-and-unity-mcp
type: plan
status: proposed
related: [ADR-0007, ADR-0009, PLAN-008, PLAN-010]
followups: [PLAN-010]
---

# Plan 009 — LevelSpec utility + unity-mcp wiring

> Code-creation plan. Ships the three Editor static methods (`DumpSpec`, `ApplySpec`, `ValidateScene`) ADR-0007 promises, plus the `unity-mcp` registration so PLAN-010 can drive Unity from an agent.

## Code deliverables

| Path | Purpose |
|---|---|
| `src/Assets/_Editor/LevelSpec/LevelSpec.cs` | `namespace LastBreath.Editor.Levels`. Public static API: `LayoutSpec DumpSpec(Scene)`, `void ApplySpec(LayoutSpec, Scene)`, `List<ValidationError> ValidateScene(Scene)`. `LayoutSpec` POCO inline (sealed types for trigger / light / prefab-ref kinds). `EditorOnly`-tagged GameObjects skipped on dump |
| `src/Assets/_Editor/LevelSpec/LayoutSpecYaml.cs` | Hand-rolled YAML emitter + parser scoped to `LayoutSpec`. No anchors, no flow style, no arbitrary depth. Avoids YamlDotNet dep |
| `src/Assets/_Editor/LevelSpec/LevelSpecMenu.cs` | `[MenuItem("LastBreath/Level/Dump Spec")]`, `Apply Spec`, `Validate Scene`. Dump default path `docs/levels/<active-scene>/<scene>.layout.yaml` |
| `src/Assets/Tests/EditMode/LevelSpecTests.cs` | `LevelSpec_RoundtripsScene_IsIdempotent`, `LevelSpec_ValidateScene_PassesForCommittedLevels`, `LevelSpec_DumpSpec_IgnoresEditorOnly` |
| `src/Assets/Tests/EditMode/Fixtures/RoundtripFixture.unity` | Fixture with mixed GameObjects, one `EditorOnly`-tagged |
| `.mcp.json` | Add `unity_mcp` server. Resolve exact command via `context7.query-docs` on `justinpbarnett/unity-mcp` (source pinned in `architecture.yaml::tooling.mcp_servers.unity_mcp`) |
| `docs/registry/architecture.yaml::tooling.mcp_servers.unity_mcp.pin` | Fill git SHA at install time |

`ValidateScene` invariants (per `LEVEL-DESIGN-INVARIANTS-PASS`):

1. Zone-trigger BoxColliders non-overlapping.
2. At least one trigger flips a `FlagDefinition` with `isSavePoint: true` — **skip-pass when zero `FlagDefinition` assets exist** in the project (compile-passes before SYS-FLAGS lands).
3. Every interactable references a registered `FlagDefinition` — same skip condition.
4. Objective-reachability — emitted as `non_blocking_note`, not implemented this plan.

Round-trip equality assertion: `ApplySpec(DumpSpec(scene))` → `DumpSpec` again → byte-equal modulo non-load-bearing GUID noise (the exact noise set documented in `LevelSpec.cs` as a sealed list of fields).

## Out of scope

- Composing any scene (PLAN-010).
- `LAYOUT-*` or `TAG-*` registry entries (PLAN-010).
- Authoring level prefabs.
- `blender-mcp` (PLAN-011).
- Validating art references inside `ValidateScene` (handled by `scripts/check-art-sync.py`).

## Owner

`gameplay-programmer` (Editor scope) for the C#. `unity-specialist` for `.mcp.json`.

## Verification

- [ ] `LevelSpec_RoundtripsScene_IsIdempotent` passes 3 runs in a row (catch flakiness)
- [ ] `LevelSpec_ValidateScene_PassesForCommittedLevels` passes against `Bootstrap.unity`
- [ ] `LevelSpec_DumpSpec_IgnoresEditorOnly` passes
- [ ] `LastBreath/Level/Dump Spec` on `Bootstrap.unity` writes a committable YAML (no absolute paths)
- [ ] `LastBreath/Level/Validate Scene` on `Bootstrap.unity` reports zero errors
- [ ] `claude mcp list` reports `unity_mcp` connected
- [ ] `architecture.yaml::tooling.mcp_servers.unity_mcp.pin` is non-null
- [ ] `python3 scripts/check-runtime-versions.py` → exit 0
