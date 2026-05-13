---
id: ADR-0007-level-design-authoring-flow
type: decision
status: accepted
date: 2026-05-12
related: [SYS-ENVIRONMENT, SCENE-CORREDOR-C7, ADR-0004, ADR-0005]
---

# ADR 0007: Level design authoring — MCP-iterate, spec-after snapshot

## Context

The PoC has roles for design intent (`game-designer`), system contracts (`systems-designer`), C# implementation (`gameplay-programmer`), Unity infra (`unity-specialist`), narrative, QA, and review — but no role owns **scene composition**: putting nodes, prefabs, triggers, lights, checkpoints, and zone volumes inside a `.unity` scene so the GDD intent (e.g., `SCENE-CORREDOR-C7`) becomes a playable level. The user is solo, plays the role of validator (programmer + game designer), and wants the assistant to actually add things in the Unity editor — not just describe them.

Three authoring patterns were considered:

- **Live MCP edit (spec-first)**. A canonical declarative `*.layout.yaml` is the source of truth; a Unity-MCP server applies it; the reviewer reviews the YAML.
- **Live MCP edit (spec-after, chosen)**. The live Unity scene is the iteration surface. At the end of every session, an Editor utility serialises the scene to a canonical `*.layout.yaml`. The YAML is the audit artifact; the `.unity` is the executable artifact.
- **`[MenuItem]` builder scripts only**. The assistant writes C# Editor scripts that build scenes from code. No live editing.
- **Direct YAML edits on `.unity` / `.prefab`**. The assistant hand-edits Unity's serialised text format.

## Decision

Adopt **live MCP edit with spec-after snapshot**.

- **Authoring surface**: the Unity editor, driven by Justin P Barnett's `unity-mcp` (see `docs/process/unity-mcp.md` for setup and capability matrix). Iteration is creative and free; the assistant adds, moves, deletes, and reparents nodes until the user is satisfied.
- **Audit artifact**: at end of session, an Editor utility `LevelSpec.DumpSpec(scenePath)` serialises the scene to `docs/levels/<scene>/<scene>.layout.yaml`. The reviewer reads the spec + a short session log + two committed viewport screenshots — never the raw `.unity` diff.
- **Idempotency**: `LevelSpec.ApplySpec(yaml)` must rebuild the scene from the spec. `ApplySpec(DumpSpec(scene)) == scene` is enforced by an EditMode test. If a manual Unity edit happens between sessions, the next `DumpSpec` rewrites the spec to match — no silent drift.
- **Invariants**: `LevelSpec.ValidateScene(scenePath)` runs in EditMode and asserts level-design contracts (zone triggers non-overlapping, at least one save-point flag wired, every interactable references a registered `CFG-FLAG`, player spawn reachable to objective).
- **New role**: `level-designer` owns `docs/levels/**`, `src/Assets/Scenes/**.unity` composition, level prefabs under `src/Assets/_Project/Prefabs/Level/**`, and level configs under `src/Assets/_Project/Config/Levels/**`. Does not touch gameplay C# (`gameplay-programmer`), engine config / asmdef (`unity-specialist`), GDD intent (`game-designer`), or narrative copy (`narrative-director`).
- **New ID prefix**: `LAYOUT-*` identifies named sub-sections inside a scene (cabin, corridor, maintenance, airlock, exterior, antenna panel, return). `SCENE-*` remains the container.
- **New rules** (`.claude/rules/level-design.md`): every commit that changes `src/Assets/Scenes/**.unity` must also change the matching `*.layout.yaml`; every referenced `LAYOUT-*` must exist in `architecture.yaml`; `ValidateScene` must pass; the diff cannot include gameplay C# (cross-role plans must say so).

## Alternatives considered

- **Spec-first**. Rejected because level design is iterative and creative — drafting the full YAML before laying anything out forces premature commitment, slows the feedback loop, and produces specs that are partially fictional until rebuilt. Spec-after preserves the same auditability without the rigidity. The spec format and `ApplySpec` utility are kept anyway, so a future "rebuild from spec" workflow is available without re-architecting.
- **`[MenuItem]` builders only**. Rejected because authoring a varied scene by code is verbose, hostile to small visual tweaks, and rewards over-abstraction. The Editor utility `LevelSpec` still provides high-level menu items (`Dump Spec`, `Apply Spec`, `Validate`), but those are session bookends, not the authoring surface.
- **Direct `.unity` / `.prefab` YAML edits**. Rejected because Unity's serialised format relies on `fileID` and `m_LocalIdentifierInFile` references that are easy to corrupt by hand. `.asset` ScriptableObjects are stable enough to edit directly when needed; scenes and prefabs are not.
- **No MCP, no role, level design ad-hoc inside `game-designer`**. Rejected because scene composition is a distinct discipline with its own invariants (zone coverage, navigation reachability, save-point wiring) that benefit from a dedicated rule file and reviewer scope.

## Consequences

- **Easy.** Iteration is fast and visual. The user validates in the editor as they go. The audit artifact is one YAML and one markdown log per session, both diff-friendly. The Unity-MCP can be swapped for a different implementation later without touching the spec format.
- **Hard.** Every level-design session must end with the snapshot ritual: `DumpSpec`, `ValidateScene`, two screenshots, a short markdown session log, and an idempotency check. Skipping the ritual breaks the audit trail. The `level-design-session` skill exists to enforce the order.
- **Accepted loss.** The `.unity` file is committed but is not the human-review surface — reviewers do not read it. If the spec and the `.unity` desynchronise (someone edits in Unity without re-dumping), the next session's `DumpSpec` silently corrects it; we accept that the previous commit's spec might lag reality by one session.
- **Mandatory tests:**
  - `LevelSpec_RoundtripsScene_IsIdempotent` — EditMode, runs `ApplySpec(DumpSpec(scene))` against a scratch copy and asserts equality (modulo non-load-bearing GUID noise).
  - `LevelSpec_ValidateScene_PassesForCommittedLevels` — EditMode, fails if any committed scene under `src/Assets/Scenes/**.unity` violates `LevelSpec.ValidateScene`.
- **Mandatory rules** (`.claude/rules/level-design.md`):
  - `LEVEL-DESIGN-NO-DIRECT-UNITY-EDIT-WITHOUT-SPEC`
  - `LEVEL-DESIGN-SPEC-IS-IDEMPOTENT`
  - `LEVEL-DESIGN-LAYOUT-ID-REGISTERED`
  - `LEVEL-DESIGN-NO-LOOSE-MAGIC`
  - `LEVEL-DESIGN-INVARIANTS-PASS`
  - `LEVEL-DESIGN-NO-GAMEPLAY-CODE`

## Notes

`LevelSpec.cs`, the Editor-only utility that implements `DumpSpec` / `ApplySpec` / `ValidateScene`, lands in a subsequent plan once the Unity project is initialised. The methodology in this ADR is engine-MCP-agnostic at the spec-format level: if `unity-mcp` is deprecated or replaced, the spec and the menu items remain stable.
