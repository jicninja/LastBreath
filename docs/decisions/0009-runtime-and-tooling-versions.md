---
id: ADR-0009-runtime-and-tooling-versions
type: decision
status: accepted
date: 2026-05-12
related: [ADR-0003, ADR-0004, ADR-0006, ADR-0007, ADR-0008]
---

# ADR 0009: Runtime versions, MCP pinning, DI, async runtime, and asset-load policy

## Context

The repo is partially explicit about its tooling. `docs/engine-reference/unity/VERSION.md` already pins Unity and its core packages with the "every value is exact, not a range" contract. The rest of the stack is either undeclared or deferred:

1. **Blender** is the asset-design authoring surface (ADR-0008) but no document names a version, and the `blender-mcp` install instructions in `docs/process/blender-mcp.md` say "pin in Wave B".
2. **MCP servers** — `.mcp.json` declares only `context7` with `npx -y` (latest-fetch). `unity-mcp` and `blender-mcp` are referenced in `AGENTS.md` but their versions/commits are deferred.
3. **Dependency injection** is described as manual `[SerializeField]` composition through a `GameSystemsRoot` prefab. No DI library is named. With the system count past a dozen (`SYS-GAME`, `SYS-OXYGEN`, `SYS-AGITATION`, `SYS-PRESENCE`, `SYS-INTERACTOR`, `SYS-ENVIRONMENT`, `SYS-OBJECTIVE`, `SYS-HUD`, `SYS-AUDIO`, `SYS-LIGHTVFX`, `SYS-FLAGS`, `SYS-NARRATIVE`, `SYS-SAVE`, `SYS-TERMINAL`, `SYS-DIALOGUE`) and a dialogue subsystem that already wires nine `[SerializeField]` references onto `DialogueSystem` (TDD `§DialogueSystem`), manual prefab wiring is a maintenance hazard.
4. **Async runtime** — the SDD calls `SubmitTurnAsync` a `Task`-returning method; the TDD shows `Awaitable<DialogueResponse>` (Unity 6 native). They disagree, and neither names a single async style for the project.
5. **Addressables** is listed as "optional, deferred for PoC" but `.claude/rules/gameplay-code.md` already bans `Resources.Load`. Runtime content loading has no declared path.

The user wants the architecture explicit and the agent forced to use a single, current stack. Per the "agentic forcing" principle established by ADR-0008: declarative documents are not enough — a script must surface drift at SessionStart so future sessions cannot silently use stale or unpinned tooling.

Four authoring patterns for the versioning decision were considered:

- **Status quo (versions live in their respective process docs).** Rejected — Blender, MCP, DI, async, Addressables touch overlapping rules. Scattering the pins across `docs/process/*.md` and `.mcp.json` invites drift between the registry, the rules, and the actual installation.
- **One ADR per topic (versioning ADR, DI ADR, async ADR, Addressables ADR).** Rejected — five overlapping ADRs read on the same diff is more friction than one. The decisions are interlocked (Unity 6 LTS dictates compatible Addressables; VContainer compatibility shapes the LifetimeScope rule; `Task` vs `UniTask` shapes the transport boundary in ADR-0006).
- **Single tooling ADR + one `tooling:` block in `architecture.yaml` + one drift script (chosen).** Mirrors ADR-0008's shape: one ADR, one registry block, one verifier script wired into SessionStart. Existing prior art: `scripts/check-art-sync.py`, `scripts/art-staging-queue.py`.
- **Enforce drift via pre-commit.** Rejected for now per ADR-0003 (soft reviewer enforcement is the project stance). The drift script runs advisory at SessionStart and on demand. Pre-commit escalation deferred to a follow-up plan if drift becomes recurrent.

## Decision

Adopt **one ADR + one registry block + one advisory drift script**. Lock the following:

### Unity

- Stay on the **Unity 6 LTS** track. Current pin is `6000.0.32f1` (mirrored in `docs/engine-reference/unity/VERSION.md`). LTS patches are bumped by the `unity-specialist` through a plan; cross-major bumps require a new ADR.
- The Unity Tech Stream (`6000.4.x`, `6000.5.x`, …) is **not** in scope. If a feature genuinely requires the Tech Stream, open an amendment to this ADR.

### Blender

- Pin **Blender 5.1** as the asset-design authoring surface (mirrored in `docs/engine-reference/blender/VERSION.md`).
- If Blender 5.1 is not yet a stable upstream release at bootstrap time, the `asset-designer` falls back to the latest stable in the 4.x LTS line, documents the fallback in `docs/engine-reference/blender/VERSION.md`, and opens a plan to bump once 5.1 ships.
- The bundled glTF 2.0 exporter is the canonical export path (ADR-0008 already locks `.glb`). Its version pin lives in the Blender VERSION.md alongside the engine pin.

### MCP servers

