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

- Dependencies via `[SerializeField]` or events. No `FindObjectOfType` in system code.
- If you need a reference to another system, inject it through `GameSystemsRoot`.

## Update loop

- Respect the order defined in `SDD#update-flow`.
- A system with timing dependencies on another uses `[DefaultExecutionOrder(N)]`.
- Physics calculations in `FixedUpdate`. Oxygen/agitation logic in `Update`.

## Events

- An event has a single publisher (the registry decides).
- Subscribe in `OnEnable`, unsubscribe in `OnDisable`. Always symmetric.
- Simple payloads: primitives or small structs. Never pass mutable references.

## Forbidden in systems

- `GameObject.Find`, `FindObjectOfType` (except in Awake of root managers).
- `Resources.Load` (use Addressables or serialized references).
- `PlayerPrefs` except in debug.
- `Coroutine` for long-running gameplay logic (prefer state + Update).
- Global singletons — use a `GameSystemsRoot` with serialized references.

## Comments

- Default: zero comments.
- Allowed: non-obvious invariants, workarounds with a link to the issue, explanation of a calculation not derivable from the name.
- Forbidden: docstrings that repeat the method name, "// added for X" comments.

## Tests

- Formulas (oxygen, agitation) → mandatory EditMode unit test.
- Systems with events → PlayMode smoke verifying the event fires with the correct payload.
- Do not chase coverage — chase preventing PoC regressions.
