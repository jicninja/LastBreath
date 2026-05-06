# Unity — Version & Packages

> This file is the contract Phase 0 (`bootstrap-unity-project`, plan 004) enforces. Every value below is exact, not a range. Bumping any line requires a new plan in `docs/plans/`.

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

When you create the project (plan 004), use exactly the LTS version above. The first sanity check in the Phase 0 plan is `cat src/ProjectSettings/ProjectVersion.txt` matching `m_EditorVersion: 6000.0.32f1`.

## Core packages (manifest.json — pinned versions)

| Package | Version | Why |
|---|---|---|
| `com.unity.render-pipelines.universal` | `17.0.3` | URP |
| `com.unity.inputsystem` | `1.11.2` | New Input System; legacy is disabled |
| `com.unity.cinemachine` | `3.1.2` | Camera rig (PoC uses a single virtual camera) |
| `com.unity.test-framework` | `1.4.5` | NUnit-based EditMode/PlayMode tests |
| `com.unity.ide.rider` | `3.0.32` | IDE integration (drop if you use VS Code only) |

URP brings volume-based post-processing (glitch, vignette, color grading); no separate `com.unity.postprocessing` package is needed.

## Optional packages (install only if a plan justifies it)

| Package | When |
|---|---|
| `com.unity.addressables` | If memory pressure becomes a problem during playtest. Default: not installed for the PoC. |
| `com.unity.timeline` | Only if a presence event needs scripted scene timing. Default: not installed. |
| `com.unity.burst` + `com.unity.collections` | Only if a hot loop becomes a measured bottleneck. Default: not installed. |

## Rules

- **Pin exact versions.** No `latest`, no ranges, no semver wildcards.
- **One render pipeline.** URP only. Do not install Built-in or HDRP packages.
- **One input system.** New Input System only. The Player Settings flag `Active Input Handling` must be `Input System Package (New)`, not `Both`.
- **No package addition without a plan.** Adding any package, even from the optional list above, requires a plan in `docs/plans/` so the rationale is captured.
- **Bump in lockstep.** A Unity LTS bump pulls a coordinated package bump for URP, Cinemachine, Input System, Test Framework. They must move together — never bump one in isolation.

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
