# Unity — Current Best Practices (PoC)

Accepted patterns for Last Breath. Not an exhaustive guide — just what applies to the PoC.

## Folder structure

```
src/Assets/
  _Project/
    Art/
    Audio/
    Prefabs/
    Scenes/
    Scripts/
      Core/         # GameManager, events, configs
      Gameplay/     # Oxygen, Agitation, Presence, Player, Interactor, Environment
      UI/
    Settings/       # URP assets, Input Actions, Volume profiles
    ScriptableObjects/  # OxygenConfig, AgitationConfig, etc.
  _Sandbox/         # prototypes, scratch
  ThirdParty/       # external packages imported as assets
```

Leading underscore = alphabetically sorted to the top.

## Assemblies

Three minimum `.asmdef`:

- `LastBreath.Core` — events, configs, shared types. No dependencies.
- `LastBreath.Gameplay` — systems. Depends on Core.
- `LastBreath.UI` — HUD, overlay. Depends on Core.

Editor scripts in `LastBreath.<X>.Editor`.

## ScriptableObjects for configs

Any value that designers want to tune = ScriptableObject. Hardcoding constants in MonoBehaviours is an anti-pattern.

## Input

- Use `InputAction` and `PlayerInput` from the new Input System.
- A single `LastBreath.inputactions` with action maps `Player`, `UI`, `Debug`.
- Runtime-configurable bindings are not needed for the PoC.

## Cinemachine

- One `CinemachineVirtualCamera` per scene for the FPS rig.
- Modify shake and FOV via parameters, never by directly scripting the camera.

## URP & Volumes

- One `Global Volume` per scene with the base profile.
- `Local Volume` with a `Box Collider` (trigger) per zone if you need to swap postprocessing on enter/exit.
- Glitches and flickers via `Volume Profile` swap or via script touching `VolumeComponent`.

## Inspector events

`UnityEvent` when the event is wired in the inspector (interactions, scene triggers).
`event Action<T>` when wired by code (systems talking to each other).

## Prefab variants

- Base prefab with the generic structure (e.g., `Interactable_Base`).
- Variants per concrete type (`Interactable_OxygenStation`, `Interactable_Panel`).
- Editing the base impacts all variants — useful.

## Performance

- Do not run `Update` per frame on things that do not need it. Use `InvokeRepeating` or a manual timer.
- Audio sources: pool. No `Instantiate` per SFX.
- Baked lights whenever possible. Real-time only where there is flicker or presence.
