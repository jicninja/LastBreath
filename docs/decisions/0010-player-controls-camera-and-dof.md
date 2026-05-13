---
id: ADR-0010-player-controls-camera-and-dof
type: decision
status: accepted
date: 2026-05-12
related: [ADR-0003, ADR-0004, ADR-0007, ADR-0009]
---

# ADR 0010: Player controls, 2.5D billboard, side-rig camera, and depth-of-field

## Context

`docs/engine-reference/unity/VERSION.md` pins Unity 6 LTS with `com.unity.inputsystem 1.11.2` and `com.unity.cinemachine 3.1.2`, sets the project to "Input System Package (New) only. Legacy disabled.", and ADR-0009 enforces the no-stale-API and DI rules. The canonical input pattern lives in `docs/process/unity-patterns.md` `§7 Input System patterns` (`UNITY-PATTERN-INPUT-SYSTEM`): consumers hold `[SerializeField] InputActionReference` and Enable/Disable on lifecycle. The GDD agrees the game is "2.5D HD" (line 11), and the TDD names "2.5D movement over a simple 3D environment" with "2D sprites for the character" (lines 18-22).

Despite the pins, three gaps shipped:

1. **The canonical `PlayerController` code example uses legacy input.** `docs/tdd/last-breath-poc-tdd.md` lines 302-336 reads `Input.GetAxisRaw("Horizontal")`, `Input.GetAxisRaw("Vertical")`, `Input.GetKey(KeyCode.LeftShift)`. The TDD is the file new agents copy from when scaffolding; the example contradicts `VERSION.md` and `UNITY-PATTERN-INPUT-SYSTEM`. Any `/review-gameplay --strict` run against code generated from this stub flags the diff.
2. **The SDD has no `CameraSystem` and `architecture.yaml::systems` has no `SYS-CAMERA`.** Cinemachine 3.1.2 is pinned but never wired into a contract. The SDD presentation-layer line ("UI, audio, lights, camera, visual effects." — line 38) names camera as presentation infrastructure but stops there. Nothing in the docs says perspective vs orthographic, FOV, follow damping, look-ahead, or depth of field. The level-designer and unity-specialist have no surface to cite.
3. **The billboard mechanism is undocumented.** SDD §Key Prefabs → Player lists "Sprite renderer or visual root" (line 811). That "or" is the gap. Nothing names how the character sprite faces the camera (Y-axis rotation in `LateUpdate` vs full quaternion alignment vs a shader-side billboard).

The user, in a planning session dated 2026-05-12, asked to make controls explicit and added two further requirements: the camera follows the character with a light lag, and the scene runs **significant depth of field**. They picked perspective projection (real bokeh DOF), side-rig with damping in X+Z (no look-ahead), keyboard plus gamepad (no mouse), and docs+plan scope (no code, since `src/` does not exist yet — Unity bootstrap is tracked as `PLAN-008`).

Authoring patterns considered:

- **Inline the contract into the TDD section, no ADR.** Rejected. ADR-0009 explicitly treats Cinemachine and Input System as load-bearing pins; a follow-up that names how they are used in gameplay belongs in `docs/decisions/`, not buried in a TDD subsection. Without an ADR, the rationale (why perspective, why side-rig, why DOF in Bokeh mode) is unfindable by grep on `docs/decisions/`.
- **One ADR per topic (input, camera, billboard, DOF).** Rejected. The four are interlocked: perspective projection is what makes the chosen DOF possible; the billboard depends on the camera transform; the input axes are XZ because the camera is side-on. Four ADRs would force four cross-citations on the same diff. ADR-0008's "one ADR per coherent decision cluster" shape applies.
- **Single ADR + SDD/TDD/registry updates + ready-to-run implementation plan (chosen).** One ADR carries the rationale. SDD adds `CameraSystem` as a first-class system and rewrites `PlayerController` responsibilities. TDD ships the explicit code and the new configs. `architecture.yaml` registers `SYS-CAMERA` and the new `CFG-*` entries. A new `docs/plans/012-player-controls-and-camera.md` is the executable plan, gated on `PLAN-008` (Unity bootstrap) and `PLAN-010` (validated level-design loop).

## Decision

Adopt **one ADR + SDD/TDD additions + four new `CFG-*` entries + one new `SYS-*` + a follow-up implementation plan**. Lock the following:

### 1. Input — Input System 1.11.2 only

- Author one committed action asset at `src/Assets/_Project/Input/PlayerControls.inputactions` containing one action map named `Gameplay` and the following actions:
  - `Move` — type `Value`, control type `Vector2`.
  - `Run` — type `Button`, interaction `Hold`.
  - `Interact` — type `Button`, interaction `Tap`.
  - `Pause` — type `Button`, interaction `Tap`.
