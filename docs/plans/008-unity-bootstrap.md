---
id: PLAN-008-unity-bootstrap
type: plan
status: proposed
related: [ADR-0009, PLAN-009, PLAN-010]
followups: [PLAN-009]
---

# Plan 008 — Unity project bootstrap

> Code-creation plan. Ships the empty Unity 6 LTS project: pinned packages, asmdef layout, an empty `GameLifetimeScope`, and one passing smoke test. No gameplay logic.

## Code deliverables

| Path | Purpose |
|---|---|
| `src/ProjectSettings/ProjectVersion.txt` | `m_EditorVersion: 6000.0.32f1` |
| `src/Packages/manifest.json` | Pins per `architecture.yaml::tooling.unity.packages` (URP 17.0.3, Input System 1.11.2, Cinemachine 3.1.2, Test Framework 1.4.5, Addressables 2.3.16, VContainer 1.16.9 via OpenUPM scope, UniTask 2.5.10 via Git URL) |
| `src/Assets/Scenes/Bootstrap.unity` | Main Camera + Directional Light + one `GameLifetimeScope` GameObject |
| `src/Assets/_Project/Scripts/Bootstrap/GameLifetimeScope.cs` | `public sealed class GameLifetimeScope : VContainer.Unity.LifetimeScope` with empty `Configure(IContainerBuilder)` override. Namespace `LastBreath.Bootstrap` |
| `src/Assets/_Project/Scripts/LastBreath.Gameplay.asmdef` | refs: `VContainer`, `VContainer.Unity`, `UniTask`, `Unity.InputSystem` |
| `src/Assets/_Editor/LastBreath.Editor.asmdef` | `includePlatforms: [Editor]`; refs `LastBreath.Gameplay` |
| `src/Assets/Tests/EditMode/LastBreath.Tests.EditMode.asmdef` | `includePlatforms: [Editor]`; refs `nunit.framework`, `UnityEngine.TestRunner`, `UnityEditor.TestRunner`, `LastBreath.Gameplay`; `defineConstraints: [UNITY_INCLUDE_TESTS]` |
| `src/Assets/Tests/EditMode/SmokeTests.cs` | One test: `[Test] public void TestFramework_IsAlive() => Assert.That(true, Is.True);` |

Folder skeleton (`.gitkeep` where empty): `src/Assets/_Project/{Scripts,Prefabs/{Level,Player,Systems},Art,Config,ScriptableObjects}/`, `src/Assets/_Editor/`, `src/Assets/_Sandbox/`, `src/Assets/Scenes/`, `src/Assets/Tests/EditMode/`.

Companion fix: `docs/engine-reference/unity/VERSION.md` line 3 references stale `plan 004 (bootstrap-unity-project)` → repoint to `PLAN-008` in the same commit.

## Out of scope

- Any system implementation (`OxygenSystem`, `FlagSystem`, …).
- `LevelSpec` utility — PLAN-009.
- Scene composition or `unity-mcp` wiring — PLAN-009 / PLAN-010.
- Anything under `src/Assets/_Project/Art/` — PLAN-011.
- Build profiles, CI, Addressables groups.

## Owner

`unity-specialist` for Unity config + asmdefs. `gameplay-programmer` for `GameLifetimeScope.cs` and `SmokeTests.cs`.

## Verification

- [ ] `grep -q "m_EditorVersion: 6000.0.32f1" src/ProjectSettings/ProjectVersion.txt`
- [ ] `python3 scripts/check-runtime-versions.py` → exit 0
- [ ] Unity opens `Bootstrap.unity` with zero compile errors
- [ ] EditMode `SmokeTests.TestFramework_IsAlive` passes
- [ ] `git status` shows no `Library/`, `Temp/`, `obj/`, `*.csproj`, `*.sln`
- [ ] No `.cs` under `src/Assets/_Project/Scripts/**` other than `GameLifetimeScope.cs`
