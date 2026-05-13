---
id: PROCESS-UNITY-PATTERNS
type: reference
layer: process
status: active
related: [GAMEPLAY-CODE, TEST-STANDARDS, LEVEL-DESIGN]
---

Reference, not tutorial. 17 patterns. Each section: when to use, minimal example, anti-pattern, rule cross-ref. Examples use `FooSystem` / `BarConfig` / `BazEvent` only.

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

**When to use:** Two subtypes only.

1. **Config / tuning SOs** — designer-tunable numbers and references. Read at `Awake`, never mutated at runtime. Examples: `OxygenConfig`, `AgitationConfig`, `LlmTransportConfig`, `CameraRigConfig`.
2. **Identity / metadata SOs** — stable handles the gameplay layer compares by *reference*, never by string. Read-only at runtime. Examples: `FlagDefinition`, `NarrativeCueDefinition`, `DialogueCueDefinition`, `PresenceEventDefinition`, `MotherAvailabilityRule`.

Runtime state for gameplay flags, world events, and inter-system signals does **not** live in a ScriptableObject. It lives in the relevant MonoBehaviour custodian (`FlagSystem`, `NarrativeDirector`, `DialogueSystem`, `PresenceDirector`) which raises C# events. SO-based event channels and SO-based runtime registries are banned by ADR-0004 (`GAMEPLAY-CODE-FLAG-NO-SO-EVENT-CHANNEL`).

**Minimal example (tuning SO):**

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

**Minimal example (identity SO):**

```csharp
[CreateAssetMenu(menuName = "LastBreath/BarDefinition")]
public sealed class BarDefinition : ScriptableObject
{
    // Identity-only fields. Read at scene load by the custodian
    // (e.g., FlagSystem reads FlagDefinition.defaultValue once at Awake).
    public string id;
    public string displayName;
    public bool defaultValue;
}
```

**Anti-patterns:**

```csharp
// 1. Mutable runtime state on a SO — leaks across sessions in the editor.
public sealed class BarConfig : ScriptableObject
{
    public float CurrentValue;
}

// 2. SO event channel — forbidden by ADR-0004.
public sealed class BazEventChannel : ScriptableObject
{
    public event Action<BazEvent> Raised;
    public void Raise(BazEvent e) => Raised?.Invoke(e);
}

// 3. SO runtime registry (RuntimeSet<T>) — also forbidden by ADR-0004.
//    Live collections of "things currently in the world" belong to a
//    MonoBehaviour custodian (e.g., InteractableRegistry), not a SO.
public sealed class FooRuntimeSet : ScriptableObject
{
    public List<FooBehaviour> Items;
    public void Add(FooBehaviour f) => Items.Add(f);
}
```

**Rule cross-ref:** `.claude/rules/gameplay-code.md` (`GAMEPLAY-CODE-FLAG-NO-SO-EVENT-CHANNEL`); ADR-0004; ADR-0006 for `MotherAvailabilityRule` as an identity SO.

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
    [Inject] private BarSystem _bar;
    private void OnEnable()  { _bar.OnRaised += HandleRaised; }
    private void OnDisable() { _bar.OnRaised -= HandleRaised; }
    private void HandleRaised(BazEvent e) { /* ... */ }
}
```

The publisher is a sibling system resolved through the VContainer `LifetimeScope` (ADR-0009) and exposes a plain C# `event Action<T>`. ScriptableObject event channels are banned by ADR-0004 (see pattern 3).

**Anti-pattern:**

```csharp
private void OnEnable() { _bar.OnRaised += e => DoStuff(e); } // cannot unsubscribe.
```

**Rule cross-ref:** `.claude/rules/gameplay-code.md` (Events); ADR-0004 (`GAMEPLAY-CODE-FLAG-NO-SO-EVENT-CHANNEL`).

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

**When to use:** Sibling systems resolved through the scene's VContainer `LifetimeScope` (ADR-0009). Live registries belong to a MonoBehaviour custodian (e.g., `InteractableRegistry`), not a ScriptableObject. Fire-and-forget signalling uses C# events on the publishing system, not SO event channels (forbidden by ADR-0004; see pattern 3).

**Minimal example:**

```csharp
using VContainer;
using VContainer.Unity;
using UnityEngine;

public sealed class GameLifetimeScope : LifetimeScope
{
    // Inspector-bound config SOs (identity / tuning, no runtime mutation).
    [SerializeField] private BarConfig _barConfig;

    protected override void Configure(IContainerBuilder builder)
    {
        builder.RegisterInstance(_barConfig);
        builder.RegisterComponentInHierarchy<FooBehaviour>();
        builder.RegisterComponentInHierarchy<BarBehaviour>();
    }
}

public sealed class BarBehaviour : MonoBehaviour
{
    [Inject] private FooBehaviour _foo;
    // Cross-system reference resolved by the scope at runtime.
}
```

**Anti-pattern:**

```csharp
private void Start() { var foo = GameObject.Find("Foo").GetComponent<FooBehaviour>(); }
// Also anti-pattern:
//   - a manual GameSystemsRoot MonoBehaviour with a [SerializeField] slot per system.
//   - SO-backed RuntimeSet<T> / EventChannel<T> for runtime gameplay state (ADR-0004).
```

**Rule cross-ref:** `.claude/rules/gameplay-code.md` (Forbidden in systems; `GAMEPLAY-CODE-DI-LIFETIMESCOPE-ONLY-AT-ROOT`; `GAMEPLAY-CODE-FLAG-NO-SO-EVENT-CHANNEL`).

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

## 14. Prefab discipline

**When to use:** Every GameObject that appears more than once or that a system instantiates at runtime is a prefab under `src/Assets/_Project/Prefabs/<Category>/`. Composition is via nested prefabs, not copy-paste.

**Minimal example:**

```text
src/Assets/_Project/Prefabs/
  Level/CorridorPanel/CorridorPanel.prefab              // base
  Level/CorridorPanel/CorridorPanel.Damaged.prefab      // variant (see pattern 15)
  Player/Player.prefab                                  // composes nested PlayerHand.prefab
