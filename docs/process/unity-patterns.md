---
id: PROCESS-UNITY-PATTERNS
type: reference
layer: process
status: active
related: [GAMEPLAY-CODE, TEST-STANDARDS]
---

Reference, not tutorial. 13 patterns. Each section: when to use, minimal example, anti-pattern, rule cross-ref. Examples use `FooSystem` / `BarConfig` / `BazEvent` only.

## 1. Project layout & .asmdef boundaries

**When to use:** Always. Root layout is fixed for every system added under `_Project/`.

**Minimal example:**

```text
src/Assets/_Project/
  Systems/        // LastBreath.Systems.asmdef
  Configs/        // LastBreath.Configs.asmdef
  Prefabs/
  Scenes/
  ScriptableObjects/
  Tests/          // LastBreath.Tests.asmdef (refs Systems, Configs)
src/Assets/_Sandbox/   // isolated, no _Project references
// Root namespace: LastBreath.<Folder>
```

**Anti-pattern:**

```text
// One mega-asmdef covering all of _Project, or _Sandbox referenced from Systems.
// Cyclic asmdef refs (Systems <-> Configs).
```

**Rule cross-ref:** `.claude/rules/prototype-code.md` (sandbox isolation).

Reviewer rule_id: UNITY-PATTERN-PROJECT-LAYOUT

## 2. MonoBehaviour vs plain-C# split

**When to use:** Any system whose logic can be expressed without Unity APIs. Default split.

**Minimal example:**

```csharp
public sealed class FooLogic
{
    private readonly BarConfig _config;
    public FooLogic(BarConfig config) { _config = config; }
    public float Tick(float dt, float input) => input * _config.Rate * dt;
}

public sealed class FooBehaviour : MonoBehaviour
{
    [SerializeField] private BarConfig _config;
    private FooLogic _logic;
    private void Awake() { _logic = new FooLogic(_config); }
    private void Update() { _logic.Tick(Time.deltaTime, 1f); }
}
```

**Anti-pattern:**

```csharp
public sealed class FooBehaviour : MonoBehaviour
{
    [SerializeField] private BarConfig _config;
    private void Update() { var x = 1f * _config.Rate * Time.deltaTime; }
}
```

**Rule cross-ref:** `.claude/rules/gameplay-code.md` (System structure).

Reviewer rule_id: UNITY-PATTERN-MONOBEHAVIOUR-SPLIT

## 3. ScriptableObject patterns

**When to use:** Three subtypes only. `Config` for tunables, `RuntimeSet<T>` for live registries, `EventChannel<T>` for typed buses. Pick the narrowest fit.

**Minimal example:**

```csharp
[CreateAssetMenu(menuName = "LastBreath/BarConfig")]
public sealed class BarConfig : ScriptableObject
{
    [SerializeField] private float _rate = 1f;
    [SerializeField] private float _max = 100f;
    public float Rate => _rate;
    public float Max => _max;
}
```

**Anti-pattern:**

```csharp
public sealed class BarConfig : ScriptableObject
{
    public float CurrentValue; // mutated at runtime — leaks state across sessions in editor.
}
```

**Rule cross-ref:** —

Reviewer rule_id: UNITY-PATTERN-SCRIPTABLE-OBJECT-CONFIG

## 4. Update-loop discipline

**When to use:** Pick the loop by responsibility, not by habit.

**Minimal example:**

```csharp
[DefaultExecutionOrder(-50)]
public sealed class FooBehaviour : MonoBehaviour
{
    private void Update() { /* gameplay logic */ }
    private void FixedUpdate() { /* physics integration */ }
    private void LateUpdate() { /* camera/follow */ }
}
```

**Anti-pattern:**

```csharp
[ExecuteAlways] // forbidden in _Project/
public sealed class FooBehaviour : MonoBehaviour { }
```

**Rule cross-ref:** `.claude/rules/gameplay-code.md` (Update loop).

Reviewer rule_id: UNITY-PATTERN-UPDATE-LOOP

## 5. Event symmetry

**When to use:** Every event subscription. No exceptions.

**Minimal example:**

```csharp
public sealed class FooBehaviour : MonoBehaviour
{
    [SerializeField] private BazEventChannel _channel;
    private void OnEnable()  { _channel.Raised += HandleRaised; }
    private void OnDisable() { _channel.Raised -= HandleRaised; }
    private void HandleRaised(BazEvent e) { /* ... */ }
}
```

**Anti-pattern:**

```csharp
private void OnEnable() { _channel.Raised += e => DoStuff(e); } // cannot unsubscribe.
```

**Rule cross-ref:** `.claude/rules/gameplay-code.md` (Events).

Reviewer rule_id: UNITY-PATTERN-EVENT-SYMMETRY

## 6. Coroutine alternatives

**When to use:** State machines for ongoing gameplay; `async`/`await` with `destroyCancellationToken` for one-shot async.

**Minimal example:**

```csharp
public sealed class FooBehaviour : MonoBehaviour
{
    private async Awaitable LoadOnceAsync()
    {
        await Awaitable.WaitForSecondsAsync(0.5f, destroyCancellationToken);
        // one-shot work; cancels on destroy.
    }
}
```

**Anti-pattern:**

```csharp
private void Start() { StartCoroutine(InfiniteLoop()); }
private IEnumerator InfiniteLoop() { while (true) { yield return null; } }
```

**Rule cross-ref:** `.claude/rules/gameplay-code.md` (no long-running coroutines).

Reviewer rule_id: UNITY-PATTERN-COROUTINE-ALTERNATIVES

## 7. Input System patterns

