---
id: PLAN-012
type: plan
layer: process
status: proposed
related: [ADR-0009, ADR-0010, PLAN-008, PLAN-010, SYS-PLAYER, SYS-CAMERA]
---

# Plan 012 — Player controls, billboard, and side-rig camera with DOF

Implements ADR-0010 as a runnable plan. Ships the explicit Input System wiring, the 2.5D Y-axis billboard, the Cinemachine 3 side-rig, and the URP Volume depth-of-field driver. Replaces the legacy-`Input` PoC stub historically present in the TDD.

## Context

ADR-0010 settled the design: Input System 1.11.2 only, XZ movement with Y locked, Y-axis billboard in `LateUpdate`, perspective Cinemachine 3 side-rig with light X+Z damping, URP Volume DOF in Bokeh mode. The SDD, TDD, registry, and glossary were updated in the same change. This plan is the executable counterpart: author the action asset, write the C# under `_Project/`, build the prefabs, register the systems on the `LifetimeScope`, write the tests, and pass `/review-gameplay --strict`.

The plan is **gated on `PLAN-008` (Unity project bootstrap) and `PLAN-010` (validate level-design loop)** and stays `proposed` until both gates are done. Without `src/Assets/_Project/`, there is no surface to write code into; without a validated scene, there is nothing to drop the player and camera prefabs into. Verify the gate by `cat src/ProjectSettings/ProjectVersion.txt` matching `m_EditorVersion: 6000.0.32f1` and `src/Packages/manifest.json` containing `com.unity.inputsystem 1.11.2`, `com.unity.cinemachine 3.1.2`, `com.unity.render-pipelines.universal 17.0.3`.

## Decisions inherited (from ADR-0010)

1. Input System 1.11.2; one action asset (`PlayerControls.inputactions`), one map (`Gameplay`), four actions (`Move`, `Run`, `Interact`, `Pause`), keyboard + gamepad bindings.
2. Movement is `CharacterController.Move(new Vector3(x, 0, z))` on the XZ plane.
3. `PlayerBillboard` MonoBehaviour on the visual root; Y-axis rotation only, in `LateUpdate`, camera read from `Camera.main` at `Awake`.
4. Cinemachine 3 `CinemachineCamera` + `CinemachinePositionComposer`, perspective FOV 35°, damping X 0.3 / Y 0 / Z 0.5, no look-ahead.
5. URP global `Volume` with `DepthOfField` in **Bokeh** mode, `focusDistance` driven each `LateUpdate` by `CameraDofDriver` from the player-camera distance.

## Owners

- `gameplay-programmer` — primary. Authors all `.cs` under `_Project/Scripts/Player/` and `_Project/Scripts/Camera/`, the tests, and the `LifetimeScope` registration.
- `unity-specialist` — Cinemachine + URP Volume wiring. Authors `CameraRig.prefab`, the `Volume` profile asset, the post-process layer setup, and reviews the `.inputactions` editor settings.
- `level-designer` — drags the `Player.prefab` and `CameraRig.prefab` into `SCN_PoC_C7`, sets the player spawn, runs the snapshot ritual (DumpSpec / Validate / screenshots / session log).
- `qa-tester` — runs the EditMode + PlayMode smoke, reports the PoC golden-path video.

## Deliverables

