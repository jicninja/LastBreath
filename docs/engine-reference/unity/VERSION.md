# Unity — Version & Packages

> This file is the contract a future Unity-bootstrap plan will enforce (see `docs/plans/008-unity-bootstrap.md` for the active proposal). Every value below is exact, not a range. Bumping any line requires a new plan in `docs/plans/`.

## Target (pinned)

| Setting | Value |
|---|---|
| **Unity LTS** | `6000.0.32f1` (Unity 6 LTS — latest patch as of this pin) |
| **Render pipeline** | URP (Universal Render Pipeline) |
| **Scripting backend (Editor)** | Mono |
| **Scripting backend (Builds)** | IL2CPP |
| **API compatibility level** | .NET Standard 2.1 |
| **Color space** | Linear |
| **Active Input Handling** | Input System Package (New) only. Legacy disabled. |

When the Unity project is created (per the active Unity-bootstrap plan, `docs/plans/008-unity-bootstrap.md`), use exactly the LTS version above. The first sanity check is `cat src/ProjectSettings/ProjectVersion.txt` matching `m_EditorVersion: 6000.0.32f1`.

## Core packages (manifest.json — pinned versions)

| Package | Version | Why |
|---|---|---|
| `com.unity.render-pipelines.universal` | `17.0.3` | URP |
| `com.unity.inputsystem` | `1.11.2` | New Input System; legacy is disabled |
| `com.unity.cinemachine` | `3.1.2` | Camera rig (PoC uses a single virtual camera) |
| `com.unity.test-framework` | `1.4.5` | NUnit-based EditMode/PlayMode tests |
| `com.unity.ide.rider` | `3.0.32` | IDE integration (drop if you use VS Code only) |
| `com.unity.addressables` | `2.3.16` | Runtime-loaded content path. Recommended-but-not-enforced by `GAMEPLAY-CODE-ADDRESSABLES-FOR-RUNTIME-LOAD` (ADR-0009). `Resources.Load` stays banned. |

URP brings volume-based post-processing (glitch, vignette, color grading); no separate `com.unity.postprocessing` package is needed.

## Third-party packages (UPM Git / OpenUPM — pinned versions)

| Package | Version | Manifest entry | Why |
|---|---|---|---|
| `jp.hadashikick.vcontainer` | `1.16.9` | `"jp.hadashikick.vcontainer": "1.16.9"` (OpenUPM) | DI container. Single `LifetimeScope` per scene; no manual `GameSystemsRoot` prefab. See ADR-0009 §DI and rule `GAMEPLAY-CODE-DI-LIFETIMESCOPE-ONLY-AT-ROOT`. |
| `com.cysharp.unitask` | `2.5.10` | `"com.cysharp.unitask": "https://github.com/Cysharp/UniTask.git?path=src/UniTask/Assets/Plugins/UniTask#2.5.10"` | Preferred async runtime under `src/Assets/_Project/**`. See ADR-0009 §UniTask and rule `GAMEPLAY-CODE-PREFER-UNITASK`. |

Both pins live in `architecture.yaml::tooling.unity.packages` and the drift script (`scripts/check-runtime-versions.py`) re-verifies on SessionStart.

## DI bootstrap

VContainer's `LifetimeScope` is the only DI entry point in `src/Assets/_Project/**`. The composition root for the main scene is `GameLifetimeScope` (a `LifetimeScope` subclass that lives on the bootstrap GameObject). It registers every `SYS-*` and resolves cross-system references through the container — never `FindObjectOfType`, never a global service locator. ScriptableObject configs (`CFG-*`) and prefab references stay inspector-bound via `[SerializeField]` on the scope itself. See `docs/sdd/last-breath-poc-sdd.md` `§LifetimeScope` and `docs/tdd/last-breath-poc-tdd.md` `§GameLifetimeScope`.

## Optional packages (install only if a plan justifies it)

| Package | When |
|---|---|
| `com.unity.timeline` | Only if a presence event needs scripted scene timing. Default: not installed. |
| `com.unity.burst` + `com.unity.collections` | Only if a hot loop becomes a measured bottleneck. Default: not installed. |

## Rules

- **Pin exact versions.** No `latest`, no ranges, no semver wildcards.
- **One render pipeline.** URP only. Do not install Built-in or HDRP packages.
- **One input system.** New Input System only. The Player Settings flag `Active Input Handling` must be `Input System Package (New)`, not `Both`.
- **No package addition without a plan.** Adding any package, even from the optional list above, requires a plan in `docs/plans/` so the rationale is captured.
- **Bump in lockstep.** A Unity LTS bump pulls a coordinated package bump for URP, Cinemachine, Input System, Test Framework, and Addressables. They must move together — never bump one in isolation.
- **Third-party pins are plan-gated too.** VContainer and UniTask bumps live in `docs/plans/` like Unity LTS bumps. Before drafting the bump plan, query Context7 for the upstream README (per the `no-stale-APIs` rule in `AGENTS.md` `§Global rules`).

## How to confirm the installed version

```bash
cat src/ProjectSettings/ProjectVersion.txt
```

Expected match line: `m_EditorVersion: 6000.0.32f1`.

`src/Packages/manifest.json` is the source of truth for package versions; this `VERSION.md` mirrors it. If they disagree, fix `manifest.json` first, then update this file.

## Bumping policy

When a new LTS patch lands, the `unity-specialist` opens a plan with these checkpoints:

1. Verify the patch is on the current major (e.g., `6000.0.x`). Cross-major bumps are a separate plan.
2. Bump `m_EditorVersion` in `ProjectVersion.txt` and the `manifest.json` versions in lockstep.
3. Run all EditMode + PlayMode tests.
4. Boot `Smoke.unity`.
5. Update this file's pinned versions.
6. Commit.

The user reviews `docs/decisions/` for any ADR that constrains the bump (e.g., a package known to break on a specific Unity version).
