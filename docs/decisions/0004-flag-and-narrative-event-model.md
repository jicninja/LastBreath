---
id: ADR-0004-flag-and-narrative-event-model
type: decision
status: accepted
date: 2026-05-12
related: [PLAN-004, SYS-FLAGS, SYS-NARRATIVE]
---

# ADR 0004: Flag and narrative event model

## Context

The PoC is shifting into a graphic-adventure shape: many gameplay events unlock other events (interactables that appear after a flag, dialogue cues triggered when a panel is read, doors gated on flag combinations). The existing event model — one C# event per system, registered in `architecture.yaml` — covers transient signals well but does not name "persistent boolean state shared by many readers."

Two industry patterns exist for this in Unity:

- **MonoBehaviour custodian + ScriptableObject definitions**: a single `FlagSystem` MonoBehaviour owns runtime state; flags are `FlagDefinition` ScriptableObjects (identity + metadata) referenced from triggers and gates.
- **Ryan Hipple SO event channels** ("Game Architecture with Scriptable Objects", Unite Austin 2017): each flag *is* a ScriptableObject that holds its own runtime value and raises its own observers; no central custodian.

The choice is non-obvious, semi-irreversible, and shapes how every future interactable, gate, and cue is authored. It needs an ADR.

## Decision

Adopt the **MonoBehaviour custodian + SO definitions** pattern.

- `SYS-FLAGS` → `FlagSystem : MonoBehaviour`, lives in `GameSystemsRoot`. Owns the runtime dict of flag values. Publishes `EVT-flag-changed { flag_id, value }`. API: `Set(FlagDefinition, bool)`, `IsSet(FlagDefinition)`, `event Action<FlagDefinition, bool> OnFlagChanged`.
- `CFG-FLAG` → `FlagDefinition : ScriptableObject { flagId, displayName, defaultValue, isSavePoint }`. One asset per flag. Used as the *identity* in API calls (reference equality), not strings.
- `SYS-NARRATIVE` → `NarrativeDirector : MonoBehaviour`. Mirrors `PresenceDirector`. Subscribes to `EVT-flag-changed`, evaluates `NarrativeCueDefinition` assets, publishes `EVT-narrative-cue-fired`.
- `CFG-NARRATIVE-CUE` → `NarrativeCueDefinition : ScriptableObject { cueId, requiredFlags[], setsFlags[], oneShot, audio, text }`.
- Designer-side wiring **inside a single prefab** (a `FlagGate` that opens a door and plays a sound) uses `UnityEvent` on the `FlagGate` / `FlagSetter` components. `UnityEvent` is allowed only on these designer-wire components, never on systems.

This extends, not replaces, the existing event model. C# events remain the contract between systems.

## Alternatives considered

- **Hipple-style SO event channels for everything.** Rejected because (1) runtime state in assets persists across play-mode sessions in editor — a documented bug-magnet that requires `OnEnable` reset boilerplate, eroding the inspector-debug benefit; (2) `architecture.yaml` models "one event = one publisher", and SO events can be `.Raise()`d from anywhere — the registry contract becomes unenforceable; (3) typed payloads force a proliferation of `GameEventInt`/`GameEventString`/... subclasses or degenerate to `object`; (4) refactor traceability degrades — `.Raise()` calls from C# are only findable by grep; (5) the team is one person, so the authoring-speed gain that justifies Hipple for designer-heavy studios does not apply here. Appendix below documents how it would be built if the decision is reversed.
- **Static `EventBus<T>`.** Rejected: hidden coupling, breaks the anti-singleton rule in `.claude/rules/gameplay-code.md`, lifecycle cleanup is invisible.
- **`UnityEvent` everywhere, including system-to-system.** Rejected: inspector references break on prefab reimport, weak typing, untrackable in `architecture.yaml`.

## Consequences

- **Easy:** flags and cues are designer-authorable (drop a `FlagDefinition` asset on a trigger). Runtime state lives in one place per system, debuggable in the inspector at runtime. Save/restore is plain dict serialization (see ADR-0005). No proliferation of `*Variable`/`*Event` SO subclasses.
- **Hard:** every new flag is two clicks (create SO + reference it). Every reaction component must hold a serialized ref to `FlagSystem` or read it through a small helper. Cross-scene flag wiring requires `FlagSystem` in every scene or `DontDestroyOnLoad`.
- **Accepted loss:** Hipple's "asset reference works across scenes for free" is given up.
- **Reviewer cost:** `code-reviewer` must reject SO-event-channel patterns if they appear — rule `FLAG-NO-SO-EVENT-CHANNEL`, added in PLAN-004.

## Notes

Migrating MonoBehaviour-custodian → SO-event-channels later is cheaper than the reverse, so this decision is intentionally the lower-commitment direction. If designer authoring becomes the bottleneck (e.g., the project grows past solo-dev), supersede this ADR.

## Appendix: how Hipple-style would look

Documented for future reference. *Not* the chosen path. Kept concrete enough to actually implement if a later ADR reverses this one.

**Flag as a runtime variable SO:**

```csharp
[CreateAssetMenu(menuName = "LastBreath/Variables/Bool")]
public class BoolVariable : ScriptableObject
{
    [SerializeField] private bool _initialValue;
    [NonSerialized]  private bool _runtimeValue;
    public event Action<bool> OnChanged;

    private void OnEnable() => _runtimeValue = _initialValue;   // reset between play sessions
    public bool Value
    {
        get => _runtimeValue;
        set
        {
            if (_runtimeValue == value) return;
            _runtimeValue = value;
            OnChanged?.Invoke(value);
        }
    }
}
```

**Generic listener component**, dropped on any GameObject that should react:

```csharp
public class BoolVariableListener : MonoBehaviour
{
    [SerializeField] private BoolVariable    _variable;
    [SerializeField] private UnityEvent<bool> _onChanged;

    private void OnEnable()  => _variable.OnChanged += Forward;
    private void OnDisable() => _variable.OnChanged -= Forward;
    private void Forward(bool v) => _onChanged.Invoke(v);
}
```

**Narrative cue as an event channel SO:**

```csharp
[CreateAssetMenu(menuName = "LastBreath/Events/Cue")]
public class CueEventChannel : ScriptableObject
{
    public event Action<string> OnRaised;
    public void Raise(string cueId) => OnRaised?.Invoke(cueId);
}
```

A door references the `BoolVariable` directly; a dialogue trigger calls `.Raise()` on the `CueEventChannel`. No `FlagSystem`, no `NarrativeDirector` — both vanish. Save/restore in this model requires a GUID resolver layer (see ADR-0005 Appendix). Every flag and cue becomes one extra asset; the project's `Data/Flags/` and `Data/Cues/` folders are the system. The reviewer rule `FLAG-NO-SO-EVENT-CHANNEL` would have to be removed.