| Path | Action | Owner |
|---|---|---|
| `src/Assets/_Project/Input/PlayerControls.inputactions` | create — one action map `Gameplay` with four actions and the keyboard + gamepad bindings from ADR-0010 §Decision item 1 | gameplay-programmer |
| `src/Assets/_Project/Scripts/Player/PlayerController.cs` | create — exact body from `docs/tdd/last-breath-poc-tdd.md` `§PlayerController` | gameplay-programmer |
| `src/Assets/_Project/Scripts/Player/PlayerState.cs` | create — `IsMoving`, `IsRunning`, `CurrentZone` per TDD | gameplay-programmer |
| `src/Assets/_Project/Scripts/Player/PlayerMovementConfig.cs` | create — `ScriptableObject` with `WalkSpeed`, `RunSpeed` per TDD | gameplay-programmer |
| `src/Assets/_Project/Scripts/Player/PlayerBillboard.cs` | create — exact body from TDD `§PlayerBillboard` | gameplay-programmer |
| `src/Assets/_Project/Scripts/Camera/CameraRig.cs` | create — exact body from TDD `§CameraRig` including the static `ComputeFollowPosition` helper | gameplay-programmer |
| `src/Assets/_Project/Scripts/Camera/CameraRigConfig.cs` | create — `ScriptableObject` per TDD | gameplay-programmer |
| `src/Assets/_Project/Scripts/Camera/CameraDofDriver.cs` | create — exact body from TDD `§CameraDofDriver` | gameplay-programmer |
| `src/Assets/_Project/Scripts/Camera/CameraDofConfig.cs` | create — `ScriptableObject` per TDD | gameplay-programmer |
| `src/Assets/_Project/Prefabs/Player.prefab` | create — root `GameObject` with `CharacterController` + `PlayerController` + visual-root child carrying `SpriteRenderer` (placeholder sprite) + `PlayerBillboard` | unity-specialist |
| `src/Assets/_Project/Prefabs/CameraRig.prefab` | create — `CinemachineCamera` (perspective, FOV 35°, `CinemachinePositionComposer` extension wired from `CameraRigConfig`) + `Volume` (Global, profile asset `Game.asset`) + `CameraRig` + `CameraDofDriver` | unity-specialist |
| `src/Assets/_Project/Volumes/Game.asset` | create — `VolumeProfile` with a `DepthOfField` override (mode Bokeh; default `aperture 5.6`, `focalLength 70`, `bladeCount 6`; `focusDistance` placeholder, runtime-driven) | unity-specialist |
| `src/Assets/_Project/Config/Player/PlayerMovementConfig.asset` | create — `WalkSpeed 2.5`, `RunSpeed 4.0` | gameplay-programmer |
| `src/Assets/_Project/Config/Camera/CameraRigConfig.asset` | create — `OffsetX 0`, `OffsetY 1.6`, `OffsetZ -6`, `DampingX 0.3`, `DampingY 0`, `DampingZ 0.5`, `FieldOfView 35` | unity-specialist |
| `src/Assets/_Project/Config/Camera/CameraDofConfig.asset` | create — `Aperture 5.6`, `FocalLength 70`, `BladeCount 6` | unity-specialist |
| `src/Assets/_Project/Scripts/Bootstrap/GameLifetimeScope.cs` | update — register `PlayerController`, `CameraRig`, `CameraDofDriver`, and `GameManager` if not already; `[SerializeField]` the action asset + four `InputActionReference`s for the controller; `[SerializeField]` the configs | gameplay-programmer |
| `src/Assets/Scenes/SCN_PoC_C7.unity` | update — drop the `Player.prefab` and `CameraRig.prefab` into the scene; wire the rig's `_target` to the player's transform | level-designer |
| `tests/EditMode/PlayerControllerTests.cs` | create — `Move_OnXZ_LocksYToZero`, `Update_WhenNotPlaying_DoesNotMove`, `Run_GatesOnIsMoving` | gameplay-programmer |
| `tests/EditMode/CameraRigTests.cs` | create — `ComputeFollowPosition_LerpsWithDamping`, `ComputeFollowPosition_LocksY` | gameplay-programmer |
| `tests/EditMode/BillboardTests.cs` | create — `LateUpdate_RotatesOnlyAroundY` (mock camera transform; assert pitch/roll are zero) | gameplay-programmer |
| `tests/PlayMode/PocSmokeTests.cs` | update — add `PlayerWalksAndCameraFollows` covering "press Move → CharacterController displaces → rig position lerps in X+Z, Y unchanged" | qa-tester |
| `docs/plans/README.md` | update — keep the row for plan 012 aligned with the plan frontmatter | gameplay-programmer |

## Phases

### Phase A — input asset and player runtime

1. Create `PlayerControls.inputactions` via the Unity Editor `.inputactions` editor. Author one map `Gameplay` with the four actions and the bindings from ADR-0010 §Decision item 1. Save and commit; verify the JSON shape via `git diff` (no hand edits afterwards).
2. Author the four `.cs` files under `_Project/Scripts/Player/`. Compile-check after each file.
3. Author the two `ScriptableObject` configs under `_Project/Config/Player/` and `_Project/Config/Camera/` (only `PlayerMovementConfig.asset` in this phase).

### Phase B — camera and DOF runtime

4. Author the four `.cs` files under `_Project/Scripts/Camera/`. Compile-check.
5. Create the URP `VolumeProfile` asset `Game.asset` with the `DepthOfField` override in Bokeh mode and the placeholder values from ADR-0010 §Decision item 5.
6. Create the two camera config assets (`CameraRigConfig.asset`, `CameraDofConfig.asset`).

