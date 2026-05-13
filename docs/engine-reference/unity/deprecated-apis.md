# Unity — Forbidden APIs

APIs that are **not** used in this project, with their alternative.

## Input

| Forbidden | Use |
|---|---|
| `Input.GetKey`, `Input.GetAxis`, `Input.mousePosition` (legacy) | `InputAction`, `PlayerInput` (new Input System) |

Reason: the legacy Input Manager is outside the new Input System and mixing the two produces subtle bugs.

## GameObject lookup

| Forbidden | Use |
|---|---|
| `GameObject.Find` | Serialized reference, or resolve via the scene's VContainer `LifetimeScope` (ADR-0009) |
| `FindObjectOfType` | Same (exception: `Awake` of the scene's `LifetimeScope`, when no other option exists) |
| `FindGameObjectsWithTag` | A pool registered by the owning system |
| `Camera.main` in `Update` | Cache in `Awake` |

## Resource loading

| Forbidden | Use |
|---|---|
| `Resources.Load` | Serialized reference, or `AssetReference<T>` + Addressables (advisory rule `GAMEPLAY-CODE-ADDRESSABLES-FOR-RUNTIME-LOAD`, ADR-0009) |

## Global singletons

| Forbidden | Use |
|---|---|
| `public static Instance` with auto-init | Register on the scene's VContainer `LifetimeScope` and resolve via constructor injection or `[Inject]` (ADR-0009) |

## Persistence

| Forbidden | Use |
|---|---|
| `PlayerPrefs` for game state | We do not persist in the PoC |
| `PlayerPrefs` for debug toggles | Allowed only in classes under `_Sandbox` |

## Physics

| Forbidden | Use |
|---|---|
| Modifying `transform.position` to move rigidbodies | `Rigidbody.MovePosition` |
| `OnCollisionEnter` without checking layer | A configured layer collision matrix |

## UI

| Forbidden | Use |
|---|---|
| IMGUI (`OnGUI`) at runtime | UI Toolkit or uGUI as appropriate |
| `IMGUI` is allowed only for `DebugOverlay` |  |

## Render

| Forbidden | Use |
|---|---|
| Built-in render pipeline | URP (the only supported pipeline) |
| HDRP | URP |
| Post-processing v2 | URP Volume System |

## Coroutines

| Forbidden | Use |
|---|---|
| Nested coroutines for gameplay logic | State machine + Update |
| Coroutines for UI timers | Accumulated `Time.deltaTime` |

Coroutines are still valid for fades, short transitions, one-shot sequences.