**When to use:** Every input consumer. Action Asset is committed; consumers hold serialised `InputActionReference`s.

**Minimal example:**

```csharp
public sealed class FooBehaviour : MonoBehaviour
{
    [SerializeField] private InputActionReference _fooAction;
    private void OnEnable()  { _fooAction.action.Enable();  _fooAction.action.performed += OnFoo; }
    private void OnDisable() { _fooAction.action.performed -= OnFoo; _fooAction.action.Disable(); }
    private void OnFoo(InputAction.CallbackContext ctx) { /* ... */ }
}
```

**Anti-pattern:**

```csharp
private void Update() { var pi = FindObjectOfType<PlayerInput>(); /* ... */ }
```

**Rule cross-ref:** —

Reviewer rule_id: UNITY-PATTERN-INPUT-SYSTEM

## 8. Addressables loading

**When to use:** Any runtime asset load. Cache the handle; release on destroy.

**Minimal example:**

```csharp
public sealed class FooBehaviour : MonoBehaviour
{
    [SerializeField] private AssetReferenceGameObject _bar;
    private AsyncOperationHandle<GameObject> _handle;
    private async void Start() { _handle = _bar.LoadAssetAsync<GameObject>(); await _handle.Task; }
    private void OnDestroy() { if (_handle.IsValid()) Addressables.Release(_handle); }
}
```

**Anti-pattern:**

```csharp
private void Start() { var prefab = Resources.Load<GameObject>("Bar"); }
```

**Rule cross-ref:** `.claude/rules/gameplay-code.md` (forbids `Resources.Load`).

Reviewer rule_id: UNITY-PATTERN-ADDRESSABLES

## 9. Serialization patterns

**When to use:** Every inspector-bound field. Default is `[SerializeField] private`.

**Minimal example:**

```csharp
public sealed class FooBehaviour : MonoBehaviour
{
    [SerializeField] private BarConfig _config;
    [field: SerializeField] public Transform Anchor { get; private set; }

    [Serializable] private struct FooBounds { public float Min; public float Max; }
    [SerializeField] private FooBounds _bounds;
}
```

**Anti-pattern:**

```csharp
public sealed class FooBehaviour : MonoBehaviour
{
    public BarConfig Config;        // public field, broad surface.
    [SerializeField] internal int X; // non-private serialized field.
}
```

**Rule cross-ref:** `.claude/rules/gameplay-code.md` (Identifiers).

Reviewer rule_id: UNITY-PATTERN-SERIALIZATION

## 10. Cross-scene references

**When to use:** Sibling systems via `GameSystemsRoot`; live registries via `RuntimeSet<T>`; fire-and-forget via `EventChannel<T>`.

**Minimal example:**

```csharp
public sealed class GameSystemsRoot : MonoBehaviour
{
    [SerializeField] private FooBehaviour _foo;
    [SerializeField] private FooRuntimeSet _activeFoos; // ScriptableObject collection
    [SerializeField] private BazEventChannel _bazChannel;
    public FooBehaviour Foo => _foo;
}
```

**Anti-pattern:**

```csharp
private void Start() { var foo = GameObject.Find("Foo").GetComponent<FooBehaviour>(); }
```

**Rule cross-ref:** `.claude/rules/gameplay-code.md` (Forbidden in systems).

Reviewer rule_id: UNITY-PATTERN-CROSS-SCENE

## 11. Memory & GC

**When to use:** Any `Update`, `FixedUpdate`, or per-frame call site.

**Minimal example:**

```csharp
public sealed class FooBehaviour : MonoBehaviour
{
    private static readonly WaitForSeconds _wait = new(0.1f);
    private readonly List<BarConfig> _scratch = new(16);
    private readonly StringBuilder _sb = new(64);
    private void Update() { _scratch.Clear(); /* reuse buffers, no new allocs */ }
}
```

**Anti-pattern:**

```csharp
private void Update() { var tmp = new List<BarConfig>(); /* allocates every frame */ }
```

**Rule cross-ref:** —

Reviewer rule_id: UNITY-PATTERN-GC

## 12. Editor-only code

**When to use:** Anything that must not ship: gizmos, debug menus, validation helpers.

**Minimal example:**

```csharp
public sealed class FooBehaviour : MonoBehaviour
{
#if UNITY_EDITOR
    [SerializeField] private bool _drawGizmos;
    private void OnDrawGizmos() { if (_drawGizmos) { /* ... */ } }
#endif
    [Conditional("UNITY_EDITOR")]
    private static void EditorLog(string msg) => Debug.Log(msg);
}
```

**Anti-pattern:**

```csharp
[SerializeField] private bool _debugMode;
private void Update() { if (_debugMode) Debug.Log(GameObject.Find("Foo")); } // ships.
```

**Rule cross-ref:** —

Reviewer rule_id: UNITY-PATTERN-EDITOR-ONLY

## 13. Testability

**When to use:** Any formula, state-transition, or pure computation. Lives outside MonoBehaviour.

**Minimal example:**

```csharp
public sealed class FooLogic
{
    public float Tick(float dt, float input, BarConfig config)
        => Mathf.Clamp(input * config.Rate * dt, 0f, config.Max);
}
// EditMode test:
// var logic = new FooLogic();
// Assert.That(logic.Tick(1f, 2f, testConfig), Is.EqualTo(2f * testConfig.Rate));
```

**Anti-pattern:**

```csharp
public sealed class FooBehaviour : MonoBehaviour
{
    private void Update() { /* formula inlined here — only PlayMode can reach it */ }
}
```

**Rule cross-ref:** `.claude/rules/test-standards.md`.

Reviewer rule_id: UNITY-PATTERN-TESTABILITY