```

In a `.unity` scene, every instance of `CorridorPanel` appears as a prefab instance — the YAML carries `m_PrefabInstance` and a non-zero `m_CorrespondingSourceObject`. Edits flow back to the prefab; scene-only overrides are explicit and minimal.

**Anti-pattern:**

```text
# Three copies of "CorridorPanel" in CorridorC7.unity, no m_PrefabInstance —
# someone Unpack-ed the prefab and edited each in isolation. Now a fix to
# the base panel needs three manual edits. Forbidden in committed scenes.
```

**Rule cross-ref:** `.claude/rules/level-design.md` (`LEVEL-DESIGN-PREFAB-DISCIPLINE`).

Reviewer rule_id: UNITY-PATTERN-PREFAB-DISCIPLINE

## 15. Prefab variants

**When to use:** A family of "same thing, different config" objects (intact / damaged / dark; common / rare / boss). One base prefab; siblings are variants, not flat duplicates.

**Minimal example:**

```text
CorridorPanel.prefab           # base — mesh, material, collider, FlagSetter component
CorridorPanel.Damaged.prefab   # variant — overrides material slot + adds Sparks particle
CorridorPanel.Dark.prefab      # variant — overrides emission color, disables Light child
```

Each variant's `.prefab` YAML carries `m_VariantParent` pointing at the base. A change to the base's mesh propagates to all variants; only the explicitly-overridden fields stay variant-local.

**Anti-pattern:**

```text
# Three independent prefabs CorridorPanelIntact.prefab, CorridorPanelDamaged.prefab,
# CorridorPanelDark.prefab — produced by Duplicate. m_VariantParent: fileID: 0
# in all three. Drift between siblings is now guaranteed.
```

**Rule cross-ref:** `.claude/rules/level-design.md` (`LEVEL-DESIGN-VARIANTS-OVER-DUPLICATION`).

Reviewer rule_id: UNITY-PATTERN-VARIANTS

## 16. GPU instancing & material discipline

**When to use:** Any material applied to a mesh that appears more than once in a frame (props, panels, modular geometry). Enable "Enable GPU Instancing" on the material; in `.mat` YAML this is `m_EnableInstancingVariants: 1`. Static, non-moving geometry additionally gets the `Static` flag for batching.

**Minimal example:**

```text
# CorridorWall.mat (URP/Lit shader, repeated 40x in the corridor scene)
m_EnableInstancingVariants: 1
# CorridorWall GameObject in the scene: Static flag enabled.
```

Per-renderer tweaks use `MaterialPropertyBlock`, not new material instances:

```csharp
public sealed class FooHighlight : MonoBehaviour
{
    [SerializeField] private Renderer _renderer;
    private MaterialPropertyBlock _mpb;
    private void OnEnable() { _mpb ??= new MaterialPropertyBlock(); }
    public void SetTint(Color c) { _renderer.GetPropertyBlock(_mpb); _mpb.SetColor("_BaseColor", c); _renderer.SetPropertyBlock(_mpb); }
}
```

**Anti-pattern:**

```csharp
// Breaks batching: assigning .material clones the material per-renderer.
_renderer.material.color = Color.red;
```

```text
# CorridorWall.mat with m_EnableInstancingVariants: 0 despite 40 copies in-scene.
# Each instance is its own draw call; URP can't batch.
```

Opt-out cases (transparent particles, sprites, materials authored by a third party) get a one-line note in the matching art asset's `manifest.notes` and the verifier accepts them.

**Rule cross-ref:** `.claude/rules/level-design.md` (`LEVEL-DESIGN-GPU-INSTANCING-ENABLED`).

Reviewer rule_id: UNITY-PATTERN-GPU-INSTANCING

## 17. Tags & layers

**When to use:** Tags identify *what* an object is for gameplay queries. Layers define *which* set an object belongs to for physics, raycasts, and rendering masks. The two are not interchangeable.

**Minimal example:**

```text
# Layer (physics): "InteractableMask" defined in TagManager.asset; PlayerInteractor
# raycasts against (1 << LayerMask.NameToLayer("InteractableMask")).
# Tag (identity): "Breathing Station" declared in TagManager.asset AND registered in
# docs/registry/architecture.yaml under tags: with id TAG-BREATHING-STATION.
```

C# never hardcodes tag string literals. Use a generated constants file or a `TagDefinition` ScriptableObject:

```csharp
// Generated by an Editor MenuItem from TagManager.asset
public static class Tags
{
    public const string BreathingStation = "Breathing Station";
    public const string OxygenStation    = "Oxygen Station";
}

// Usage:
if (other.CompareTag(Tags.BreathingStation)) { /* ... */ }
```

**Anti-pattern:**

```csharp
if (other.CompareTag("Breathing Station")) { /* ... */ }     // string literal, drifts silently when the tag is renamed.
if (other.tag == "Breathing Station") { /* ... */ }          // .tag allocates; CompareTag does not — but the literal is still the real problem.
```

```text
# TagManager.asset declares "Breathing Station" but architecture.yaml has no entry
# under tags:. The reviewer fails the commit: every active tag must be registered.
```

**Rule cross-ref:** `.claude/rules/level-design.md` (`LEVEL-DESIGN-TAGS-REGISTERED`), `.claude/rules/gameplay-code.md` (`GAMEPLAY-CODE-NO-TAG-STRING-LITERALS`).

Reviewer rule_id: UNITY-PATTERN-TAGS-AND-LAYERS