- `context7`, `unity-mcp`, `blender-mcp` are pinned by **version tag** (npm tag for `context7`) or **commit SHA** (for the two community Python servers).
- The pins live in `docs/engine-reference/mcp/VERSIONS.md` and are mirrored in `architecture.yaml::tooling.mcp_servers`.
- `.mcp.json` references the pinned `context7` version explicitly (no `npx -y` latest-fetch).
- Bumping any MCP pin is plan-gated, identical to the Unity package bump policy. The plan must query Context7 for the upstream README before bumping (per the global `no-stale-APIs` rule in `AGENTS.md` `§Global rules`).

### Dependency injection — VContainer

- **VContainer** (`hadashiA/VContainer`) replaces manual `GameSystemsRoot` prefab wiring as the only DI mechanism in `src/Assets/_Project/**`.
- Each playable scene gets one `LifetimeScope` subclass (`GameLifetimeScope` for the main scene; smoke scenes may have their own). The scope is the composition root; all cross-system references resolve through container registration, not `FindObjectOfType`, not a global service locator.
- `[SerializeField]` remains valid for **inspector-bound configs** (ScriptableObjects: `OxygenConfig`, `AgitationConfig`, `FlagDefinition`, `LlmTransportConfig`, …) and for **prefab references** the scope itself holds. Cross-system runtime references (e.g., `DialogueSystem` needing `FlagSystem`, `GameManager`, `OxygenSystem`, `AgitationSystem`, …) move from `[SerializeField]` to constructor injection or `[Inject]` properties.
- ADR-0004 stands: VContainer adoption does **not** reintroduce Ryan-Hipple-style SO event channels. ScriptableObjects are identity + tuning only.

### Async runtime — UniTask

- **UniTask** (`Cysharp/UniTask`) is the preferred async runtime for `src/Assets/_Project/**`. Methods that today return `Task` or `Awaitable` (e.g., `DialogueSystem.SubmitTurnAsync`, `DialogueLogic.ProcessTurnAsync`) return `UniTask` / `UniTask<T>`.
- Raw `System.Threading.Tasks.Task` is allowed **only at the transport boundary** — `OllamaHttpTransport.SendAsync` and any future HTTP / file I/O seam. Inside the `_Project/` body, `await someTask.AsUniTask()` to cross the boundary.
- No ban on `Awaitable` in engine-bridge code if a Unity API surfaces it (e.g., `SceneManager.LoadSceneAsync().ToUniTask()`); but propagating `Awaitable` deeper into the gameplay surface is forbidden — wrap at the call site.
- Per the user clarification, **no hard ban on `Task`** is encoded in the reviewer rules. The rule `GAMEPLAY-CODE-PREFER-UNITASK` is "prefer UniTask; cite the boundary if you use Task", not "fail the diff on a Task return type".

### Asset management — Addressables (advisory)

- **Addressables** is the documented path for runtime-loaded content (content not bound at compile time via Inspector). Concretely: anything that would have been `Resources.Load` is `AssetReference<T>` + `Addressables.LoadAssetAsync(...).ToUniTask()`.
- For the PoC, the predominant pattern remains `[SerializeField]` inspector binding (it covers all `CFG-*` configs and most prefabs). Addressables is **recommended but not enforced** for the rare runtime-loaded cases.
- The existing `gameplay-code.md` ban on `Resources.Load` (line 47) stands. The new rule `GAMEPLAY-CODE-ADDRESSABLES-FOR-RUNTIME-LOAD` is **advisory** — the reviewer flags non-Addressables runtime loads as advisory notes, never blocks the commit.
- Promoting the rule from advisory to blocking is a future-plan decision, gated on the PoC actually using Addressables for something. There is no point banning a pattern no code in the repo currently produces.

### Reviewer rules (added to `.claude/rules/gameplay-code.md`)

- `GAMEPLAY-CODE-DI-LIFETIMESCOPE-ONLY-AT-ROOT` — VContainer registration happens in a single `LifetimeScope` subclass per scene; gameplay systems receive dependencies via constructor injection or `[Inject]` properties. `[SerializeField]` remains valid for inspector-bound configs (ScriptableObjects, prefab refs) and for the scope itself.
- `GAMEPLAY-CODE-PREFER-UNITASK` — async methods under `src/Assets/_Project/**` return `UniTask` / `UniTask<T>`. Raw `Task` allowed only at the transport boundary; cite the boundary at the use site.
- `GAMEPLAY-CODE-ADDRESSABLES-FOR-RUNTIME-LOAD` (advisory) — content loaded at runtime (not bound via Inspector) uses `AssetReference<T>` + Addressables. Reviewer flags violations advisory, not blocking. The `Resources.Load` ban (already in place) stands.
- `GAMEPLAY-CODE-NO-STALE-EXTERNAL-API` — reinforces `AGENTS.md` `§Global rules`. Any call into Unity, VContainer, UniTask, or Addressables APIs must be Context7-verified against the pinned version before the diff lands. The reviewer checks the citation block in the diff's plan, not the API itself.

### Drift verification — `scripts/check-runtime-versions.py`

