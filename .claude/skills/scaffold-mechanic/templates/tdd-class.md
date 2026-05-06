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

## Public API
- TODO: methods, events, properties.

## Dependencies
- TODO: serialised refs and event subscriptions.

## Test plan
- EditMode: TODO.
- PlayMode smoke: TODO.

## {{name-kebab}}config

`{{Name}}Config` is a ScriptableObject holding the tunable parameters for `{{Name}}System`.