- Bindings, both schemes shipped from day one:
  - Keyboard — `Move` reads composite 2D `WASD` and a second composite `Arrows`; `Run` reads `Left Shift`; `Interact` reads `E`; `Pause` reads `Esc`.
  - Gamepad — `Move` reads `<Gamepad>/leftStick`; `Run` reads `<Gamepad>/leftShoulder` (hold); `Interact` reads `<Gamepad>/buttonSouth`; `Pause` reads `<Gamepad>/start`.
- Consumers hold `[SerializeField] InputActionReference` per action and enable/disable in `OnEnable`/`OnDisable`, per `UNITY-PATTERN-INPUT-SYSTEM`. No `Input.GetAxis*`, no `Input.GetKey*`, no `Input.mousePosition`, anywhere under `src/Assets/_Project/**`.
- Suppression is by `action.Disable()`. When `GameState != Playing` (terminal open, paused, loading), the `Gameplay` action map is disabled. This composes with the existing SDD invariant "while a terminal is open, `PlayerController` movement and interaction input is suppressed" and with `GAMEPLAY-CODE-SAVE-NO-EVENTS-DURING-LOADING`.

### 2. Movement — 3D XZ plane, Y locked

- The character moves in **3D world space on the XZ plane**. Y is locked at 0 in the PoC (no jump, no gravity).
- Axis mapping is fixed: `Move.x → world X`, `Move.y → world Z`. `CharacterController.Move(new Vector3(input.x, 0f, input.y) * speed * Time.deltaTime)`.
- Run is hold-to-sprint and only takes effect while `Move` is non-zero. The speed values live in `CFG-PLAYER-MOVEMENT` (`PlayerMovementConfig`): default `WalkSpeed = 2.5`, `RunSpeed = 4.0` (carried over from the historical TDD constants).
- The controller does not own rotation. The visual root's rotation is the billboard's responsibility (item 3).

### 3. Billboard — Y-axis billboard in `LateUpdate`