- Reads the declared versions from `architecture.yaml::tooling` and `docs/engine-reference/**/VERSION.md`.
- Compares against the on-disk truth:
  - `src/ProjectSettings/ProjectVersion.txt` → Unity editor pin
  - `src/Packages/manifest.json` → Unity packages (URP, Input System, Cinemachine, Test Framework, VContainer, UniTask, Addressables)
  - `.mcp.json` → MCP server tags
- Handles "not yet bootstrapped" as a `skip`, not an error. Missing `ProjectVersion.txt` does not block.
- Exit codes mirror `scripts/check-art-sync.py`: `0` = clean (or skipped), `1` = drift, `2` = infrastructure error.
- Wired into `.claude/settings.json::hooks.SessionStart` alongside `art-staging-queue.py`. Advisory only — no pre-commit hook in this ADR, consistent with ADR-0003.

## Alternatives considered

- **Stay on manual `GameSystemsRoot` prefab wiring.** Rejected. With nine `[SerializeField]` references on `DialogueSystem` alone, every new cross-system call multiplies inspector bookkeeping and breaks under prefab variants. VContainer pays its own footprint after the second system that needs the third.
- **Zenject / Extenject instead of VContainer.** Rejected. Heavier, slower, and the project does not need Zenject's IL-weaving or signal bus — VContainer covers constructor injection and `MonoBehaviour` `[Inject]` with less surface area.
- **Reflex instead of VContainer.** Rejected at this scope size. Smaller and newer than VContainer, but VContainer has the larger ecosystem and the stricter compile-time validator that catches missing registrations.
- **Unity 6 Tech Stream (6000.4.x).** Rejected by the user this round. The PoC has no requirement that depends on Tech Stream features, and LTS is the safer surface for a year-scale project.
- **Native `Awaitable` instead of UniTask.** Rejected. `Awaitable` is fine for one-off engine glue but lacks `WhenAll` / cancellation ergonomics / structured-concurrency helpers that UniTask provides. Mixing both in `_Project/` is the failure mode this ADR explicitly closes by naming one runtime.
- **Mandatory Addressables for everything.** Rejected. The PoC has no shipped content that loads outside Inspector binding. Forcing Addressables on `CFG-*` configs would add boilerplate for zero benefit. Advisory rule keeps the door open without the friction.
- **Pre-commit hook on version drift.** Rejected this ADR; defer to a follow-up plan if drift recurs. Soft enforcement (SessionStart advisory + reviewer flag) is the ADR-0003 stance.

## Consequences

- **Easy.** Every external pin in one place (`architecture.yaml::tooling`); `VERSION.md` mirrors are auto-checked by the script; reviewer rules cite this ADR by ID; the SessionStart advisory surfaces drift without a human having to remember.
- **Easy.** Future bumps follow the existing `unity-specialist` plan template — one source of truth, one diff, one ADR cite.
- **Hard.** Adopting VContainer means the `GameSystemsRoot` prefab pattern in the SDD and TDD is now historical. The reframe is documentation only at this point (no `_Project/` C# exists), but the next plan that bootstraps the project (`plan 004`) must scaffold the `LifetimeScope` and the registration site, not the legacy prefab.
- **Hard.** UniTask is a package addition the Unity bootstrap must perform. The TDD's `Awaitable<DialogueResponse>` becomes `UniTask<DialogueResponse>` and any future code that calls into the `DialogueLogic` boundary must `await UniTask`, not `await Awaitable`.
- **Accepted loss.** Addressables advisory means the reviewer will not catch every misuse. The acceptance is conscious: the PoC does not exercise the runtime-load path yet, so a blocking rule would be ceremony without substance.
- **Mandatory tests (added by the plan that bootstraps `_Project/`)**:
  - `LifetimeScope_RegistersAllSystems` — EditMode, builds the scope in a smoke fixture and resolves every `SYS-*` once.
  - `DialogueSystem_SubmitTurnAsync_ReturnsUniTask` — EditMode, pairs `DialogueLogic` with `MockTransport` and verifies the awaiter signature compiles against `UniTask`.

## Notes

- The `tooling:` block in `architecture.yaml` is the single source of truth for pins. `VERSION.md` mirrors are human-readable companions; if the two disagree, fix `architecture.yaml` first, then the VERSION.md mirror — never the other way around.
- The drift script is intentionally lenient about "not yet bootstrapped" (skip, exit 0) so the SessionStart hook does not noise the preamble during the period before `plan 004` ships the Unity project.
- This ADR does **not** install any packages. Package installation lands in `plan 004 / Phase 0 (bootstrap-unity-project)`, which consumes this ADR.
- If `unity-mcp` or `blender-mcp` is replaced upstream (forks, ports), the schema of `docs/engine-reference/mcp/VERSIONS.md` and the `architecture.yaml::tooling.mcp_servers` block stay stable — only the entries' `source:` + `pin:` change.
- The `GameSystemsRoot` identifier survives in the SDD/TDD as a historical anchor only. Live prose uses `LifetimeScope`. New code never references `GameSystemsRoot`. The registry never had a `SYS-*` for `GameSystemsRoot`; nothing to deprecate.
