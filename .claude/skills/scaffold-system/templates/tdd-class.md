---
id: CLASS-{{Name}}System
type: class
layer: tdd
status: poc
related: [SYS-{{NAME}}]
---

# {{Name}}System

## Class signature

```csharp
public class {{Name}}System : MonoBehaviour
{
    [SerializeField] private {{Name}}Config _config;
}
```

For systems with formula-bearing logic, the public class above is a thin Unity-side adapter; the actual logic lives in a plain C# class per `docs/process/unity-patterns.md` §2 (monobehaviour-split). Presentation-only systems can keep all logic in the MonoBehaviour.

## Public API
- TODO: methods, events, properties.

## Dependencies
- Serialised refs: TODO.
- Event subscriptions (subscribed in `OnEnable`, unsubscribed in `OnDisable`):
  TODO.

## Test plan
- EditMode: TODO. For presentation-only systems, EditMode coverage may be minimal — test pure helpers and config-driven calculations only.
- PlayMode smoke: TODO. Confirm any published event fires with the correct payload under a representative input.

## {{name-kebab}}config

`{{Name}}Config` is a ScriptableObject holding the tunable parameters for `{{Name}}System`.
