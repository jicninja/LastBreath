---
id: ADR-0002-monobehaviour-vs-plain-csharp-split
type: decision
status: accepted
date: 2026-05-05
related: [PROCESS-UNITY-PATTERNS, PLAN-002]
---

# ADR 0002: Formula-bearing logic lives in plain C#, not MonoBehaviour

## Context

Unity gameplay code is conventionally written as a tree of `MonoBehaviour` subclasses. This is the path of least resistance: components attach to GameObjects, the engine calls `Update()`, references serialise in the Inspector. The cost is testability and reasoning: a `MonoBehaviour` cannot be instantiated outside the editor, depends on Unity's lifecycle, and conflates "what the system does" with "how Unity drives it."

For a PoC where the core fantasy hangs on numeric formulas (oxygen drain, agitation modulation, presence event pacing), getting those formulas wrong is the highest-impact failure mode. EditMode tests on plain C# classes run in milliseconds and can be written first (TDD red→green→refactor). EditMode tests on MonoBehaviour-based logic require play-mode harnesses, longer feedback loops, and friction that pushes developers away from writing tests at all.

## Decision

**Formula-bearing logic in `src/Assets/_Project/**` lives in plain C# classes (no `MonoBehaviour` inheritance).** The `MonoBehaviour` exists as a thin Unity-side adapter: it owns serialised configuration references, instantiates the plain logic class in `Awake`, and forwards `Update()` calls. Tests target the plain class directly via NUnit `EditMode`.

Concretely, for a system named `Foo`:

- `FooLogic.cs` — plain C# class. Pure deterministic logic. No `using UnityEngine;` outside types like `Mathf` (and even that is preferred in the form of `System.Math`). Takes config in its constructor; exposes the public surface needed for testing.
- `FooBehaviour.cs` (or `FooSystem.cs` MonoBehaviour) — `MonoBehaviour` adapter. Holds `[SerializeField] FooConfig`, instantiates `FooLogic` in `Awake`, calls `_logic.Tick(Time.deltaTime)` in `Update`. Subscribes to events in `OnEnable`, unsubscribes in `OnDisable`, forwards published events.
- `FooSystemTests.cs` — EditMode test, instantiates `FooLogic` directly with synthesised config, asserts on outputs.

Presentation-only systems (HUD, audio, lighting/VFX) are exempt: they contain no formula-bearing logic and may keep all behaviour in the MonoBehaviour. The split is mandatory only when the system holds rules that can be tested deterministically.

The pattern is documented in `docs/process/unity-patterns.md` Section 2 (`UNITY-PATTERN-MONOBEHAVIOUR-SPLIT`) and enforced by the `code-reviewer` subagent against the `monobehaviour-formula.diff` fixture.

## Alternatives considered

- **All-MonoBehaviour, PlayMode tests for everything.** *Rejected because* PlayMode tests have minute-scale feedback loops; TDD discipline collapses. The PoC has formulas that change frequently during playtest tuning — fast EditMode feedback is non-negotiable.
- **All-plain-C#, MonoBehaviour wrappers only at the scene boundary.** *Rejected because* Unity's editor workflow (Inspector, prefab variants, scene wiring) is genuinely valuable for a small team and shouldn't be fought.
- **Inheritance: `FooSystem : MonoBehaviour, IFooLogic` with logic methods marked virtual for test override.** *Rejected because* mock-style testing of MonoBehaviour subclasses is fragile, doesn't catch update-order bugs, and the inheritance noise outweighs the testability gain.
- **Source-generators / aspect-weaving.** *Rejected because* over-engineered for solo-dev PoC scope.

## Consequences

- **Easy:** EditMode tests on the plain class run in <100 ms; TDD on formulas is frictionless. Formula bugs are caught before the playtester hits them. The MonoBehaviour adapter is small and obvious.
- **Hard:** every formula-bearing system carries two C# files instead of one. Naming convention overhead (`FooLogic` + `FooBehaviour`/`FooSystem`). Slightly more ceremony for the first system written.
- **Accepted loss:** new contributors used to all-MonoBehaviour Unity codebases will need to learn the convention. The recipe in `docs/process/unity-patterns.md` is the onboarding path.
- **Reviewer cost:** the `code-reviewer` subagent must catch formula-in-MonoBehaviour patterns. Synthetic fixture `monobehaviour-formula.diff` exists to verify it does.

## Notes

This pattern leaves the door open to a future refactor where `FooLogic` becomes a domain library reusable in non-Unity contexts (server-side simulation, balancing tools). That is *not* a goal for the PoC, but the split makes it cheap if the project grows.