### Phase C — prefabs and scene wiring

7. Author `Player.prefab`: root with `CharacterController` and `PlayerController` (drag the action references and the movement config), child visual root with `SpriteRenderer` (placeholder white pixel) and `PlayerBillboard`.
8. Author `CameraRig.prefab`: `CinemachineCamera` (perspective FOV 35°, `CinemachinePositionComposer` extension), a `Volume` set to Global with the `Game.asset` profile, the `CameraRig` MonoBehaviour wired to the `CinemachineCamera` and the rig config, the `CameraDofDriver` wired to the `Volume` and the DOF config.
9. Drop both prefabs into `SCN_PoC_C7`. Wire `CameraRig._target` to the player's transform and `CameraDofDriver._target` likewise. Set the `MainCamera` tag on the rig's Unity Camera component (the one Cinemachine drives).

### Phase D — composition root

10. Update `GameLifetimeScope` to register `GameManager`, `PlayerController`, `CameraRig`, `CameraDofDriver`. Decide between container-resolved vs `[SerializeField]`-bound action references; default to `[SerializeField]` on the controller (ADR-0009 §DI keeps inspector binding for asset references).

### Phase E — tests and review

11. Author the three EditMode test files. Mock `GameManager` via a simple test double; the controller's `[Inject]` field is settable in tests through a constructor or reflection helper (project convention; cite a precedent in EditMode tests if one exists).
12. Extend `PocSmokeTests` with `PlayerWalksAndCameraFollows`. Use the Input System test helpers (`InputTestFixture`) to inject a `Move.x = 1` value for 0.5 s and assert displacement and camera position deltas.
13. Run all EditMode + PlayMode tests. Boot `SCN_PoC_C7.unity` from the editor; visually verify the rig follows with damping and the DOF blurs the background.
14. Dispatch `/review-gameplay --strict` on the diff. The reviewer must flag zero rule violations, recognise the new `SYS-CAMERA` and `CFG-*` IDs, and cite ADR-0010 against the controller and rig classes.
15. Update `docs/plans/README.md` to list plan 012 as `active` and link the scene smoke and the ADR.

## Verification

1. `grep -nE "Input\.(GetAxis|GetKey|GetButton)" src/Assets/_Project/Scripts/` returns zero matches.
2. `grep -nE "InputActionReference" src/Assets/_Project/Scripts/Player/` returns at least four matches (one per action slot) on `PlayerController.cs`.
3. `grep -rE "Cinemachine\.CinemachineVirtualCamera" src/Assets/_Project/` returns zero (CM2 is forbidden; CM3 lives in `Unity.Cinemachine`).
4. The Unity Editor opens `SCN_PoC_C7.unity` without warnings on Cinemachine or URP.
5. Pressing `W` / `<Gamepad>/leftStick up` moves the player on `+Z`. Pressing `D` / right-stick-x moves on `+X`. Holding `Shift` / `<Gamepad>/leftShoulder` switches to `RunSpeed`. `Esc` opens the pause path (`GameManager.SetState(Paused)` if implemented; otherwise `Pause` action is wired but unconsumed and the unconsumed state is logged in the session note).
6. The visual background blurs in Bokeh mode; the player stays sharp; moving away increases the blur on the far end of the corridor.
7. `tests/EditMode` and `tests/PlayMode` runs are green.
8. `/review-gameplay --strict` returns no violations.

## Out of scope

- Animation system / sprite-sheet authoring (the visual root ships with a placeholder white pixel sprite).
- Multi-rig setups (combat, cinematic). One rig at PoC scope.
- Mouse / touch input. Keyboard + gamepad only.
- Saved control rebinding UI. Bindings are committed in the action asset.
- Cinematic DOF rack-focus pulls. The driver follows the player; bespoke focus events come later.

## Open questions (decide during execution)

- `PlayerInput` vs `InputActionReference`. ADR-0010 picks the latter; the plan keeps that decision unless the action asset's "Generate C# Class" tooling proves significantly faster. If a switch is warranted, amend ADR-0010 first.
- Pause action ownership. The current plan wires `Pause` on the action asset but leaves the consumer to a follow-up (GameManager pause path is out of scope). Acceptable for the PoC; document in the scene session log.
- Camera rotation around Y for "look at the player from a slight angle" — left at zero offset in this plan. Adjust `OffsetX` if the corridor layout demands a different angle; values change in `CameraRigConfig.asset`, no code change.