- The character's visual root carries a `PlayerBillboard` MonoBehaviour. In `LateUpdate`, it sets `transform.rotation = Quaternion.Euler(0f, _camera.transform.eulerAngles.y, 0f)` so the sprite always faces the camera horizontally. Camera pitch and roll do not propagate to the sprite.
- The camera reference is resolved via `Camera.main` at `Awake` (Unity's built-in `MainCamera` tag is exempt from `GAMEPLAY-CODE-NO-TAG-STRING-LITERALS`, since it is engine-reserved). The reference is cached; `Camera.main` is not called per frame. If `_camera` is null in `LateUpdate` (editor edge case), the script no-ops.
- Mechanism is C# only. **No shader-side billboard.** A shader-side billboard couples the render pipeline to gameplay-visible orientation, makes EditMode testing harder, and adds nothing for the PoC.

### 4. Camera — perspective Cinemachine 3 side-rig

- Camera projection is **perspective**. FOV 35°. The rig sits offset from the player approximately `(0, 1.6, -6)` in world space; exact values live in `CFG-CAMERA-RIG` (`CameraRigConfig`).
- Implementation uses a **Cinemachine 3 `CinemachineCamera`** (the `Unity.Cinemachine` namespace component, not the deprecated `Cinemachine` CM2 `CinemachineVirtualCamera`) with a `CinemachinePositionComposer` extension.
  - Damping: `Damping.x ≈ 0.3`, `Damping.z ≈ 0.5`, `Damping.y = 0`. Dead zone narrow on X. No look-ahead.
  - Follow target is the `PlayerController` transform; the rig holds the reference, not the player.
- A pure-function helper `CameraRig.ComputeFollowPosition(target, previous, dt)` is extracted so EditMode tests can verify the lerp without needing Cinemachine at test time. The MonoBehaviour calls this helper to drive the offset.
- Orthographic projection is **rejected** by this ADR. Re-introducing orthographic requires an amendment.

### 5. Depth of field — URP `Volume` in Bokeh mode

- The scene carries one global URP `Volume` (`src/Assets/_Project/Volumes/Game.asset` profile) with a `DepthOfField` override in **Bokeh** mode. Defaults: `focusDistance` driven at runtime, `aperture = 5.6`, `focalLength = 70 mm`, `bladeCount = 6`. Exact values live in `CFG-CAMERA-DOF` (`CameraDofConfig`).
- A `CameraDofDriver` MonoBehaviour reads the URP `DepthOfField` override and writes `focusDistance.value = Vector3.Distance(camera.position, target.position)` every frame. The driver is read-only on game state (it reads the camera and the player transform; it does not call into `OxygenSystem`, `AgitationSystem`, `GameManager`, or any save path).
- Bokeh mode (not Gaussian) is mandatory: the user requirement is "DOF importante". Gaussian gives uniform blur; Bokeh produces the focal separation that justifies perspective in item 4.
- The driver guards against null `target` and null `Camera.main` (the latter only in EditMode harnesses). Production scenes always have both wired through the `LifetimeScope`.

## Alternatives rejected

- **Orthographic camera.** DOF on an orthographic camera in URP produces a flat blur with no depth cue. The user explicitly asked for "DOF importante"; orthographic contradicts the requirement.
- **Shader-side billboard.** Couples the render pipeline to gameplay orientation, hides the rotation from EditMode tests, and provides no benefit at PoC scope.
- **Look-ahead camera (Cinemachine `Tracked Dolly` or `Position Composer` with look-ahead damping).** The GDD line 103 forbids "fighting the input"; the user's stated intent is "follow a bit, no inertia drama". Look-ahead introduces overshoot and is hard to tune at PoC scope.
- **Full XZ follow with zero damping.** Reads as jittery on diagonal input and produces motion sickness in a horror PoC. Light damping is the agreed compromise.
- **Mouse-driven input.** The PoC has no cursor-driven UI, no aim, and no inventory. Mouse adds a binding surface for zero gain; defer until a feature genuinely needs it.
- **`PlayerInput` component instead of `InputActionReference`.** `PlayerInput` brings auto-wiring and a UnityEvent-based callback shape that conflicts with `UNITY-PATTERN-INPUT-SYSTEM` and with VContainer `[Inject]`. Stay on the lower-level `InputActionReference` pattern that the rest of the project already cites.

## Consequences

- **Easy.** Reviewer rules are already in place. `UNITY-PATTERN-INPUT-SYSTEM` (`docs/process/unity-patterns.md` `§7`), `GAMEPLAY-CODE-DI-LIFETIMESCOPE-ONLY-AT-ROOT`, and `GAMEPLAY-CODE-NO-TAG-STRING-LITERALS` cover the controller's surface area without new rule code. The diff that lands this ADR also fixes the legacy-`Input` violation already present in the TDD stub.
- **Easy.** No package additions. Cinemachine 3.1.2 and Input System 1.11.2 are already pinned by ADR-0009. The URP `Volume` framework is part of `com.unity.render-pipelines.universal 17.0.3`, also already pinned.
- **Easy.** New registry entries are additive: `SYS-CAMERA`, `CFG-PLAYER-MOVEMENT`, `CFG-PLAYER-INPUT`, `CFG-CAMERA-RIG`, `CFG-CAMERA-DOF`. No existing ID is renamed; `SYS-PLAYER` gains a `config:` reference but its publishes/subscribes stay identical.
- **Hard.** The TDD's `PlayerController` code example becomes the source of truth for the Input System pattern at PoC scale. Every future system that reads input must mirror its shape (`InputActionReference` + `OnEnable`/`OnDisable`). Drift will be caught by `/review-gameplay`.
- **Accepted loss.** The PoC ships with one rig and one DOF preset. Cinematic tuning (depth-aware focus pulls, anamorphic bokeh, vignette interaction) is out of scope. A follow-up plan can add a second rig (`CameraRig.Combat`, `CameraRig.Cinematic`) once a use case appears.
- **Mandatory tests** (added by `docs/plans/012-player-controls-and-camera.md`):
  - `PlayerControllerTests.Move_OnXZ_LocksYToZero` (EditMode).
  - `PlayerControllerTests.Update_WhenNotPlaying_DoesNotMove` (EditMode, mocks `GameManager`).
  - `CameraRigTests.ComputeFollowPosition_LerpsWithDamping` (EditMode, pure function).
  - `BillboardTests.LateUpdate_RotatesOnlyAroundY` (EditMode, mock camera transform).
  - `PocSmokeTests.PlayerWalksAndCameraFollows` (PlayMode, asserts `Move.performed → CharacterController moves → camera transform lerps`).

## References

- `docs/engine-reference/unity/VERSION.md` (lines 15, 24-25) — pin sources for Input System, Cinemachine, URP.
- `docs/process/unity-patterns.md` (lines 188-212) — `UNITY-PATTERN-INPUT-SYSTEM` template.
- `docs/gdd/last-breath-poc-gdd.md` (line 11, line 103) — 2.5D framing; "no fighting the input".
- `docs/tdd/last-breath-poc-tdd.md` (lines 18-22, 302-336) — assumptions and the legacy-Input stub this ADR replaces.
- `docs/sdd/last-breath-poc-sdd.md` (lines 73-90, line 38, line 408, line 811) — `PlayerController` section, presentation-layer note, terminal-suppression invariant, Player prefab.
- ADR-0003 (soft reviewer enforcement), ADR-0004 (identity-only SOs), ADR-0007 (level-design authoring flow — camera lives where the level-designer composes), ADR-0009 (runtime versions and DI).
