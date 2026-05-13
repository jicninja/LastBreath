# Rules — Gameplay Code

Applies to any C# under `src/Assets/_Project/**` that implements systems or mechanics.

## Identifiers

- Strict ASCII in file names, classes, methods, and variables.
- Classes in PascalCase, public members in PascalCase, private in `_camelCase`.
- Events: `OnSomethingHappened` (UnityEvent) or `SomethingChanged` (C# event).

## System structure

A system = one main MonoBehaviour + optionally a config ScriptableObject.

```csharp
public class OxygenSystem : MonoBehaviour
{
    [SerializeField] private OxygenConfig _config;

    public event Action<float, float> OxygenChanged; // current, max
    public event Action OxygenDepleted;

    public float Current { get; private set; }
    public float Max => _config.MaxOxygen;
    // ...
}
```

- Dependencies via VContainer constructor injection or `[Inject]` properties resolved by the scene's `LifetimeScope`. `[SerializeField]` is allowed for inspector-bound configs (ScriptableObjects, prefab references) and for the `LifetimeScope` itself. No `FindObjectOfType` in system code.
- Cross-system references resolve through container registration on the `LifetimeScope`, never through a manual `GameSystemsRoot` lookup. See ADR-0009 §DI and `GAMEPLAY-CODE-DI-LIFETIMESCOPE-ONLY-AT-ROOT`.

## Update loop

- Respect the order defined in `SDD#update-flow`.
- A system with timing dependencies on another uses `[DefaultExecutionOrder(N)]`.
- Physics calculations in `FixedUpdate`. Oxygen/agitation logic in `Update`.

## Events

- An event has a single publisher (the registry decides).
- Subscribe in `OnEnable`, unsubscribe in `OnDisable`. Always symmetric.
- Simple payloads: primitives or small structs. Never pass mutable references.

## Forbidden in systems

- `GameObject.Find`, `FindObjectOfType` (except in `Awake` of the scene's `LifetimeScope` root, when no other option exists).
- `Resources.Load` — banned. Use Addressables (`AssetReference<T>` + `Addressables.LoadAssetAsync(...).ToUniTask()`) for runtime-loaded content, or `[SerializeField]` for inspector-bound content.
- `PlayerPrefs` except in debug.
- `Coroutine` for long-running gameplay logic (prefer `UniTask` + state + `Update`).
- Global singletons — register the system on the scene's VContainer `LifetimeScope` and resolve via constructor or `[Inject]`.

## Comments

- Default: zero comments.
- Allowed: non-obvious invariants, workarounds with a link to the issue, explanation of a calculation not derivable from the name.
- Forbidden: docstrings that repeat the method name, "// added for X" comments.

## Tests

- Formulas (oxygen, agitation) → mandatory EditMode unit test.
- Systems with events → PlayMode smoke verifying the event fires with the correct payload.
- Do not chase coverage — chase preventing PoC regressions.

## Flags and Save (graphic-adventure model)

Rules below were introduced with `SYS-FLAGS`, `SYS-NARRATIVE`, `SYS-SAVE`. Rationale in ADR-0004 and ADR-0005; the SDD invariants and TDD class signatures are the binding contract.

### `GAMEPLAY-CODE-FLAG-NO-SO-EVENT-CHANNEL`

- The flag and narrative event model is a MonoBehaviour custodian (`FlagSystem` / `NarrativeDirector`) with `FlagDefinition` / `NarrativeCueDefinition` as *identity-only* ScriptableObjects. Ryan Hipple-style SO event channels are forbidden.
- Forbidden patterns:
  - `ScriptableObject` types that hold runtime mutable state and raise their own observers (e.g., `BoolVariable`, `GameEvent`, `*EventChannel`).
  - `[SerializeField]` of a `ScriptableObject` that exposes a `Raise(...)` method or a public mutable `Value` property changed at runtime.
  - `_runtimeValue` / `OnEnable`-resets-to-default patterns on a SO whose values are read or written at runtime.
- Allowed:
  - SO subclasses for *static identity + metadata* (`FlagDefinition.defaultValue` is read at `Awake`, never mutated at runtime).
  - SO subclasses for *tuning data* (`OxygenConfig`, `AgitationConfig`, …).
- Cite: `docs/decisions/0004-flag-and-narrative-event-model.md`; TDD `§Flags` intro.

### `GAMEPLAY-CODE-SAVE-ONLY-SAVESYSTEM-TOUCHES-DISK`

- Only `SaveSystem` may touch persistent storage. No other class under `src/Assets/_Project/**` may call:
  - `System.IO.File.*`, `System.IO.Directory.*`, `System.IO.StreamWriter`, `System.IO.StreamReader`, `BinaryFormatter`, `Application.persistentDataPath` reads/writes outside `SaveSystem`.
  - `PlayerPrefs.*` outside `[Conditional("DEBUG_OVERLAY")]` paths.
- Migrations live in `SaveSystem.Migrate(SaveData)`. No other class versions or migrates save data.
- Cite: `docs/decisions/0005-save-system-architecture.md`; SDD `§SaveSystem` Invariants; TDD `§Save` `### SaveSystem`.

### `GAMEPLAY-CODE-SAVE-NO-EVENTS-DURING-LOADING`

- While `GameManager.CurrentState == GameState.Loading`, no system may invoke its public events (`Invoke`, `?.Invoke`, raising a UnityEvent). Restore paths must write fields directly and rely on the single `EVT-save-restored` published by `SaveSystem` once the transition to `Playing` happens.
- Concretely:
  - `FlagSystem.RestoreState(dto)` calls `RestoreSilently(...)`, never `Set(...)`.
  - `NarrativeDirector.RestoreState(dto)` rehydrates `firedOneShots` and does not evaluate cues.
  - `OxygenSystem.RestoreState(dto)` assigns `Current` directly without firing `OxygenChanged`.
- Update loops must gate on `State == Playing` before publishing time-based events.
- Cite: SDD `§SaveSystem` Invariants; TDD `§Save` `### ISaveable<TDto>`; TDD `§Flags` `### FlagSystem` `RestoreSilently` contract.

## Ship AI and dialogue

Rules below were introduced with `SYS-TERMINAL` and `SYS-DIALOGUE`. Rationale lives in ADR-0006; the SDD invariants and TDD class signatures are the binding contract.

### `GAMEPLAY-CODE-DIALOGUE-NO-DIRECT-LLM`

- All LLM access flows through `IDialogueTransport.SendAsync`, and `SendAsync` is invoked **only from inside `SYS-DIALOGUE`** (`DialogueSystem` and its plain-C# `DialogueLogic`). No other class under `src/Assets/_Project/**` may call a transport directly.
- **`SendAsync` is also gated on `DialogueLogic.EvaluateAvailability(...)` returning `Online`** (per ADR-0006 amendment 2026-05-12). The `Garbled` and `Silent` branches in `DialogueSystem.SubmitTurnAsync` synthesize their `DialogueResponse` without calling the transport. A code path that branches on `AvailabilityState` and then calls `SendAsync` from any branch other than `Online` is a violation.
- Forbidden patterns:
  - `[SerializeField] IDialogueTransport _transport;` on any class that is not `DialogueSystem`.
  - `UnityWebRequest` or `HttpClient` instantiations outside `OllamaHttpTransport`.
  - Wrapping a transport in a static helper or singleton (`LlmClient.Send(...)`) — the seam is instance-only.
  - Subscribing to a transport's internal events from outside `SYS-DIALOGUE`.
  - Calling `SendAsync` from the `Garbled` or `Silent` branches of `SubmitTurnAsync`.
- Allowed:
  - `OllamaHttpTransport` and `MockTransport` implementations themselves.
  - `DialogueSystem.SubmitTurnAsync(...)` as the public entry point for `TerminalSystem` and any future caller.
  - `SendAsync` invoked exclusively from the `Online` branch inside `DialogueSystem.SubmitTurnAsync`.
- Cite: ADR-0006 §Decision item 1 (the seam) + ADR-0006 amendment 2026-05-12 (availability gating); SDD `§DialogueSystem` Invariants and the "Decision — availability gating" block; TDD `### IDialogueTransport`, `### DialogueSystem`, and `### MotherAvailabilityRule`.

### `GAMEPLAY-CODE-DIALOGUE-NO-SECRETS-IN-SAVE`

- `DialogueDto` and all DTOs it transitively contains (`DialogueExchange`, `InboxEntry`) must hold **conversational state only**. Forbidden fields:
  - Endpoint URLs, port numbers, model names, prompt templates.
  - API keys, tokens, authentication headers, or any credential.
  - `LlmTransportConfig` or `DialogueAIConfig` references — these are tuning configs, not save state.
- The save file is reviewable plaintext JSON; treat it as such.
- Cite: ADR-0006 §Decision items 4 and 8; TDD `### DialogueDto` `Notes on shape`; TDD `### LlmTransportConfig`.

### `GAMEPLAY-CODE-DIALOGUE-PROMPT-MUST-WITHHOLD`

- The LLM prompt context is built by `DialogueLogic.BuildContext(...)` and serialized into the prompt by `DialogueLogic.BuildPrompt(...)`. Both consult an **explicit allowlist** of fields. The allowed fields are exactly those declared on `DialogueContext`: `zone`, `oxygen` (bucket), `agitation` (bucket), `objectiveText`, `mandate` / `integrity` / `budget` (floats in the struct, **bucketed at serialization** to `very-low | low | medium | high | very-high`), `recentExchanges`, `recentEvents` (capped 0..10, FIFO; closed `RecentEventTag` enum + `RecentTagAge` enum), `lastSignificantInteraction` (nullable string sourced exclusively through `IFocusLabel.FocusLabel`).
- Forbidden patterns:
  - `System.Reflection` over a game-state object to enumerate fields into the prompt.
  - Adding a field to `DialogueContext` without a corresponding update to ADR-0006 / TDD `### DialogueContext` `Withheld by design` block.
  - Sending exact oxygen percentage, exact agitation float, exact `mandate`/`integrity`/`budget` floats, player position vectors, full flag dictionaries, exact presence cooldowns or per-firing timestamps, prior-session history, or inbox contents into the prompt body.
  - Reading `lastSignificantInteraction` from anywhere other than the cached value populated by the `EVT-interaction-completed` handler casting the source to `IFocusLabel`.
- Required:
  - `BuildContext` AND `BuildPrompt` are both `public` so the reviewer can grep both and verify the allowlist is exhaustive at construction (`BuildContext`) and at serialization (`BuildPrompt`).
  - The TDD `### DialogueContext` `Withheld by design` block is the canonical exclusion list. New entries to either the allowlist or the withhold list come through an ADR amendment, not a silent code edit.
- Cite: ADR-0006 §Decision item 5 + ADR-0006 amendment 2026-05-12 (allowlist extension); TDD `### DialogueContext` (allowlist + withheld block); TDD `### DialogueLogic` (`BuildContext` + `BuildPrompt`); TDD `### IFocusLabel`.

## Tags and layers

The companion to level-design rule `LEVEL-DESIGN-TAGS-REGISTERED`. Tags are declared in `src/ProjectSettings/TagManager.asset` and registered in `docs/registry/architecture.yaml` under `tags:` (see `docs/process/unity-patterns.md` `§17`). The rule below covers C# usage.

### `GAMEPLAY-CODE-NO-TAG-STRING-LITERALS`

C# under `src/Assets/_Project/Scripts/**` does not embed tag string literals. Use either a generated constants class (`Tags.BreathingStation`) populated from the registry, or a `TagDefinition` ScriptableObject reference, never `"Breathing Station"` inline.

- Forbidden patterns:
  - `gameObject.CompareTag("...")` with a string literal argument.
  - `other.tag == "..."` comparisons.
  - `GameObject.FindWithTag("...")`, `FindGameObjectsWithTag("...")`, `FindGameObjectWithTag("...")` with a string literal argument.
  - `gameObject.tag = "..."` assignments to literals.
- Allowed patterns:
  - `gameObject.CompareTag(Tags.BreathingStation)` (constants class generated from the registry).
  - `gameObject.CompareTag(_tagDefinition.Value)` (SO with a serialized tag value, identity-only, no runtime mutation).
  - Unity's built-in literals (`"Untagged"`, `"Player"`, `"MainCamera"`, `"GameController"`, `"Respawn"`, `"Finish"`, `"EditorOnly"`) only inside engine-bridge code (e.g., a fresh `SpawnPoint` lookup at boot) and only if the use site cites the engine reason.
- Cite: `docs/process/unity-patterns.md` `§17` (`UNITY-PATTERN-TAGS-AND-LAYERS`); `.claude/rules/level-design.md` (`LEVEL-DESIGN-TAGS-REGISTERED`).

## Runtime, DI, async, and asset loading

Rules below were introduced with ADR-0009 to make the project's runtime stack explicit. Pins live in `docs/registry/architecture.yaml::tooling`; the engine-reference `VERSION.md` files mirror them. The drift script `scripts/check-runtime-versions.py` runs advisory at SessionStart.

### `GAMEPLAY-CODE-DI-LIFETIMESCOPE-ONLY-AT-ROOT`

VContainer is the only DI mechanism in `src/Assets/_Project/**`. Registration happens in a single `LifetimeScope` subclass per scene (`GameLifetimeScope` for the main scene). Gameplay systems receive cross-system dependencies via constructor injection or `[Inject]` properties resolved by the scope.

- Forbidden patterns:
  - A `GameSystemsRoot` MonoBehaviour that holds nested `[SerializeField]` references to every system as the cross-system wiring mechanism.
  - `[SerializeField]` of another system (`[SerializeField] private FlagSystem _flagSystem;`) on a class that is not a `LifetimeScope` subclass. Cross-system refs go through the container.
  - `FindObjectOfType<T>()` inside system code. Allowed only in the `Awake` of a `LifetimeScope` for engine-bridge bootstrap, and only when documented at the call site.
  - A `ServiceLocator`, `Singleton<T>`, or static `Instance` property exposing a system. The scope is the locator.
- Allowed patterns:
  - `[SerializeField]` on the `LifetimeScope` itself, pointing to ScriptableObject configs (`OxygenConfig`, `AgitationConfig`, `LlmTransportConfig`, `FlagDefinition`, …) and to scene-bound prefabs / GameObjects the scope registers.
  - Constructor injection on plain-C# classes (`DialogueLogic`).
  - `[Inject]` property or method injection on MonoBehaviour systems (`DialogueSystem`, `OxygenSystem`, …).
  - A second `LifetimeScope` for a smoke scene or an additive sub-scene, registered as a child of the main scope.
- Cite: ADR-0009 §Decision (Dependency injection — VContainer); `docs/engine-reference/unity/VERSION.md` §DI bootstrap; SDD `§LifetimeScope`; TDD `§GameLifetimeScope`.

### `GAMEPLAY-CODE-PREFER-UNITASK`

Async methods under `src/Assets/_Project/**` return `UniTask` / `UniTask<T>`. Raw `System.Threading.Tasks.Task` is allowed only at the transport boundary (`OllamaHttpTransport.SendAsync` and any future HTTP / file I/O seam). Wrap engine `Awaitable` at the call site via `.AsUniTask()` rather than propagating it.

- Forbidden patterns:
  - A public method on a system that returns `Task<T>` or `Awaitable<T>` from inside `src/Assets/_Project/Scripts/**` (transport implementations excepted).
  - `async void` on gameplay code — use `async UniTaskVoid` if a fire-and-forget is genuinely needed.
  - `Task.Run` on the Unity main thread to fake threading. Use `UniTask.RunOnThreadPool` or stay single-threaded.
- Allowed patterns:
  - `public UniTask<DialogueResponse> SubmitTurnAsync(...)` on `DialogueSystem`.
  - `Task<TransportResponse> SendAsync(...)` on `IDialogueTransport` and its implementations (transport boundary; cite ADR-0006 at the use site).
  - `await Addressables.LoadAssetAsync<T>(...).ToUniTask()` to cross the engine boundary into UniTask.
- Cite: ADR-0009 §Decision (Async runtime — UniTask); ADR-0006 §Decision item 1 (transport boundary); `docs/engine-reference/unity/VERSION.md` (UniTask pin).

### `GAMEPLAY-CODE-ADDRESSABLES-FOR-RUNTIME-LOAD`

Runtime-loaded content (content not bound at compile time via Inspector) uses `AssetReference<T>` + `Addressables.LoadAssetAsync(...).ToUniTask()`. The reviewer flags non-Addressables runtime loads **advisory**, never blocking. The `Resources.Load` ban (Forbidden in systems, line 47) stands and is **blocking**.

- Forbidden patterns:
  - `Resources.Load<T>("path")` — blocking violation, surfaced as an error (this rule does not relax the existing ban).
  - `AssetDatabase.LoadAssetAtPath<T>(...)` inside `src/Assets/_Project/Scripts/**` runtime code. AssetDatabase is editor-only and breaks builds.
- Advisory patterns (flagged, not blocked):
  - A new system that loads a prefab via a serialized string path and `Instantiate` at runtime, where an `AssetReference` would have been the better surface. The reviewer suggests the migration; the diff lands.
- Allowed patterns:
  - `[SerializeField] private AssetReferenceGameObject _crewmateAssetRef;` plus `await _crewmateAssetRef.InstantiateAsync().ToUniTask()` for runtime instantiation.
  - `[SerializeField]` of a direct prefab / ScriptableObject reference when the binding is known at edit time (the entire `CFG-*` family). This is the dominant pattern for the PoC and is not an Addressables miss.
- Cite: ADR-0009 §Decision (Asset management — Addressables advisory); `docs/engine-reference/unity/VERSION.md` (`com.unity.addressables` pin).

### `GAMEPLAY-CODE-NO-STALE-EXTERNAL-API`

Reinforces the global `no-stale-APIs` rule in `AGENTS.md` `§Global rules`. Specifically: any code that calls into Unity, VContainer, UniTask, or Addressables APIs must be Context7-verified against the pinned version in `docs/registry/architecture.yaml::tooling`. The reviewer checks the diff's plan or commit message for the Context7 citation; the reviewer does not re-query the API itself.

- Forbidden patterns:
  - A diff that introduces a Unity API call deprecated by the pinned LTS without a comment citing why the old API is still correct.
  - A VContainer registration pattern from an old major (1.x → 1.15 was a breaking-ish bump on a few helpers) without a Context7-verified citation.
  - A UniTask helper that was renamed across the 2.x line without an updated import.
- Allowed:
  - A diff whose plan or commit body includes a one-line citation: `Context7-verified against UniTask 2.5.10 — see plan §verification.`
- Cite: ADR-0009 §Decision (Reviewer rules); `AGENTS.md` `§Global rules` (no-stale-APIs).
