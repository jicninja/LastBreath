# Last Breath - Technical Design Document PoC

## Goal

Define a simple Unity C# implementation for the *Last Breath* PoC. This document brings the architecture down to concrete scripts, `Update` flow, prefabs, and code samples.

Priorities:
- Implement fast.
- Keep code easy to understand.
- Avoid complex patterns.
- Allow Inspector balance.
- Have a 3 to 5 minute playable scene.

## Technical Assumptions

- Unity 6 LTS with URP (`docs/engine-reference/unity/VERSION.md`).
- VContainer (`jp.hadashikick.vcontainer`) for DI; one `LifetimeScope` per scene (ADR-0009).
- UniTask (`com.cysharp.unitask`) for async; raw `Task` only at the transport boundary.
- Addressables (`com.unity.addressables`) recommended for runtime-loaded content; advisory rule.
- A single main scene: `SCN_PoC_C7`.
- **2.5D**: a billboard 2D sprite character moving on the **XZ plane** of a perspective 3D scene. Y is locked at 0 in the PoC (see ADR-0010).
- 2D sprites for the character (billboarded around world Y) and select environment props.
- Trigger-driven presence events, not AI.
- Input via `com.unity.inputsystem 1.11.2` only — legacy `Input` API is forbidden. Devices: keyboard and gamepad. Actions: `Move`, `Run`, `Interact`, `Pause` (see ADR-0010 and `§PlayerControls.inputactions`).
- Cinemachine 3 `CinemachineCamera` side-rig with URP `Volume` depth of field in Bokeh mode (see ADR-0010 and `§CameraSystem`).

## DI, Async, and Asset Loading

These three subsections capture the runtime conventions that bind every C# class under `src/Assets/_Project/**`. They derive from ADR-0009. Reviewer rules in `.claude/rules/gameplay-code.md` cite this section.

### DI — VContainer

- One `LifetimeScope` subclass per playable scene (`GameLifetimeScope` for `SCN_PoC_C7`); see `§Prefab Organization → GameLifetimeScope (VContainer composition root)`.
- Cross-system references resolve through the container:
  ```csharp
  public class DialogueSystem : MonoBehaviour, ISaveable<DialogueDto>
  {
      [Inject] private FlagSystem _flagSystem;
      [Inject] private GameManager _gameManager;
      [Inject] private OxygenSystem _oxygenSystem;
      [Inject] private AgitationSystem _agitationSystem;
      [Inject] private EnvironmentSystem _environmentSystem;
      [Inject] private ObjectiveSystem _objectiveSystem;
      [Inject] private IDialogueTransport _transport;
      [Inject] private DialogueLogic _dialogueLogic;

      [SerializeField] private DialogueAIConfig _aiConfig;
      [SerializeField] private LlmTransportConfig _transportConfig;
      [SerializeField] private List<DialogueCueDefinition> _allCues;
      // ↑ ScriptableObject and data refs remain serialized; cross-system refs do not.
  }
  ```
- Plain-C# collaborators (e.g., `DialogueLogic`) use constructor injection.
- Test scopes (`TestLifetimeScope`) override the production registration:
  ```csharp
  builder.Register<IDialogueTransport, MockTransport>(Lifetime.Scoped); // overrides OllamaHttpTransport
  ```
- Reviewer rule: `GAMEPLAY-CODE-DI-LIFETIMESCOPE-ONLY-AT-ROOT`.

### Async — UniTask

- All async methods inside `_Project/` return `UniTask` / `UniTask<T>`:
  ```csharp
  public async UniTask<DialogueResponse> SubmitTurnAsync(string playerText, string activeTerminalId)
  {
      var transportResult = await _transport.SendAsync(prompt, ct).AsUniTask();
      // ...
  }
  ```
- Transport boundary returns raw `Task` (ADR-0006). Adapt at the use site with `.AsUniTask()`.
- Engine awaitables wrap at the call site: `await Addressables.LoadAssetAsync<T>(...).ToUniTask()`, `await SceneManager.LoadSceneAsync(...).ToUniTask()`.
- Fire-and-forget uses `UniTaskVoid`, never `async void`:
  ```csharp
  private async UniTaskVoid PlayPresenceCueAsync(PresenceEventDefinition def) { /* ... */ }
  ```
- Cancellation: every public `UniTask`-returning method takes a `CancellationToken` (default to `destroyCancellationToken` at the MonoBehaviour boundary).
- Reviewer rule: `GAMEPLAY-CODE-PREFER-UNITASK`.

### Asset loading — Addressables (advisory)

- `Resources.Load` stays banned (blocking; existing rule line 47).
- `AssetDatabase.LoadAssetAtPath` is editor-only and forbidden at runtime.
- Default pattern remains `[SerializeField]` inspector binding for `CFG-*` and prefab references. Most PoC content lands this way.
- For runtime-loaded content (rare in the PoC; future expansion):
  ```csharp
  [SerializeField] private AssetReferenceGameObject _crewmatePrefab;

  private async UniTask SpawnCrewmateAsync(Vector3 at, CancellationToken ct)
  {
      var handle = _crewmatePrefab.InstantiateAsync(at, Quaternion.identity);
      var instance = await handle.ToUniTask(cancellationToken: ct);
      // ...
      // On despawn: Addressables.ReleaseInstance(instance);
  }
  ```
- `Addressables.Release` / `ReleaseInstance` paired with every load. The reviewer flags unreleased handles advisory.
- Reviewer rule: `GAMEPLAY-CODE-ADDRESSABLES-FOR-RUNTIME-LOAD` (advisory).

## Script Structure

```text
src/Assets/
  LastBreath/
    Scripts/
      Core/
        GameManager.cs
        GameState.cs
        PocCheckpointController.cs  // legacy, registry-only (ADR-0005); SaveSystem replaces it.
      Player/
        PlayerController.cs
        PlayerState.cs
        PlayerInteractor.cs
      Systems/
        OxygenSystem.cs
        AgitationSystem.cs
        EnvironmentSystem.cs
        PresenceDirector.cs
      Interactions/
        IInteractable.cs
        DoorInteractable.cs
        OxygenStationInteractable.cs
        PickupInteractable.cs
        PanelInteractable.cs
      Presence/
        PresenceEventDefinition.cs
        PresenceEventTrigger.cs
        PresenceAgitationTrigger.cs
        LightFlickerEffect.cs
        GlitchPulseEffect.cs
      UI/
        HudController.cs
        DebugOverlay.cs
      Data/
        OxygenConfig.cs
        AgitationConfig.cs
```

Practical rule:
- `Core`: global state.
- `Player`: input, movement, and player data.
- `Systems`: main rules.
- `Interactions`: usable objects.
- `Presence`: triggers and effects.
- `UI`: visualization.
- `Data`: balance ScriptableObjects.

## Main Classes

### GameManager

Coordinates the global flow. Does not compute oxygen or agitation.

Responsibilities:
- Current PoC state.
- Run start.
- Failure due to oxygen.
- Success when completing the objective.
- Pause or restart if needed.

```csharp
public enum GameState
{
    Boot,
    Intro,
    Playing,
    AirlockTransition,
    Paused,
    Loading,            // SaveSystem.Load is in progress; gameplay systems gate event publishing on State == Playing (ADR-0005).
    Completed,
    Failed
}
```

```csharp
using System;
using UnityEngine;

public class GameManager : MonoBehaviour
{
    public GameState CurrentState { get; private set; } = GameState.Boot;

    public event Action<GameState> OnStateChanged;

    private void Start()
    {
        SetState(GameState.Intro);
        SetState(GameState.Playing);
    }

    public bool IsGameplayActive()
    {
        return CurrentState == GameState.Playing;
    }

    public void SetState(GameState newState)
    {
        if (CurrentState == newState)
            return;

        CurrentState = newState;
        OnStateChanged?.Invoke(CurrentState);
    }

    public void FailRun()
    {
        SetState(GameState.Failed);
    }

    public void CompleteRun()
    {
        SetState(GameState.Completed);
    }
}
```

### Save and restore

The PoC's single autosave is the airlock save-point flag. Authoring details live in `§Save` (this document) and ADR-0005. The flow:

- A `FlagDefinition` whose `isSavePoint == true` is wired at the airlock interactable. Flipping it `true` for the first time triggers `SaveSystem.Save("autosave")`.
- On a fresh launch (or an explicit reload) `SaveSystem.Load("autosave")` walks each `ISaveable<TDto>` system and restores its DTO while `GameManager.CurrentState == GameState.Loading`. No system publishes events during `Loading`. When restore completes, `SaveSystem` raises `EVT-save-restored` exactly once and `GameManager` transitions back to `Playing`.

Older drafts of this TDD described a `PocCheckpointController` that hand-set transform / oxygen / agitation values in a `RestartFromAirlockCheckpoint()` method. That approach is **superseded by `SaveSystem`** — new gameplay code must not introduce a parallel checkpoint path. The class still exists in `architecture.yaml` as a registered identifier for backwards compatibility (`CLASS-PocCheckpointController`, status `deprecated`); reviewers reject new references to it.

### PlayerState

Simple data that other systems can read. Prevents each system from asking the `PlayerController` for different things.

```csharp
public enum EnvironmentZone
{
    Interior,
    Airlock,
    Exterior
}

public class PlayerState
{
    public bool IsMoving;
    public bool IsRunning;
    public EnvironmentZone CurrentZone = EnvironmentZone.Interior;
}
```

For the PoC it can be a regular C# class created by `PlayerController`, or a `MonoBehaviour` if it is more convenient to expose it in the Inspector.

### PlayerController

Responsibilities:
- Read input.
- Move the player.
- Update `PlayerState`.

Must not:
- Subtract oxygen.
- Raise agitation directly from presence events.
- Control objectives.

```csharp
using UnityEngine;
using UnityEngine.InputSystem;
using VContainer;

public class PlayerController : MonoBehaviour
{
    [SerializeField] private CharacterController _controller;
    [SerializeField] private PlayerMovementConfig _config;
    [SerializeField] private InputActionReference _moveAction;     // Value, Vector2
    [SerializeField] private InputActionReference _runAction;      // Button, Hold

    [Inject] private GameManager _gameManager;

    public PlayerState State { get; } = new PlayerState();

    private void OnEnable()
    {
        _moveAction.action.Enable();
        _runAction.action.Enable();
    }

    private void OnDisable()
    {
        _moveAction.action.Disable();
        _runAction.action.Disable();
    }

    private void Update()
    {
        if (_gameManager.CurrentState != GameState.Playing) return;

        Vector2 input = Vector2.ClampMagnitude(_moveAction.action.ReadValue<Vector2>(), 1f);
        bool wantsRun = _runAction.action.IsPressed();

        State.IsMoving  = input.sqrMagnitude > 0.01f;
        State.IsRunning = State.IsMoving && wantsRun;

        float speed = State.IsRunning ? _config.RunSpeed : _config.WalkSpeed;
        Vector3 movement = new Vector3(input.x, 0f, input.y);

        _controller.Move(movement * speed * Time.deltaTime);
    }
}
```

Notes:
- Movement is 3D on the XZ plane. `Move.x → world X`, `Move.y → world Z`. Y is locked at 0 in the PoC (no jump, no gravity).
- The controller owns no rotation. Sprite facing is the `PlayerBillboard`'s job (`§CameraSystem`).
- Action enable/disable is the suppression seam: when the terminal opens (`TerminalSystem`), or `GameManager.CurrentState` flips out of `Playing` (pause, loading), the action map is disabled and the controller short-circuits.
- `_runAction.action.IsPressed()` reads the current hold state every frame; the action is configured as `Button` with `Interactions = Hold` in `PlayerControls.inputactions` so it stays true while the key/shoulder is held.
- The four `InputActionReference` slots are bound to actions of `PlayerControls.inputactions` via the Inspector. `Interact` and `Pause` are read by other systems (`PlayerInteractor`, `GameManager`); the controller itself only needs `Move` and `Run`.
- Legacy `Input.GetAxis*`/`Input.GetKey*` are forbidden by ADR-0010 and `UNITY-PATTERN-INPUT-SYSTEM`. Active Input Handling in Player Settings is `Input System Package (New)` only (`docs/engine-reference/unity/VERSION.md`).

### PlayerMovementConfig

`ScriptableObject` for balance, mirrors `OxygenConfig`'s shape.

```csharp
using UnityEngine;

[CreateAssetMenu(menuName = "Last Breath/Player Movement Config")]
public class PlayerMovementConfig : ScriptableObject
{
    public float WalkSpeed = 2.5f;
    public float RunSpeed  = 4.0f;
}
```

### PlayerControls.inputactions

Authored once, committed at `src/Assets/_Project/Input/PlayerControls.inputactions`. Registered as `CFG-PLAYER-INPUT` (type `InputActionAsset`).

Action map: `Gameplay`.

| Action     | Type   | Interaction | Keyboard binding                                       | Gamepad binding                  |
|------------|--------|-------------|--------------------------------------------------------|----------------------------------|
| `Move`     | Value (Vector2) | —     | 2D composite `WASD`; second composite `Arrows`         | `<Gamepad>/leftStick`            |
| `Run`      | Button | Hold        | `<Keyboard>/leftShift`                                 | `<Gamepad>/leftShoulder` (hold)  |
| `Interact` | Button | Tap         | `<Keyboard>/e`                                         | `<Gamepad>/buttonSouth`          |
| `Pause`    | Button | Tap         | `<Keyboard>/escape`                                    | `<Gamepad>/start`                |

Notes:
- One action map only; control schemes (`Keyboard`, `Gamepad`) are auto-derived by the Input System from the bindings above.
- The asset is generated via the Unity Editor's `.inputactions` editor; do not hand-edit the JSON. The plan 007 step that authors the asset is the only place its binary changes.

## CameraSystem

Side-rig that follows the player on XZ and drives URP DOF in Bokeh mode. See SDD `§CameraSystem` and ADR-0010.

### PlayerBillboard

```csharp
using UnityEngine;

public class PlayerBillboard : MonoBehaviour
{
    private Transform _cameraTransform;

    private void Awake()
    {
        Camera mainCamera = Camera.main;
        _cameraTransform = mainCamera != null ? mainCamera.transform : null;
    }

    private void LateUpdate()
    {
        if (_cameraTransform == null) return;
        transform.rotation = Quaternion.Euler(0f, _cameraTransform.eulerAngles.y, 0f);
    }
}
```

Notes:
- Y-axis only. Camera pitch and roll never propagate to the sprite.
- `Camera.main` is cached at `Awake`; not called per frame.
- The Unity built-in `MainCamera` tag is exempt from `GAMEPLAY-CODE-NO-TAG-STRING-LITERALS` (engine-reserved).

### CameraRig

```csharp
using UnityEngine;
using Unity.Cinemachine;

public class CameraRig : MonoBehaviour
{
    [SerializeField] private CinemachineCamera _virtualCamera;
    [SerializeField] private CameraRigConfig _config;
    [SerializeField] private Transform _target;

    private void Awake()
    {
        _virtualCamera.Follow = _target;
        // Position Composer values come from _config; the actual extension fields are
        // configured on the CinemachineCamera asset in the editor, mirroring _config.
    }

    public static Vector3 ComputeFollowPosition(Vector3 target, Vector3 previous, float dt, CameraRigConfig config)
    {
        float kx = 1f - Mathf.Exp(-dt / Mathf.Max(config.DampingX, 0.0001f));
        float kz = 1f - Mathf.Exp(-dt / Mathf.Max(config.DampingZ, 0.0001f));
        float x = Mathf.Lerp(previous.x, target.x + config.OffsetX, kx);
        float z = Mathf.Lerp(previous.z, target.z + config.OffsetZ, kz);
        float y = previous.y; // Y is fixed by ADR-0010 §Decision item 4.
        return new Vector3(x, y, z);
    }
}
```

Notes:
- `ComputeFollowPosition` is a static pure function. EditMode tests call it directly without instantiating Cinemachine.
- Cinemachine 3 lives in the `Unity.Cinemachine` namespace; the deprecated CM2 `Cinemachine.CinemachineVirtualCamera` is forbidden by ADR-0010.

### CameraRigConfig

```csharp
using UnityEngine;

[CreateAssetMenu(menuName = "Last Breath/Camera Rig Config")]
public class CameraRigConfig : ScriptableObject
{
    public float OffsetX = 0f;
    public float OffsetY = 1.6f;
    public float OffsetZ = -6f;
    public float DampingX = 0.3f;
    public float DampingY = 0.0f;
    public float DampingZ = 0.5f;
    public float FieldOfView = 35f;
}
```

### CameraDofDriver

```csharp
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;

public class CameraDofDriver : MonoBehaviour
{
    [SerializeField] private Volume _volume;
    [SerializeField] private Transform _target;
    [SerializeField] private CameraDofConfig _config;

    private DepthOfField _dof;
    private Transform _cameraTransform;

    private void Awake()
    {
        Camera mainCamera = Camera.main;
        _cameraTransform = mainCamera != null ? mainCamera.transform : null;
        if (_volume != null && _volume.profile.TryGet(out DepthOfField dof))
        {
            _dof = dof;
            _dof.mode.value          = DepthOfFieldMode.Bokeh;
            _dof.aperture.value      = _config.Aperture;
            _dof.focalLength.value   = _config.FocalLength;
            _dof.bladeCount.value    = _config.BladeCount;
        }
    }

    private void LateUpdate()
    {
        if (_dof == null || _target == null || _cameraTransform == null) return;
        _dof.focusDistance.value = Vector3.Distance(_cameraTransform.position, _target.position);
    }
}
```

Notes:
- The driver reads `_target.position` and the camera's position. It does not touch any gameplay system.
- The `DepthOfField` override must already exist on the `Volume`'s profile, configured at edit time. The driver writes runtime values only.

### CameraDofConfig

```csharp
using UnityEngine;

[CreateAssetMenu(menuName = "Last Breath/Camera DOF Config")]
public class CameraDofConfig : ScriptableObject
{
    public float Aperture    = 5.6f;
    public float FocalLength = 70f;
    public int   BladeCount  = 6;
}
```

## Oxygen

### OxygenConfig

Use a `ScriptableObject` for balance.

```csharp
using UnityEngine;

[CreateAssetMenu(menuName = "Last Breath/Oxygen Config")]
public class OxygenConfig : ScriptableObject
{
    public float maxOxygen = 100f;
    public float baseDrainPerSecond = 0.4f;
    public float exteriorMultiplier = 1.5f;
    public float warningThreshold = 50f;
    public float criticalThreshold = 25f;
}
```

### OxygenSystem

Responsibilities:
- Hold the current oxygen value.
- Compute drain each frame.
- Apply multipliers.
- Notify when reaching zero.

Computation flow:

```text
if GameState != Playing:
    do not consume

baseDrain = OxygenConfig.baseDrainPerSecond
agitationMultiplier = AgitationSystem.OxygenMultiplier
environmentMultiplier = EnvironmentSystem.OxygenMultiplier
drain = baseDrain * agitationMultiplier * environmentMultiplier * deltaTime
currentOxygen -= drain
if currentOxygen <= 0:
    GameManager.FailRun()
```

Base code:

```csharp
using System;
using UnityEngine;

public class OxygenSystem : MonoBehaviour
{
    [SerializeField] private OxygenConfig config;
    [SerializeField] private GameManager gameManager;
    [SerializeField] private AgitationSystem agitationSystem;
    [SerializeField] private EnvironmentSystem environmentSystem;

    public float CurrentOxygen { get; private set; }
    public float Max => config.maxOxygen;
    public float Normalized => CurrentOxygen / config.maxOxygen;

    // Payload matches EVT-oxygen-changed in architecture.yaml: (current, max).
    // Consumers compute their own normalised value if needed.
    public event Action<float, float> OnOxygenChanged;
    public event Action OnOxygenDepleted;

    private bool isDepleted;

    private void Awake()
    {
        CurrentOxygen = config.maxOxygen;
    }

    public void SetOxygen(float amount)
    {
        isDepleted = false;
        CurrentOxygen = Mathf.Clamp(amount, 0f, config.maxOxygen);
        OnOxygenChanged?.Invoke(CurrentOxygen, config.maxOxygen);
    }

    private void Update()
    {
        if (!gameManager.IsGameplayActive())
            return;

        float drain = config.baseDrainPerSecond;
        drain *= agitationSystem.OxygenMultiplier;
        drain *= environmentSystem.OxygenMultiplier;
        drain *= Time.deltaTime;

        Consume(drain);
    }

    public void Consume(float amount)
    {
        if (isDepleted)
            return;

        CurrentOxygen = Mathf.Max(0f, CurrentOxygen - amount);
        OnOxygenChanged?.Invoke(CurrentOxygen, config.maxOxygen);

        if (CurrentOxygen <= 0f)
        {
            isDepleted = true;
            OnOxygenDepleted?.Invoke();
            gameManager.FailRun();
        }
    }

    public void Refill(float amount)
    {
        SetOxygen(CurrentOxygen + amount);
    }
}
```

## Agitation

### Simple state

For the PoC, two states are enough:

```csharp
public enum AgitationState
{
    Normal,
    Agitated
}
```

Rule:
- `Normal`: drain x1.
- `Agitated`: increased drain.

### AgitationConfig

```csharp
using UnityEngine;

[CreateAssetMenu(menuName = "Last Breath/Agitation Config")]
public class AgitationConfig : ScriptableObject
{
    public float maxAgitation = 100f;
    public float agitatedThreshold = 40f;
    public float runningGainPerSecond = 10f;
    public float exteriorGainPerSecond = 4f;
    public float calmLossPerSecond = 8f;
    public float agitatedOxygenMultiplier = 1.8f;
}
```

### AgitationSystem

Responsibilities:
- Raise agitation when running, being outside, or receiving events.
- Lower agitation when there is no pressure.
- Expose an oxygen multiplier.

```csharp
using System;
using UnityEngine;

public class AgitationSystem : MonoBehaviour
{
    [SerializeField] private AgitationConfig config;
    [SerializeField] private GameManager gameManager;
    [SerializeField] private PlayerController player;

    public float CurrentAgitation { get; private set; }
    public AgitationState CurrentState { get; private set; }
    public float OxygenMultiplier { get; private set; } = 1f;

    public event Action<float> OnAgitationChanged;
    public event Action<AgitationState> OnAgitationStateChanged;

    private void Update()
    {
        if (!gameManager.IsGameplayActive())
            return;

        float delta = 0f;

        if (player.State.IsRunning)
            delta += config.runningGainPerSecond;

        if (player.State.CurrentZone == EnvironmentZone.Exterior)
            delta += config.exteriorGainPerSecond;

        if (delta <= 0f)
            delta -= config.calmLossPerSecond;

        AddAgitation(delta * Time.deltaTime);
    }

    public void AddAgitation(float amount)
    {
        SetAgitation(CurrentAgitation + amount);
    }

    public void SetAgitation(float amount)
    {
        CurrentAgitation = Mathf.Clamp(
            amount,
            0f,
            config.maxAgitation
        );

        UpdateState();
        OnAgitationChanged?.Invoke(CurrentAgitation / config.maxAgitation);
    }

    private void UpdateState()
    {
        AgitationState nextState = CurrentAgitation >= config.agitatedThreshold
            ? AgitationState.Agitated
            : AgitationState.Normal;

        OxygenMultiplier = nextState == AgitationState.Agitated
            ? config.agitatedOxygenMultiplier
            : 1f;

        if (CurrentState == nextState)
            return;

        CurrentState = nextState;
        OnAgitationStateChanged?.Invoke(CurrentState);
    }
}
```

Notes:
- Agitation can drop even in the interior.
- Outside, it should always rise a bit to sustain tension.
- Do not add extra states until the PoC needs them.

## Flags

Persistent boolean world state for graphic-adventure unlocks (`SYS-FLAGS`, ADR-0004). The custodian is `FlagSystem`; identities are `FlagDefinition` ScriptableObjects. Designer-side reactions are wired on `FlagGate` and `FlagSetter` components.

`UnityEvent` is ONLY allowed on `FlagGate`, `FlagSetter`, and the future `NarrativeCueGate`. Never on systems. System-to-system communication remains C# events (`event Action<T>`).

### FlagDefinition

```csharp
using UnityEngine;

[CreateAssetMenu(menuName = "Last Breath/Flag")]
public class FlagDefinition : ScriptableObject
{
    public string flagId;
    public string displayName;
    public bool defaultValue;
    public bool isSavePoint;
}
```

One asset per flag. The `flagId` string is the disk-format key (used by `FlagDto`); inside C#, the `FlagDefinition` reference is the identity (reference equality), never the string.

### FlagSystem

Composed by `GameLifetimeScope` (ADR-0009 §DI). Holds no runtime system references — it is the lowest-layer state custodian.

```csharp
using System;
using System.Collections.Generic;
using UnityEngine;

public class FlagSystem : MonoBehaviour, ISaveable<FlagDto>
{
    // [SerializeField] is allowed: this is a list of inspector-bound config SOs
    // (FlagDefinition assets), not a runtime system reference. Per ADR-0009.
    [SerializeField] private List<FlagDefinition> _definitions;

    public event Action<FlagDefinition, bool> OnFlagChanged;

    public string SaveKey => "flags";

    public void Set(FlagDefinition flag, bool value);
    public bool IsSet(FlagDefinition flag);
    public void RestoreSilently(IReadOnlyDictionary<FlagDefinition, bool> values);

    public FlagDto CaptureState();
    public void RestoreState(FlagDto dto);

    private void Awake();
}
```

Contract:
- `Awake` initializes every known `FlagDefinition` to its `defaultValue`.
- `Set` is idempotent: if the new value equals the current value, no-op and no event.
- `Set` fires `OnFlagChanged(flag, value)` exactly once per real transition.
- `RestoreSilently` is the `SaveSystem`-only path: writes values without publishing `OnFlagChanged` (ADR-0005 invariant `SAVE-NO-EVENTS-DURING-LOADING`).
- `RestoreState(dto)` resolves each `FlagEntry.flagId` against `_definitions` and calls `RestoreSilently`.

No `FooLogic` split: pure state container, no formula. ADR-0002 §"Concretely, for a system named `Foo`" does not apply. Tested via EditMode smoke that constructs the MonoBehaviour and exercises `Set` / `IsSet` plus capture/restore round-trip.

### FlagGate

Designer-wire component on any GameObject that should react to a flag. The `LifetimeScope` injects `_flagSystem` after scene load (ADR-0009).

```csharp
using UnityEngine;
using UnityEngine.Events;
using VContainer;

public class FlagGate : MonoBehaviour
{
    // Runtime system ref via VContainer.
    [Inject] private FlagSystem _flagSystem;

    // Inspector-bound: SO ref, primitive, designer UnityEvents. All allowed per ADR-0009.
    [SerializeField] private FlagDefinition _requiredFlag;
    [SerializeField] private bool _expectedValue;
    [SerializeField] private UnityEvent _onConditionMet;
    [SerializeField] private UnityEvent _onConditionLost;

    private void OnEnable();
    private void OnDisable();
    private void HandleFlagChanged(FlagDefinition flag, bool value);
}
```

Contract:
- Subscribes to `FlagSystem.OnFlagChanged` in `OnEnable`, unsubscribes in `OnDisable` (symmetric).
- Filters by reference equality on `_requiredFlag`.
- Invokes `_onConditionMet` when the changed value equals `_expectedValue`, `_onConditionLost` otherwise.

### FlagSetter

Designer-wire component that flips a flag from a `UnityEvent` source (door trigger, dialog cue, debug button). The `LifetimeScope` injects `_flagSystem` after scene load (ADR-0009).

```csharp
using UnityEngine;
using VContainer;

public class FlagSetter : MonoBehaviour
{
    // Runtime system ref via VContainer.
    [Inject] private FlagSystem _flagSystem;

    // Inspector-bound: SO ref + primitive. Allowed per ADR-0009.
    [SerializeField] private FlagDefinition _flag;
    [SerializeField] private bool _value;

    public void Apply() => _flagSystem.Set(_flag, _value);
}
```

`Apply()` is the public method exposed for `UnityEvent` wiring from triggers.

## Narrative

Evaluates `NarrativeCueDefinition` assets against current flag state and publishes narrative cues (`SYS-NARRATIVE`, ADR-0004). Mirror of `PresenceDirector`.

### NarrativeCueDefinition

```csharp
using UnityEngine;

[CreateAssetMenu(menuName = "Last Breath/Narrative Cue")]
public class NarrativeCueDefinition : ScriptableObject
{
    public string cueId;
    public FlagDefinition[] requiredFlags;
    public FlagDefinition[] setsFlags;
    public bool oneShot;
    public AudioClip audioCue;
    public string text;
}
```

A cue fires when every `FlagDefinition` in `requiredFlags` resolves to `true` in `FlagSystem`. On firing, the director publishes `OnCueFired` and then sets every `FlagDefinition` in `setsFlags` to `true`. `oneShot` cues do not re-fire after their first firing per save.

### NarrativeDirector

Composed by `GameLifetimeScope` (ADR-0009 §DI; reviewer rule `GAMEPLAY-CODE-DI-LIFETIMESCOPE-ONLY-AT-ROOT`).

```csharp
using System;
using System.Collections.Generic;
using UnityEngine;
using VContainer;

public class NarrativeDirector : MonoBehaviour, ISaveable<NarrativeDto>
{
    // Inspector-bound config SO list — allowed per ADR-0009.
    [SerializeField] private List<NarrativeCueDefinition> _cues;

    // Runtime system refs via VContainer.
    [Inject] private FlagSystem _flagSystem;
    [Inject] private GameManager _gameManager;

    public event Action<NarrativeCueDefinition> OnCueFired;

    public string SaveKey => "narrative";

    public NarrativeDto CaptureState();
    public void RestoreState(NarrativeDto dto);

    private void OnEnable();
    private void OnDisable();
    private void HandleFlagChanged(FlagDefinition flag, bool value);
}
```

Contract:
- Subscribes to `FlagSystem.OnFlagChanged` in `OnEnable`, unsubscribes in `OnDisable`.
- On every flag change, while `_gameManager.CurrentState == GameState.Playing`, walks every non-fired cue and fires any whose `requiredFlags` are all currently true. Fires order: publish `OnCueFired(cue)` first, then apply `setsFlags`. This lets subscribers observe the cue before its cascade.
- If `_gameManager.CurrentState == GameState.Loading`, evaluation is skipped entirely. The `OnCueFired` event is not published during restore.
- `CaptureState` records the set of fired `oneShot` cue IDs into `NarrativeDto.firedOneShots`.
- `RestoreState` replaces the fired-set without publishing `OnCueFired` (silent restore, ADR-0005).

ADR-0002 split (borderline — evaluation logic against state):

Recommended refactor when implementing — `NarrativeEvaluator` (plain C#) + `NarrativeDirector` (MonoBehaviour adapter).

```csharp
public class NarrativeEvaluator
{
    public NarrativeEvaluator(IReadOnlyList<NarrativeCueDefinition> cues);

    public NarrativeCueDefinition NextCueToFire(
        IReadOnlyDictionary<FlagDefinition, bool> flagValues,
        IReadOnlyCollection<string> alreadyFiredOneShots);

    public void MarkFired(NarrativeCueDefinition cue);
    public IReadOnlyCollection<string> FiredOneShots { get; }
}
```

The `NarrativeDirector` MonoBehaviour owns the evaluator instance, forwards flag changes into it, and translates the chosen `NarrativeCueDefinition` into the published event plus `_flagSystem.Set` calls for `setsFlags`. `NarrativeEvaluator` is an implementation-detail helper, not a public registered class — it does not require its own `CLASS-*` ID.

EditMode tests target `NarrativeEvaluator` directly: given a flag-value dict and a fired-set, assert the expected `NarrativeCueDefinition` is returned (or null).

## Interior and Exterior

### EnvironmentSystem

Responsibilities:
- Hold the current zone.
- Expose a drain multiplier.
- Update `PlayerState`.

```csharp
using UnityEngine;

public class EnvironmentSystem : MonoBehaviour
{
    [SerializeField] private OxygenConfig oxygenConfig;
    [SerializeField] private PlayerController player;

    public EnvironmentZone CurrentZone { get; private set; } = EnvironmentZone.Interior;

    public float OxygenMultiplier
    {
        get
        {
            return CurrentZone == EnvironmentZone.Exterior
                ? oxygenConfig.exteriorMultiplier
                : 1f;
        }
    }

    public void SetZone(EnvironmentZone zone)
    {
        CurrentZone = zone;
        player.State.CurrentZone = zone;
    }
}
```

### EnvironmentZoneTrigger

```csharp
using UnityEngine;

public class EnvironmentZoneTrigger : MonoBehaviour
{
    [SerializeField] private EnvironmentSystem environmentSystem;
    [SerializeField] private EnvironmentZone zone;

    private void OnTriggerEnter(Collider other)
    {
        if (!other.CompareTag("Player"))
            return;

        environmentSystem.SetZone(zone);
    }
}
```

Use:
- A trigger in the airlock switches to `Exterior`.
- Another trigger on the way back switches to `Interior`.

## Presence System

### Goal

Fire simple ambient events:
- Sound.
- Light flicker.
- Screen glitch.
- Agitation increase.

There is no enemy, vision, pathfinding, or combat.

### PresenceEventDefinition

```csharp
using UnityEngine;

public enum PresenceEventType
{
    Sound,
    Lights,
    Glitch,
    Combined
}

[CreateAssetMenu(menuName = "Last Breath/Presence Event")]
public class PresenceEventDefinition : ScriptableObject
{
    public string eventId;
    public PresenceEventType type;
    public AudioClip audioClip;
    public float agitationGain = 15f;
    // Normalized 0..1 designer hint published as the EVT-presence-event-fired
    // `intensity` payload (architecture.yaml). Lighting/audio reactions scale on it.
    [Range(0f, 1f)] public float intensity = 0.5f;
    public float duration = 1f;
    public bool triggerOnce = true;
}
```

Fixed PoC assets:

| Asset | `eventId` | Type | Duration | Agitation |
| --- | --- | --- | --- | --- |
| `PE_CorridorLights` | `PRES_CORRIDOR_LIGHTS` | `Combined` | 1.5 s | 12 |
| `PE_AirlockBreath` | `PRES_AIRLOCK_BREATH` | `Sound` | 3.0 s | 10 |
| `PE_ExteriorBeacon` | `PRES_EXTERIOR_BEACON` | `Lights` | 1.0 s | 15 |
| `PE_AntennaBlackout` | `PRES_ANTENNA_BLACKOUT` | `Combined` | 2.0 s | 25 |
| `PE_ReturnDoor` | `PRES_RETURN_DOOR` | `Sound` | 6.0 s | 18 |

Do not create extra events until these five are implemented and tested.

`PRES_EXTERIOR_BEACON` fires on agitation >70 outside. If it did not happen before grabbing the module, use a `PresenceEventTrigger` as a fallback on the return path.

### PresenceDirector

Responsibilities:
- Run an event.
- Play sound.
- Call visual effects.
- Add agitation.

```csharp
using System;
using System.Collections;
using System.Collections.Generic;
using UnityEngine;

public class PresenceDirector : MonoBehaviour
{
    [SerializeField] private AudioSource presenceAudio;
    [SerializeField] private AgitationSystem agitationSystem;
    [SerializeField] private LightFlickerEffect lightFlickerEffect;
    [SerializeField] private GlitchPulseEffect glitchPulseEffect;

    private readonly HashSet<string> triggeredEvents = new HashSet<string>();

    public string LastEventId { get; private set; }

    // Payload matches EVT-presence-event-fired in architecture.yaml:
    // { event_id: string, intensity: float }.
    public event Action<string, float> OnPresenceEventFired;

    public void Play(PresenceEventDefinition definition)
    {
        if (definition.triggerOnce && triggeredEvents.Contains(definition.eventId))
            return;

        triggeredEvents.Add(definition.eventId);
        LastEventId = definition.eventId;
        OnPresenceEventFired?.Invoke(definition.eventId, definition.intensity);
        StartCoroutine(PlayRoutine(definition));
    }

    private IEnumerator PlayRoutine(PresenceEventDefinition definition)
    {
        agitationSystem.AddAgitation(definition.agitationGain);

        if (definition.audioClip != null)
            presenceAudio.PlayOneShot(definition.audioClip);

        if (definition.type == PresenceEventType.Lights ||
            definition.type == PresenceEventType.Combined)
        {
            lightFlickerEffect.Play(definition.duration);
        }

        if (definition.type == PresenceEventType.Glitch ||
            definition.type == PresenceEventType.Combined)
        {
            glitchPulseEffect.Play(definition.duration);
        }

        yield return new WaitForSeconds(definition.duration);
    }
}
```

### PresenceEventTrigger

```csharp
using UnityEngine;

public class PresenceEventTrigger : MonoBehaviour
{
    [SerializeField] private PresenceDirector director;
    [SerializeField] private PresenceEventDefinition eventDefinition;

    private void OnTriggerEnter(Collider other)
    {
        if (!other.CompareTag("Player"))
            return;

        director.Play(eventDefinition);
    }
}
```

### PresenceAgitationTrigger

Trigger without a collider for the exterior event by agitation threshold.

```csharp
using UnityEngine;

public class PresenceAgitationTrigger : MonoBehaviour
{
    [SerializeField] private AgitationSystem agitationSystem;
    [SerializeField] private EnvironmentSystem environmentSystem;
    [SerializeField] private PresenceDirector director;
    [SerializeField] private PresenceEventDefinition eventDefinition;
    [SerializeField] private float thresholdNormalized = 0.7f;

    private bool fired;

    private void OnEnable()
    {
        agitationSystem.OnAgitationChanged += HandleAgitationChanged;
    }

    private void OnDisable()
    {
        agitationSystem.OnAgitationChanged -= HandleAgitationChanged;
    }

    private void HandleAgitationChanged(float normalizedValue)
    {
        if (fired)
            return;

        if (environmentSystem.CurrentZone != EnvironmentZone.Exterior)
            return;

        if (normalizedValue < thresholdNormalized)
            return;

        fired = true;
        director.Play(eventDefinition);
    }
}
```

### LightFlickerEffect

```csharp
using System.Collections;
using UnityEngine;

public class LightFlickerEffect : MonoBehaviour
{
    [SerializeField] private Light[] lights;
    [SerializeField] private float flickerInterval = 0.08f;

    public void Play(float duration)
    {
        StartCoroutine(FlickerRoutine(duration));
    }

    private IEnumerator FlickerRoutine(float duration)
    {
        float timer = 0f;

        while (timer < duration)
        {
            bool enabledState = Random.value > 0.5f;

            foreach (Light targetLight in lights)
                targetLight.enabled = enabledState;

            timer += flickerInterval;
            yield return new WaitForSeconds(flickerInterval);
        }

        foreach (Light targetLight in lights)
            targetLight.enabled = true;
    }
}
```

### GlitchPulseEffect

Quick implementation:
- Activate a URP `Volume` with postprocessing effects.
- Raise intensity briefly.
- Return to zero.

```csharp
using System.Collections;
using UnityEngine;
using UnityEngine.Rendering;

public class GlitchPulseEffect : MonoBehaviour
{
    [SerializeField] private Volume glitchVolume;

    public void Play(float duration)
    {
        StartCoroutine(PulseRoutine(duration));
    }

    private IEnumerator PulseRoutine(float duration)
    {
        glitchVolume.weight = 1f;
        yield return new WaitForSeconds(duration);
        glitchVolume.weight = 0f;
    }
}
```

## Basic Interactions

### IInteractable

```csharp
public interface IInteractable
{
    string Prompt { get; }
    bool CanInteract { get; }
    void Interact(PlayerController player);
}
```

### PlayerInteractor

Trigger-based, event-driven against the Input System `Interact` action.

```csharp
using UnityEngine;
using UnityEngine.InputSystem;

public class PlayerInteractor : MonoBehaviour
{
    [SerializeField] private InputActionReference _interactAction; // Button, Tap

    private IInteractable _currentInteractable;

    private void OnEnable()
    {
        _interactAction.action.Enable();
        _interactAction.action.performed += OnInteractPerformed;
    }

    private void OnDisable()
    {
        _interactAction.action.performed -= OnInteractPerformed;
        _interactAction.action.Disable();
    }

    private void OnInteractPerformed(InputAction.CallbackContext ctx)
    {
        if (_currentInteractable == null || !_currentInteractable.CanInteract) return;
        PlayerController player = GetComponentInParent<PlayerController>();
        _currentInteractable.Interact(player);
    }

    private void OnTriggerEnter(Collider other)
    {
        _currentInteractable = other.GetComponent<IInteractable>();
    }

    private void OnTriggerExit(Collider other)
    {
        IInteractable interactable = other.GetComponent<IInteractable>();
        if (interactable == _currentInteractable)
            _currentInteractable = null;
    }
}
```

Notes:
- Reads the `Interact` action from `PlayerControls.inputactions` (`CFG-PLAYER-INPUT`), the same action asset `PlayerController` is bound to. See ADR-0010 §Decision item 1.
- Subscribes to `performed` (event-driven), never polls in `Update`. `Interactions = Tap` ensures the callback fires once per press.
- Suppression composes with the action map: when `TerminalSystem` or pause disables the `Gameplay` map, this consumer stops receiving callbacks. No `Update`-gating needed.
- A future camera raycast variant (for mouse-click interaction) would read a second action; the PoC ships trigger-based only.

### OxygenStationInteractable

```csharp
using UnityEngine;

public class OxygenStationInteractable : MonoBehaviour, IInteractable
{
    [SerializeField] private OxygenSystem oxygenSystem;
    [SerializeField] private float refillAmount = 35f;

    private bool used;

    public string Prompt => used ? "Empty" : "Refill oxygen";
    public bool CanInteract => !used;

    public void Interact(PlayerController player)
    {
        if (used)
            return;

        used = true;
        oxygenSystem.Refill(refillAmount);
    }
}
```

### PickupInteractable

```csharp
using UnityEngine;

public class PickupInteractable : MonoBehaviour, IInteractable
{
    [SerializeField] private string itemId = "energy_module";
    [SerializeField] private ObjectiveSystem objectiveSystem;

    public string Prompt => "Take module";
    public bool CanInteract => true;

    public void Interact(PlayerController player)
    {
        objectiveSystem.MarkItemCollected(itemId);
        gameObject.SetActive(false);
    }
}
```

### PanelInteractable

```csharp
using UnityEngine;

public class PanelInteractable : MonoBehaviour, IInteractable
{
    [SerializeField] private ObjectiveSystem objectiveSystem;
    [SerializeField] private GameManager gameManager;
    [SerializeField] private string requiredItemId = "energy_module";

    public string Prompt => "Insert module";
    public bool CanInteract => objectiveSystem.HasItem(requiredItemId);

    public void Interact(PlayerController player)
    {
        if (!CanInteract)
            return;

        gameManager.CompleteRun();
    }
}
```

## Minimum ObjectiveSystem

For the PoC, a real inventory is not needed. A `HashSet<string>` and a `CurrentObjectiveId` are enough.

```csharp
using System.Collections.Generic;
using UnityEngine;

public class ObjectiveSystem : MonoBehaviour
{
    private readonly HashSet<string> collectedItems = new HashSet<string>();

    public string CurrentObjectiveId { get; private set; } = "restore_power";

    public void SetObjective(string objectiveId)
    {
        CurrentObjectiveId = objectiveId;
    }

    public void MarkItemCollected(string itemId)
    {
        collectedItems.Add(itemId);
    }

    public void RemoveItem(string itemId)
    {
        collectedItems.Remove(itemId);
    }

    public bool HasItem(string itemId)
    {
        return collectedItems.Contains(itemId);
    }
}
```

It can be extended later to show objectives in UI, but do not block the first prototype on that.

## Save

DTO-snapshot save orchestrator (`SYS-SAVE`, ADR-0005). Only system permitted to touch disk. Restore drives the `GameState.Loading` window during which all gameplay systems gate their `Update` and event publishing on `State == Playing`.

### ISaveable&lt;TDto&gt;

Declared once. Every saveable system implements it for its DTO type.

```csharp
public interface ISaveable<TDto>
{
    string SaveKey { get; }
    TDto CaptureState();
    void RestoreState(TDto dto);
}
```

Contract:
- `SaveKey` is a stable string used only for diagnostics and migration mapping. It is not the disk-format key (the `SaveData` field name is).
- `CaptureState` returns a fresh DTO with no shared mutable references to runtime state.
- `RestoreState` writes runtime fields without publishing events. Systems entering `RestoreState` must assume `GameManager.CurrentState == GameState.Loading`.

### SaveData

Root `[Serializable]` class with one DTO field per saveable system.

```csharp
using System;
using System.Collections.Generic;

[Serializable]
public class SaveData
{
    public int version;
    public string saveId;
    public string sceneName;
    public long timestampUtc;

    public GameDto game;
    public PlayerDto player;
    public OxygenDto oxygen;
    public AgitationDto agitation;
    public EnvironmentDto environment;
    public FlagDto flags;
    public PresenceDto presence;
    public NarrativeDto narrative;
    public ObjectiveDto objective;
    public WorldObjectsDto worldObjects;
    public DialogueDto dialogue;
}
```

Per-system DTOs (plain `[Serializable]` classes, primitive fields only):

```csharp
[Serializable]
public class GameDto
{
    public GameState state;
}

[Serializable]
public class PlayerDto
{
    public float positionX;
    public float positionY;
    public float positionZ;
    public bool isRunning;
}

[Serializable]
public class OxygenDto
{
    public float current;
}

[Serializable]
public class AgitationDto
{
    public float current;
    public AgitationState state;
}

[Serializable]
public class EnvironmentDto
{
    public EnvironmentZone zone;
}

[Serializable]
public class FlagDto
{
    public List<FlagEntry> entries;
}

[Serializable]
public class FlagEntry
{
    public string flagId;
    public bool value;
}

[Serializable]
public class PresenceDto
{
    public List<string> firedEventIds;
    public string lastEventId;
}

[Serializable]
public class NarrativeDto
{
    public List<string> firedOneShots;
}

[Serializable]
public class ObjectiveDto
{
    public string currentObjectiveId;
    public List<string> collectedItems;
}

[Serializable]
public class WorldObjectsDto
{
    public List<InteractableEntry> entries;
}

[Serializable]
public class InteractableEntry
{
    public string persistenceId;
    public string stateJson;
}

[Serializable]
public class InteractableDto
{
    public string persistenceId;
}
```

Notes on shape:
- `FlagDto` serializes `flagId` as a string for the disk format. On `RestoreState`, `FlagSystem` re-resolves each `flagId` against its serialized `_definitions` list to recover the `FlagDefinition` reference, then calls `RestoreSilently`. Unknown ids (deleted flags) are ignored during restore and emit a warning.
- `WorldObjectsDto` uses the `InteractableEntry { persistenceId, stateJson }` envelope: each `IPersistentInteractable` serializes its own `InteractableDto` subclass into `stateJson` via `JsonUtility`. This decouples save format from concrete interactable shape and avoids needing a discriminator enum. `InteractableDto` is the base; concrete interactables extend it (e.g., `DoorDto : InteractableDto { bool isOpen; }`).
- `PresenceDto.firedEventIds` and `lastEventId` are added even though not strictly required by the brief: the `PresenceDirector` already tracks `triggeredEvents` (line ~624 in `PresenceDirector`) and `LastEventId`, and dropping them on restore would re-fire one-shot presence events.
- `DialogueDto` is the snapshot of `DialogueSystem` state (bounded `exchanges`, per-terminal `inbox`, `mandate`/`integrity`/`budget`, `turnCount`). Full shape declared in `§Dialogue → DialogueDto`. Endpoint URLs, model names, and any transport configuration are deliberately absent (reviewer rule `GAMEPLAY-CODE-DIALOGUE-NO-SECRETS-IN-SAVE`).

### SaveSystem

```csharp
using System;
using System.Collections;
using UnityEngine;

public class SaveSystem : MonoBehaviour
{
    [SerializeField] private GameManager _gameManager;
    [SerializeField] private PlayerController _player;
    [SerializeField] private OxygenSystem _oxygenSystem;
    [SerializeField] private AgitationSystem _agitationSystem;
    [SerializeField] private EnvironmentSystem _environmentSystem;
    [SerializeField] private FlagSystem _flagSystem;
    [SerializeField] private PresenceDirector _presenceDirector;
    [SerializeField] private NarrativeDirector _narrativeDirector;
    [SerializeField] private ObjectiveSystem _objectiveSystem;
    [SerializeField] private InteractableRegistry _interactableRegistry;
    [SerializeField] private DialogueSystem _dialogueSystem;

    public event Action<string> OnSaveCompleted;
    public event Action OnSaveRestored;

    public void Save(string slot);
    public IEnumerator Load(string slot);

    private void OnEnable();
    private void OnDisable();
    private void HandleFlagChanged(FlagDefinition flag, bool value);
    private static SaveData Migrate(SaveData data);
}
```

Contract:
- `Save(slot)` is synchronous: captures all DTOs into a fresh `SaveData`, writes JSON to disk under the slot, fires `OnSaveCompleted(slot)`.
- `Load(slot)` is a coroutine because of the optional scene-reload branch. Flow: set `GameState.Loading` -> read JSON -> `Migrate(data)` -> for each saveable system, call `RestoreState(dto)` -> fire `OnSaveRestored` -> set `GameState.Playing`.
- Subscribes to `FlagSystem.OnFlagChanged` in `OnEnable`, unsubscribes in `OnDisable`. When a flag transitions to `true` and `flag.isSavePoint == true`, calls `Save("autosave")`. No autosave-by-time.
- `Migrate(SaveData)` is a placeholder for version bumps. PoC: returns `data` unchanged; future format changes add `if (data.version < N)` branches.

ADR-0002 split: orchestration only, no formula. Exempt. EditMode tests target `Capture -> serialize -> deserialize -> Restore -> assert equality` per system, plus a schema test that every `ISaveable<T>` reference in `SaveSystem` is non-null at scene boot (`SaveSchema_AllSystemsRegistered`).

### IPersistentInteractable

```csharp
public interface IPersistentInteractable : IInteractable
{
    string PersistenceId { get; }
    InteractableDto CaptureState();
    void RestoreState(InteractableDto dto);
}
```

Contract:
- `PersistenceId` is designer-assigned, stable, unique per scene. Never reused after deprecation.
- `CaptureState` returns a concrete subclass of `InteractableDto` (e.g., `DoorDto`); the registry stores the JSON-serialized form in `InteractableEntry.stateJson` keyed by `PersistenceId`.
- `RestoreState` receives the same concrete subclass after the registry deserializes the envelope.

### InteractableRegistry

```csharp
using System.Collections.Generic;
using UnityEngine;

public class InteractableRegistry : MonoBehaviour, ISaveable<WorldObjectsDto>
{
    public string SaveKey => "worldObjects";

    public IReadOnlyCollection<IPersistentInteractable> All { get; }

    public void Register(IPersistentInteractable obj);
    public void Unregister(string id);

    public WorldObjectsDto CaptureState();
    public void RestoreState(WorldObjectsDto dto);
}
```

Contract:
- Each `IPersistentInteractable` calls `Register` in its `OnEnable` and `Unregister(PersistenceId)` in `OnDisable`. Symmetric.
- `PersistenceId` collisions throw on `Register` — uniqueness per scene is a hard invariant.
- `CaptureState` walks `All`, serializes each interactable's `InteractableDto` via `JsonUtility.ToJson`, and emits one `InteractableEntry` per id.
- `RestoreState` matches entries to currently-registered interactables by `PersistenceId`; missing ids log a warning and are skipped (deleted interactable in a newer scene version).
- `SaveSystem` delegates world-object capture to this registry directly via `ISaveable<WorldObjectsDto>`.

ADR-0002 split: container with one piece of behavior (the JSON envelope walk). Borderline. Default: keep as a single MonoBehaviour. If the envelope logic grows (multi-format, conflict resolution), promote to `InteractableRegistryLogic` per ADR-0002.

## Terminals

Wall-mounted PC consoles. Diegetic surface for the ship AI live channel and the per-terminal inbox of scripted AI messages (`SYS-TERMINAL`, ADR-0006). Peer of `PanelInteractable`; both implement `IInteractable`. `TerminalInteractable` does not extend `PanelInteractable`.

### TerminalInteractable

```csharp
using UnityEngine;

public class TerminalInteractable : MonoBehaviour, IInteractable
{
    [SerializeField] private string _terminalId;
    [SerializeField] private TerminalSystem _terminalSystem;

    public string TerminalId => _terminalId;

    public string Prompt => "Use terminal";
    public bool CanInteract { get; }
    public void Interact(PlayerController player);
}
```

Contract:
- `_terminalId` is designer-set, stable per scene, unique. Used as the routing key for `EVT-dialogue-response-ready` and `EVT-ai-message-delivered`.
- `CanInteract` returns `true` only when `_terminalSystem` is not currently displaying another terminal (single-open invariant in `SYS-TERMINAL`).
- `Interact(player)` forwards the request via `_terminalSystem.Open(this)`. The terminal does not own its open/close state — that is `TerminalSystem`'s job.

ADR-0002 split: exempt — no formula, just forwards a call.

### TerminalSystem

Composed by `GameLifetimeScope` (ADR-0009 §DI; reviewer rule `GAMEPLAY-CODE-DI-LIFETIMESCOPE-ONLY-AT-ROOT`).

```csharp
using System;
using UnityEngine;
using VContainer;

public class TerminalSystem : MonoBehaviour
{
    // Inspector-bound prefab reference (the chat UI Canvas the scope itself instantiates).
    // [SerializeField] is allowed for prefab refs per ADR-0009.
    [SerializeField] private TerminalChatView _chatView;

    // Cross-system runtime references resolved by VContainer.
    [Inject] private DialogueSystem _dialogueSystem;
    [Inject] private GameManager _gameManager;

    public event Action<string> OnTerminalOpened;
    public event Action<string> OnTerminalClosed;

    public TerminalInteractable ActiveTerminal { get; private set; }

    public void Open(TerminalInteractable terminal);
    public void Close();
    public int GetUnreadCount(string terminalId);

    private void OnEnable();
    private void OnDisable();
    private void HandleDialogueResponseReady(string terminalId, string speech, string[] tags);
    private void HandleAiMessageDelivered(string terminalId, string messageId);
}
```

Contract:
- `Open(terminal)` is a no-op when `ActiveTerminal != null` (single-open invariant; no event fires for the dropped request). Also a no-op when `_gameManager.CurrentState != GameState.Playing` (gate per SDD `§TerminalSystem` and ADR-0005 `SAVE-NO-EVENTS-DURING-LOADING`).
- On a successful `Open`: suppresses `PlayerController` movement and interaction input, binds the chat UI to `terminal._terminalId`, sets `ActiveTerminal`, and publishes `OnTerminalOpened(terminalId)` exactly once.
- `Close()` is a no-op when `ActiveTerminal == null`. On a successful close: restores `PlayerController` input, clears `ActiveTerminal`, and publishes `OnTerminalClosed(terminalId)` exactly once.
- `GetUnreadCount(terminalId)` reads the in-memory inbox view materialized from `_dialogueSystem`'s state (sourced from `DialogueDto.inbox`). Used by HUD/glow effects on each terminal.
- Subscribes in `OnEnable` to `_dialogueSystem.OnDialogueResponseReady` and `_dialogueSystem.OnAiMessageDelivered`; unsubscribes symmetrically in `OnDisable`.
- `HandleDialogueResponseReady` renders the speech into the chat UI when `terminalId == ActiveTerminal?.TerminalId`. Responses addressed to other terminals are ignored by this surface (still routed by `SYS-DIALOGUE`).
- `HandleAiMessageDelivered` increments the local unread badge for the addressed `terminalId`.
- Inbox truth lives in `DialogueDto.inbox`. `TerminalSystem` holds only a local view. **`TerminalSystem` is NOT `ISaveable<T>`.**

ADR-0002 split: exempt — UI lifecycle and input suppression, no formula. EditMode tests target the open/close gating and the dispatch filter via the publicly observable events; no plain-C# helper is needed.

### Terminal chat UI components

Per `SPEC-2026-05-12-ship-ai-context-and-runtime` decision 5, the chat surface is built in **uGUI + TextMeshPro**, fully custom. No third-party Asset Store package, no UI Toolkit migration. One Canvas prefab + four MonoBehaviours + one indicator. ~200 LOC total. All ADR-0002-exempt (UI lifecycle, no formula content).

`TerminalSystem` gains one new `[SerializeField] private TerminalChatView _chatView` (already shown in the class body above — prefab ref, allowed per ADR-0009) and forwards open/close calls to it. No change to `TerminalSystem`'s public API or to `EVT-terminal-opened` / `EVT-terminal-closed`.

#### TerminalChatPanel.prefab

Canvas prefab. The terminal screen shown when a `TerminalInteractable` is opened. World-space or overlay (Unity-specialist decides at implementation time; both viable). Owns:
- One `ChatHistoryView` instance (scrollable transcript).
- One `ChatInputField` instance (text entry + Send button).
- One `AvailabilityIndicator` instance (status line).
- A monospace TMP font reference (CRT diegetic aesthetic).

#### ChatEntry.prefab (×3 variants)

Prefab variants for chat-history rows, one per role:
- `player` — the player's typed line.
- `ship-ai-online` — a normal ship-AI reply.
- `ship-ai-garbled` — a `Garbled`-state reply rendered with TMP rich-text glitch tags / random char substitution.

Variant keys use the canonical `ship-ai` prefix (per glossary `ship AI`), not the persona name `MOTHER`. Each variant holds a single `TMP_Text` inside.

#### TerminalChatView

```csharp
using UnityEngine;

public class TerminalChatView : MonoBehaviour
{
    [SerializeField] private ChatHistoryView _history;
    [SerializeField] private ChatInputField _input;
    [SerializeField] private AvailabilityIndicator _indicator;

    public void Open(string terminalId);
    public void Close();
    public void RenderResponse(string speech, string[] tags);
}
```

The view layer for `TerminalSystem`. Subscribes to `_dialogueSystem.OnDialogueResponseReady` filtered by `terminalId == _activeTerminalId`. Decides which `ChatEntry` variant to instantiate based on `tags`: `silent` → no entry, only the indicator pulses "NO RESPONSE" briefly; `nonsequitur` + `false-claim` → `ship-ai-garbled` variant; otherwise → `ship-ai-online` variant.

#### ChatHistoryView

`ScrollRect` + `VerticalLayoutGroup` of `ChatEntry` instances. `AddEntry(ChatEntry.prefab variant, string text)` appends and auto-scrolls to bottom. Bounded by `DialogueAIConfig.maxHistoryDepth` for visible entries (older entries drop off the top; the canonical history truth lives in `DialogueDto.exchanges`).

#### ChatInputField

```csharp
using UnityEngine;

public class ChatInputField : MonoBehaviour
{
    public event System.Action<string> OnSubmit;

    public void SetEnabled(bool enabled);
    public void Focus();
    public void Clear();
}
```

Wraps `TMP_InputField` + Send button + Enter key binding. Disabled (`SetEnabled(false)`) while a turn is in flight or while the current `AvailabilityState` is `Silent` (the player can read history but cannot submit a turn that nothing will respond to).

#### AvailabilityIndicator

Small status line bound to the current `AvailabilityState`:
- `Online` → "ONLINE" (subtle, low-contrast).
- `Garbled` → "DEGRADED" (animated, colored).
- `Silent` → "NO SIGNAL" (static, no glitch).

Reads the state by querying `DialogueLogic.EvaluateAvailability` indirectly through `DialogueSystem` (a `public AvailabilityState GetAvailability(...)` accessor on `DialogueSystem` exposes it without leaking the rule list). Polled on `EVT-zone-changed`, `EVT-flag-changed`, and on every turn boundary.

## Dialogue

Ship AI live channel + scripted inbox routing (`SYS-DIALOGUE`, ADR-0006, ADR-0002, ADR-0005). Owns AI internal state (`mandate`, `integrity`, `budget`). `DialogueSystem` is the MonoBehaviour adapter; the formula-bearing path is `DialogueLogic` (plain C# per ADR-0002).

### DialogueCueDefinition

```csharp
using UnityEngine;

[CreateAssetMenu(menuName = "LastBreath/Dialogue/Cue")]
public class DialogueCueDefinition : ScriptableObject
{
    public string cueId;
    public FlagDefinition[] requiredFlags;
    public string targetTerminalId;
    public string messageId;
    public string body;
    public bool oneShot;
}
```

One asset per inbox cue. Identity-only SO; no runtime mutation (ADR-0004). Registered as `CFG-DIALOGUE-CUE`. Consumed only by `SYS-DIALOGUE`; separate from `NarrativeCueDefinition` (`CFG-NARRATIVE-CUE`) by deliberate decomposition (SDD `§DialogueSystem → Decision`).

Fields:
- `cueId` — stable identity, used in diagnostics.
- `requiredFlags` — all `FlagDefinition`s must resolve to `true` in `FlagSystem` for the cue to fire.
- `targetTerminalId` — routing key; matches a `TerminalInteractable._terminalId`.
- `messageId` — stable id used in inbox de-duplication. The `(messageId, targetTerminalId)` pair is the inbox primary key.
- `body` — the AI's pre-scripted message text.
- `oneShot` — if `true`, the cue is never re-evaluated after its first delivery per save.

### MotherAvailabilityRule

```csharp
using UnityEngine;

public enum AvailabilityState { Online, Garbled, Silent }

[CreateAssetMenu(menuName = "LastBreath/Dialogue/Availability Rule")]
public class MotherAvailabilityRule : ScriptableObject
{
    public string ruleId;                   // stable id for diagnostics
    public string zone;                     // empty = any zone
    public FlagDefinition[] requiredFlags;  // all true ⇒ rule may apply
    public FlagDefinition[] forbiddenFlags; // all false ⇒ rule may apply
    public AvailabilityState state;
    public int priority;                    // higher wins; ties resolved by file order
}
```

One asset per rule. Identity-only SO per ADR-0004: no `_runtimeValue`, no `OnEnable`-resets pattern; values are read at `Awake` and never mutated at runtime. Registered as `CFG-AVAILABILITY-RULE`. Consumed by `DialogueLogic.EvaluateAvailability(...)`.

Fields:
- `ruleId` — stable identity for diagnostics and tie-detection logging.
- `zone` — match scope. Empty string = applies to any zone. Otherwise matches `DialogueContext.zone` exactly.
- `requiredFlags` — every `FlagDefinition` listed must resolve to `true` in `FlagSystem` for the rule to apply.
- `forbiddenFlags` — every `FlagDefinition` listed must resolve to `false`.
- `state` — the `AvailabilityState` returned when this rule matches (`Online` lets the player chat normally; `Garbled` sends a canned reply with `["nonsequitur","false-claim"]` and ticks `integrity` down; `Silent` sends an empty-speech reply with `["silent"]` and does not touch `integrity`).
- `priority` — integer, higher wins. Ties on equal priority resolve to the rule earlier in the input list (deterministic file order). `DialogueSystem.Awake` logs a warning when ties are detected so designers can fix authoring.

The default `Online` is implicit: when no rule matches, `EvaluateAvailability` returns `Online`. Designers do **not** need to author an explicit `Online` rule for the common case; rules are added only to introduce `Garbled` or `Silent` zones / states.

Separate-asset (one rule per file) chosen over nested-array-on-`DialogueAIConfig` to mirror the `DialogueCueDefinition` authoring pattern.

### DialogueAIConfig

```csharp
using UnityEngine;

[CreateAssetMenu(menuName = "LastBreath/Dialogue/AI Config")]
public class DialogueAIConfig : ScriptableObject
{
    public string personaName = "MOTHER";
    [TextArea(8, 32)] public string systemPrompt;
    public int maxHistoryDepth = 5;
    public string[] offlineFallbackReplies;
    public AnimationCurve[] degradationCurves;

    public MotherAvailabilityRule[] availabilityRules;  // designer-authored zone/flag gates
    public string[] garbledReplies;                     // canned pool for Garbled state
}
```

Registered as `CFG-DIALOGUE-AI`. Identity/tuning only; no runtime mutation (ADR-0004). Fields:
- `personaName` — default `"MOTHER"`; surfaced in HUD attribution.
- `systemPrompt` — long persona block fed to the model on every turn (format rules, role, register). Required sections (per `SPEC-2026-05-12-ship-ai-context-and-runtime`): identity, register, three-axes interpretation, withholding rules, format spec, never-do block.
- `maxHistoryDepth` — last N exchanges fed back to the model (default `5`). Bounds prompt size and `DialogueDto.exchanges` length.
- `offlineFallbackReplies` — pool of canned replies used when the transport returns `Timeout` / `NetworkError` / `Malformed`. Picking strategy is `DialogueLogic`-internal.
- `degradationCurves` — designer-tunable curves for `mandate` / `integrity` / `budget` updates per turn. `AnimationCurve` chosen for inspector tunability; consumed by `DialogueLogic`.
- `availabilityRules` — designer-authored list of `MotherAvailabilityRule` SOs. Empty array = ship AI is always `Online`. Evaluated by `DialogueLogic.EvaluateAvailability` before every turn.
- `garbledReplies` — canned pool consumed when `EvaluateAvailability` returns `Garbled`. Selection is deterministic: `index = turnCount % garbledReplies.Length`. Same canned reply replays on save/restore for the same turn (per ADR-0006 amendment 2026-05-12).

### LlmTransportConfig

```csharp
using UnityEngine;

[CreateAssetMenu(menuName = "LastBreath/Dialogue/Transport Config")]
public class LlmTransportConfig : ScriptableObject
{
    public string defaultEndpoint = "http://localhost:11434";
    public string modelName = "hermes3:8b-llama3.1-q4_K_M";
    public float timeoutSecondsP95 = 4.0f;
}
```

Registered as `CFG-LLM-TRANSPORT`. Endpoint URL only — **never** holds an API key, token, or any secret (ADR-0006). The resolved endpoint at runtime is `env LASTBREATH_LLM_ENDPOINT` > `defaultEndpoint` > hardcoded `http://localhost:11434`.

**Model pick** (per `SPEC-2026-05-12-ship-ai-context-and-runtime`, target hardware 16–24 GB VRAM):
- **Primary:** `hermes3:8b-llama3.1-q4_K_M`. Nous Research fine-tune of Llama 3.1 8B for function-calling / structured output. ~5 GB Q4. Latency ~0.7–1.2s/turn for ~200 tokens. Weak safety alignment fits MOTHER's character.
- **Documented fallback:** `qwen2.5:14b-instruct-q4_K_M`. ~9 GB Q4, latency 1.5–2.0s/turn. Switch by changing `modelName` only.

**`format: "json"` is hard-coded in `OllamaHttpTransport` and is NOT exposed on this config.** Designers cannot disable JSON mode; removing it requires an ADR amendment.

### IDialogueTransport

Declared once. The only seam between `SYS-DIALOGUE` and the outside world (ADR-0006).

```csharp
using System.Threading;
using UnityEngine;

public interface IDialogueTransport
{
    // Transport boundary — Task is intentional here (ADR-0006 §Decision item 1;
    // ADR-0009 §Async runtime; rule GAMEPLAY-CODE-PREFER-UNITASK §Allowed patterns).
    // Callers inside _Project/ adapt via .AsUniTask() at the use site.
    Task<TransportResponse> SendAsync(string prompt, CancellationToken ct);
}

public readonly struct TransportResponse
{
    public readonly string Body;
    public readonly TransportStatus Status;
    public TransportResponse(string body, TransportStatus status) { Body = body; Status = status; }
}

public enum TransportStatus { Ok, Timeout, NetworkError, Malformed }
```

Contract:
- One method. No streaming, no per-turn options. Model name, temperature, system prompt are baked into the implementation (constructor) or its bound `LlmTransportConfig`.
- `SendAsync` never throws across the seam: transport exceptions map to `TransportStatus.NetworkError`; HTTP timeout maps to `Timeout`; unparseable body maps to `Malformed`.
- No class outside `SYS-DIALOGUE` calls `SendAsync` directly (reviewer rule `GAMEPLAY-CODE-DIALOGUE-NO-DIRECT-LLM`).

### OllamaHttpTransport

```csharp
using System.Threading;
using UnityEngine;

public class OllamaHttpTransport : IDialogueTransport
{
    public OllamaHttpTransport(LlmTransportConfig config);

    public Task<TransportResponse> SendAsync(string prompt, CancellationToken ct);
}
```

Contract:
- Constructor resolves the endpoint per ADR-0006: env `LASTBREATH_LLM_ENDPOINT` > `config.defaultEndpoint` > hardcoded `http://localhost:11434`.
- `SendAsync` POSTs JSON to the Ollama-compatible chat endpoint, awaits the response within `config.timeoutSecondsP95`, and returns a `TransportResponse`.
- Status mapping: success body parsed to `Ok`; cancellation or timer-elapsed to `Timeout`; any thrown `Exception` to `NetworkError`; parsing failure to `Malformed`.
- Implementation is deferred (PLAN-005 is doc-only). The signature is declared here so reviewer rules can cite the contract.

### MockTransport

```csharp
using System.Collections.Generic;
using System.Threading;
using UnityEngine;

public class MockTransport : IDialogueTransport
{
    public MockTransport(List<MockTurn> turns);

    public Task<TransportResponse> SendAsync(string prompt, CancellationToken ct);
}

[System.Serializable]
public class MockTurn
{
    public string matchPrefix;
    public string body;
    public TransportStatus status;
}
```

Contract:
- `SendAsync` returns the first `MockTurn` whose `matchPrefix` is a prefix of `prompt`, packaged as a synchronously-completed `Task<TransportResponse>` (`Task.FromResult`).
- If no prefix matches, returns `TransportResponse { Body = "", Status = Malformed }`.
- EditMode-only / editor-time offline use. **Never** instantiated in builds (ADR-0006).

### DialogueContext

Flat carrier struct fed to the prompt builder. The **exact allowlist** of state visible to the model. Reviewer rule `GAMEPLAY-CODE-DIALOGUE-PROMPT-MUST-WITHHOLD` greps for this type to verify no field is sneaked in.

```csharp
using System.Collections.Generic;

public enum OxygenBucket { High, Medium, Low, Critical }
public enum AgitationBucket { Calm, Tense, Panic }

public enum RecentEventTag {
    ProtocolBreach,
    ZoneTransition,
    PresenceEvent,
    OxygenBucketDrop,
    AgitationSpike,
    ObjectiveAdvanced,
    ObjectiveBlocked,
    InboxIgnored,
    Idle
}

public enum RecentTagAge { JustNow, ThisTurn, EarlierThisRun }

public readonly struct RecentEvent
{
    public readonly RecentEventTag Tag;
    public readonly RecentTagAge Age;
    public RecentEvent(RecentEventTag tag, RecentTagAge age) { Tag = tag; Age = age; }
}

public readonly struct DialogueContext
{
    public readonly string zone;
    public readonly OxygenBucket oxygen;
    public readonly AgitationBucket agitation;
    public readonly string objectiveText;
    public readonly float mandate;
    public readonly float integrity;
    public readonly float budget;
    public readonly IReadOnlyList<DialogueExchange> recentExchanges;
    public readonly IReadOnlyList<RecentEvent> recentEvents;     // bounded 0..10, FIFO eviction
    public readonly string lastSignificantInteraction;           // nullable; from IFocusLabel.FocusLabel

    public DialogueContext(
        string zone,
        OxygenBucket oxygen,
        AgitationBucket agitation,
        string objectiveText,
        float mandate,
        float integrity,
        float budget,
        IReadOnlyList<DialogueExchange> recentExchanges,
        IReadOnlyList<RecentEvent> recentEvents,
        string lastSignificantInteraction);
}
```

**Withheld by design (must NOT be added):**
- No `Vector3 position` or any positional field.
- No exact oxygen percentage (only the bucket).
- No exact agitation value (only the bucket).
- No exact `mandate` / `integrity` / `budget` floats — these are bucketed at prompt-serialization time (`very-low | low | medium | high | very-high`); the floats stay in `DialogueContext` for `DialogueLogic` math but never enter the prompt body.
- No flag list, full or filtered.
- Exact presence cooldowns and per-firing timestamps are withheld; aggregated `RecentEventTag.PresenceEvent` entries with `RecentTagAge` buckets are part of the allowlist (per ADR-0006 amendment 2026-05-12).
- No prior-session history (`recentExchanges` is bounded by `DialogueAIConfig.maxHistoryDepth` within the current run; `recentEvents` is bounded to 10 entries with FIFO eviction).
- No raw flag IDs in `lastSignificantInteraction` — values come exclusively from `IFocusLabel.FocusLabel`, which designers author on opt-in interactables.

Reflection-based "send everything" is forbidden. The prompt builder reads each field by name, explicitly.

### IFocusLabel

```csharp
public interface IFocusLabel
{
    string FocusLabel { get; }
}
```

Opt-in interface implemented by `IInteractable`s that the ship AI is allowed to refer to by name (e.g., `OxygenStationInteractable`, the airlock interactable, `PanelInteractable` for `panel C-7`). The label is a `[SerializeField] string _focusLabel` on the implementing `MonoBehaviour`, designer-set in the inspector — identical in shape to the existing `_terminalId` precedent on `TerminalInteractable`.

Contract:
- Returns `null` when the interaction is trivial and the AI must not refer to it (default for `PickupInteractable`, generic loot, etc.).
- Returns a designer-curated string otherwise. Forbidden values: anything that resembles a flag ID, a registry ID, or an internal class name. Designer responsibility, enforced by the reviewer at PR time.
- `DialogueSystem` listens to `EVT-interaction-completed`, casts the source to `IFocusLabel`, and if non-null caches the returned label as the run's `lastSignificantInteraction`. The cached value persists across save/restore via `DialogueDto.lastSignificantInteraction`.
- Registered as `CLASS-IFocusLabel` under `SYS-DIALOGUE.classes`.

### DialogueResponse

Parsed structured response. Flat by design so `JsonUtility.FromJson` handles it (ADR-0006).

```csharp
using System;

[Serializable]
public class DialogueResponse
{
    public string speech;
    public float mandateDelta;
    public string[] tags;
}
```

Parsed via `JsonUtility.FromJson<DialogueResponse>(transportResponse.Body)`. `tags` is bounded to known strings (`refusal`, `policy`, `evasion`, `compliance`, `nonsequitur`, `warning`, `false-claim`, `silent`); unknown tags are dropped by `DialogueLogic`. A malformed body or missing required field falls back to a configured offline reply and ticks `integrity` down. The `silent` tag is reserved for synthesized empty-speech responses produced by the `Silent` availability branch (see `### MotherAvailabilityRule` and ADR-0006 amendment 2026-05-12); it never appears on real LLM output.

### DialogueLogic

Plain C# class per ADR-0002. **Not** a MonoBehaviour. This is the formula-bearing path of `SYS-DIALOGUE`; EditMode tests target this class.

```csharp
using System.Collections.Generic;
using System.Threading;
using UnityEngine;

public class DialogueLogic
{
    public DialogueLogic(
        DialogueAIConfig aiConfig,
        IDialogueTransport transport,
        DialogueDto initialState);

    public async UniTask<DialogueResponse> ProcessTurnAsync(
        string playerText,
        DialogueContext ctx,
        CancellationToken ct);

    public DialogueContext BuildContext(
        string zone,
        OxygenBucket oxygen,
        AgitationBucket agitation,
        string objectiveText,
        IReadOnlyList<RecentEvent> recentEvents,
        string lastSignificantInteraction);

    public (string systemPrompt, string userMessage) BuildPrompt(
        DialogueContext ctx,
        DialogueAIConfig cfg);

    public DialogueResponse ParseResponse(string body);

    public AvailabilityState EvaluateAvailability(
        DialogueContext ctx,
        IReadOnlyList<MotherAvailabilityRule> rules,
        IReadOnlyDictionary<FlagDefinition, bool> flagValues);

    public DialogueState SnapshotState();
    public void RestoreSnapshot(DialogueState state);

    public IReadOnlyList<DialogueCueDefinition> EvaluatePendingInbox(
        IReadOnlyDictionary<FlagDefinition, bool> flagValues,
        IEnumerable<DialogueCueDefinition> allCues,
        ISet<string> alreadyDelivered);
}

public class DialogueState
{
    public List<DialogueExchange> exchanges;
    public float mandate;
    public float integrity;
    public float budget;
    public int turnCount;
    public List<RecentEvent> recentEvents;
    public string lastSignificantInteraction;
}
```

Contract:
- Constructor rehydrates internal state from `initialState` (empty DTO acceptable for fresh runs). Holds the `IDialogueTransport` reference for the lifetime of the logic instance.
- `ProcessTurnAsync(playerText, ctx, ct)`:
  1. Builds the prompt from `aiConfig.systemPrompt`, `ctx` (allowlisted fields only), and `ctx.recentExchanges` bounded by `aiConfig.maxHistoryDepth`.
  2. Calls `_transport.SendAsync(prompt, ct)`.
  3. On `Ok`: parses `TransportResponse.Body` into a `DialogueResponse` via `JsonUtility.FromJson`. On parse failure, treat as `Malformed`.
  4. On `Timeout` / `NetworkError` / `Malformed`: picks a reply from `aiConfig.offlineFallbackReplies`, sets `mandateDelta = 0`, sets `tags = ["false-claim"]`, ticks `integrity` down per `aiConfig.degradationCurves` ("failure looks like AI degradation" — ADR-0006).
  5. Applies internal state updates (`mandate += response.mandateDelta`; integrity/budget per curves). Appends a `DialogueExchange` to history (trimmed to `maxHistoryDepth`). Increments `turnCount`.
  6. Returns the `DialogueResponse`.
- `BuildContext(...)` is public so the reviewer can grep this method and verify the allowlist is consulted explicitly. **No reflection.** Every field of `DialogueContext` is set by name.
- `BuildPrompt(ctx, cfg)` is public for the same reason: the reviewer greps both `BuildContext` and `BuildPrompt` to confirm exhaustive use of the allowlist. Returns the literal system prompt from `cfg.systemPrompt` (no interpolation, designer authors verbatim) and a compact key:value `userMessage` block: `state` (with `mandate`/`integrity`/`budget` bucketed via half-open intervals `[0.0, 0.15) / [0.15, 0.3) / [0.3, 0.7) / [0.7, 0.85) / [0.85, 1.0]` to `very-low|low|medium|high|very-high`), `recent` CSV of `recentEvents`, optional `last_focus`, optional `history` of up to `cfg.maxHistoryDepth` exchanges with assistant entries serialized as `speech` only.
- `ParseResponse(body)` is public. Pulls `.message.content` from the Ollama wrapper, deserializes via `JsonUtility.FromJson<DialogueResponse>`, validates `speech` non-empty, clamps `mandateDelta ∈ [-0.2, 0.2]`, filters `tags` to the allowed enum subset (the `silent` tag is rejected here — it is only allowed on synthesized responses, never on parsed LLM output). Failure → returns `null`; caller treats as `TransportStatus.Malformed`.
- `EvaluateAvailability(ctx, rules, flagValues)` walks `rules` in descending `priority`. Skips a rule if `zone != ""` and `zone != ctx.zone`; skips if any `requiredFlag` is `false` in `flagValues`; skips if any `forbiddenFlag` is `true`. First match wins. No match → returns `Online`. Tie-break on equal priority: rule earlier in the input list wins (deterministic file order); a startup helper logs a warning when ties are detected so designers fix the priority. EditMode-testable; no Unity types in the signature.
- `SnapshotState()` / `RestoreSnapshot(state)` are the capture/restore hooks called by `DialogueSystem` for DTO round-trip. `RestoreSnapshot` writes fields directly; it **does not** invoke the transport. `recentEvents` are restored with all `Age` values demoted to `EarlierThisRun` regardless of the stored value (per ADR-0006 amendment 2026-05-12 — preserves SDD `§SaveSystem.Acceptance` "observationally equal to capture" without lying about wall-clock time).
- `EvaluatePendingInbox(flagValues, allCues, alreadyDelivered)` walks `allCues`, returns those whose `requiredFlags` are all `true` in `flagValues` and whose `messageId` is not in `alreadyDelivered`. `oneShot` cues already in `alreadyDelivered` are skipped permanently.

Determinism: given the same `DialogueContext` and the same `TransportResponse`, `DialogueLogic` is deterministic. Tests pair it with `MockTransport` to exercise success, timeout, and malformed paths.

### DialogueSystem

MonoBehaviour adapter (ADR-0002). Owns the `DialogueLogic` instance, the `IDialogueTransport` implementation, and the per-terminal inbox state. Implements `ISaveable<DialogueDto>` (ADR-0005). Composed by `GameLifetimeScope` (ADR-0009 §DI; reviewer rule `GAMEPLAY-CODE-DI-LIFETIMESCOPE-ONLY-AT-ROOT`).

```csharp
using System;
using System.Collections.Generic;
using System.Threading;
using UnityEngine;
using VContainer;

public class DialogueSystem : MonoBehaviour, ISaveable<DialogueDto>
{
    // Inspector-bound configs (CFG-* SOs and SO lists). [SerializeField] is allowed
    // here per ADR-0009: configs are designer-authored data, not runtime system refs.
    [SerializeField] private DialogueAIConfig _aiConfig;
    [SerializeField] private LlmTransportConfig _transportConfig;
    [SerializeField] private List<DialogueCueDefinition> _allCues;
    [SerializeField] private List<MotherAvailabilityRule> _availabilityRules;

    // Cross-system runtime references resolved by VContainer (ADR-0009 §DI).
    // Never [SerializeField] for these; the LifetimeScope wires them.
    [Inject] private FlagSystem _flagSystem;
    [Inject] private GameManager _gameManager;
    [Inject] private OxygenSystem _oxygenSystem;
    [Inject] private AgitationSystem _agitationSystem;
    [Inject] private EnvironmentSystem _environmentSystem;
    [Inject] private ObjectiveSystem _objectiveSystem;
    [Inject] private PlayerInteractor _interactor;

    public event Action<string, string, string[]> OnDialogueResponseReady;
    public event Action<string, string> OnAiMessageDelivered;

    public string SaveKey => "dialogue";

    public async UniTask<DialogueResponse> SubmitTurnAsync(
        string playerText,
        string activeTerminalId);

    public IReadOnlyList<InboxEntry> GetInbox(string terminalId);

    public DialogueDto CaptureState();
    public void RestoreState(DialogueDto dto);

    private void Awake();
    private void OnEnable();
    private void OnDisable();
    private void HandleFlagChanged(FlagDefinition flag, bool value);
    private void HandleInteractionCompleted(string interactableId, IInteractable source);
}
```

Contract:
- `Awake` constructs the transport (`OllamaHttpTransport` from `_transportConfig` by default) and `DialogueLogic` (passing `_aiConfig`, the transport, and an empty `DialogueDto` for a fresh run). Restore from save overrides this state via `RestoreState`.
- Subscribes in `OnEnable` to `_flagSystem.OnFlagChanged` and to `_interactor.OnInteractionCompleted` (`EVT-interaction-completed`); unsubscribes symmetrically in `OnDisable`. The interaction subscription drives two things: (a) caches the latest non-null `IFocusLabel.FocusLabel` as the run's `lastSignificantInteraction`; (b) appends a `RecentEvent(ProtocolBreach, JustNow)` to the in-memory queue when the source's `IFocusLabel` (or a separate protocol-breach predicate) marks the interaction as breaching.
- The in-memory `Queue<RecentEvent>` is kept by `DialogueSystem` and fed by all the existing subscriptions (`EVT-zone-changed`, `EVT-oxygen-changed`, `EVT-agitation-changed`, `EVT-presence-event-fired`, `EVT-flag-changed`) plus the new `EVT-interaction-completed`. Eviction policy: FIFO when the queue exceeds 10. Consecutive duplicates of the same `Tag` collapse into a single entry holding the most recent `Age`. The mapping from each upstream event to a `RecentEventTag` value is implementation-deferred — see `## Out of scope` in `SPEC-2026-05-12-ship-ai-context-and-runtime`.
- `SubmitTurnAsync(playerText, activeTerminalId)` is invoked directly by `TerminalSystem` (not via event). Behavior:
  1. If `_gameManager.CurrentState != GameState.Playing`, returns a `DialogueResponse` with the configured offline fallback and does **not** publish `OnDialogueResponseReady`.
  2. Builds the `DialogueContext` by reading buckets from `_oxygenSystem`, `_agitationSystem`, `_environmentSystem`, and the current objective text from `_objectiveSystem`, plus the in-memory `recentEvents` snapshot and the cached `lastSignificantInteraction`. Bucket mapping is a private helper (`OxygenBucket` / `AgitationBucket`); the exact value is never copied across.
  3. Calls `_dialogueLogic.EvaluateAvailability(ctx, _availabilityRules, _flagSystem.GetSnapshot())` to decide the branch:
     - **`Online`** → `_dialogueLogic.ProcessTurnAsync(playerText, ctx, destroyCancellationToken)` (existing flow).
     - **`Garbled`** → no transport call. Picks `_aiConfig.garbledReplies[turnCount % _aiConfig.garbledReplies.Length]` (deterministic round-robin), synthesizes a `DialogueResponse` with `tags=["nonsequitur","false-claim"]`, ticks `integrity` down per the configured curve, increments `turnCount`, appends a `DialogueExchange` to history.
     - **`Silent`** → no transport call. Synthesizes an empty-speech `DialogueResponse` with `tags=["silent"]`, **does not** touch `integrity`, increments `turnCount`, appends a `DialogueExchange` (with empty `aiSpeech`) to history so the player line and silence marker survive in the save.
  4. If, on completion, `_gameManager.CurrentState == GameState.Playing`, publishes `OnDialogueResponseReady(activeTerminalId, response.speech, response.tags)` exactly once. (Both `Garbled` and `Silent` branches still publish the event so the UI can render the appropriate state.)
  5. Returns the response.
- `HandleFlagChanged(flag, value)`:
  - If `_gameManager.CurrentState != GameState.Playing`, returns immediately. No event published during `GameState.Loading` (ADR-0005 `SAVE-NO-EVENTS-DURING-LOADING`).
  - Otherwise, calls `_dialogueLogic.EvaluatePendingInbox(flagValues, _allCues, alreadyDelivered)`. For each returned `DialogueCueDefinition`, appends an `InboxEntry` to `DialogueDto.inbox` and publishes `OnAiMessageDelivered(cue.targetTerminalId, cue.messageId)`. One event per cue.
- `GetInbox(terminalId)` exposes the per-terminal inbox slice for `TerminalSystem` to materialize its view.
- `CaptureState()` returns a fresh `DialogueDto` populated from `_dialogueLogic.SnapshotState()` plus the current `inbox` list. No transport configuration is captured (reviewer rule `GAMEPLAY-CODE-DIALOGUE-NO-SECRETS-IN-SAVE`).
- `RestoreState(dto)` writes fields directly via `_dialogueLogic.RestoreSnapshot(...)`, repopulates the `inbox` list, **without invoking the transport** and **without firing `OnDialogueResponseReady` or `OnAiMessageDelivered`** (silent restore per ADR-0005 `SAVE-NO-EVENTS-DURING-LOADING`).
- `IDialogueTransport.SendAsync` is never called from `RestoreState` or while `GameState.Loading`. Saved exchanges are the canonical truth (ADR-0006).

ADR-0002 split: this is the MonoBehaviour adapter; the formula path is in `DialogueLogic`. EditMode tests pair `DialogueLogic` with `MockTransport`; PlayMode smoke verifies the event payloads on `SubmitTurnAsync` and `HandleFlagChanged`.

### DialogueDto

Saved snapshot. Plain `[Serializable]` class with primitive / nested-serializable fields only. Stored as `SaveData.dialogue` (see `§Save → SaveData`).

```csharp
using System;
using System.Collections.Generic;

[Serializable]
public class DialogueDto
{
    public List<DialogueExchange> exchanges;
    public List<InboxEntry> inbox;
    public float mandate;
    public float integrity;
    public float budget;
    public int turnCount;
    public List<RecentEventDto> recentEvents;          // capped at 10; FIFO eviction at capture time
    public string lastSignificantInteraction;          // nullable; from IFocusLabel.FocusLabel
}

[Serializable]
public class RecentEventDto
{
    public RecentEventTag tag;
    public RecentTagAge age;
}

[Serializable]
public class DialogueExchange
{
    public string playerText;
    public string aiSpeech;
    public string[] aiTags;
    public int turnIndex;
}

[Serializable]
public class InboxEntry
{
    public string terminalId;
    public string messageId;
    public string body;
    public bool isRead;
}
```

Notes on shape:
- `exchanges` is bounded by `DialogueAIConfig.maxHistoryDepth`. Older exchanges are dropped at capture time, not restore time.
- `inbox` is the canonical truth for per-terminal messages. `TerminalSystem` derives its unread counts from `inbox.Where(e => e.terminalId == id && !e.isRead).Count()`.
- `mandate`, `integrity`, `budget` are AI internal state. They are saved but **never** exposed in any published event payload (SDD `§DialogueSystem` invariant). The HUD does not subscribe to them.
- Endpoint URLs, model names, tokens, and any transport configuration are **deliberately absent**. Reviewer rule `GAMEPLAY-CODE-DIALOGUE-NO-SECRETS-IN-SAVE` enforces this.
- Restored silently per `SAVE-NO-EVENTS-DURING-LOADING`. The transport is never invoked during restore (ADR-0006).
- `recentEvents` is restored with all `age` fields demoted to `EarlierThisRun` regardless of the stored value. The tags survive (so the ship AI's awareness of run history is preserved); only the temporal label is normalized. After several save/restore cycles, the stable shape is "tail of up to 10 events, all `EarlierThisRun`." See ADR-0006 amendment 2026-05-12.
- `lastSignificantInteraction` is a designer-curated string (sourced exclusively through `IFocusLabel.FocusLabel`); never a flag ID, never a registry ID. Reviewer responsibility at PR time.

## Minimum HUD

### HudController

Responsibilities:
- Update the oxygen bar.
- Show the prompt.
- Show failure/success state.

```csharp
using UnityEngine;
using UnityEngine.UI;

public class HudController : MonoBehaviour
{
    [SerializeField] private OxygenSystem oxygenSystem;
    [SerializeField] private Image oxygenFill;

    private void OnEnable()
    {
        oxygenSystem.OnOxygenChanged += HandleOxygenChanged;
    }

    private void OnDisable()
    {
        oxygenSystem.OnOxygenChanged -= HandleOxygenChanged;
    }

    private void HandleOxygenChanged(float normalizedValue)
    {
        oxygenFill.fillAmount = normalizedValue;
    }
}
```

### DebugOverlay

Overlay for development only. Must be toggleable with `debugMode`.

Data to display:
- Numeric oxygen.
- Numeric agitation.
- Current zone.
- Current objective.
- Last `presenceEventId`.
- Global game state.

```csharp
using UnityEngine;
using UnityEngine.UI;

public class DebugOverlay : MonoBehaviour
{
    [SerializeField] private bool debugMode = true;
    [SerializeField] private Text debugText;
    [SerializeField] private GameManager gameManager;
    [SerializeField] private OxygenSystem oxygenSystem;
    [SerializeField] private AgitationSystem agitationSystem;
    [SerializeField] private EnvironmentSystem environmentSystem;
    [SerializeField] private ObjectiveSystem objectiveSystem;
    [SerializeField] private PresenceDirector presenceDirector;

    private void Update()
    {
        debugText.gameObject.SetActive(debugMode);

        if (!debugMode)
            return;

        debugText.text =
            $"State: {gameManager.CurrentState}\n" +
            $"O2: {oxygenSystem.CurrentOxygen:0.0}\n" +
            $"Agitation: {agitationSystem.CurrentAgitation:0.0}\n" +
            $"Zone: {environmentSystem.CurrentZone}\n" +
            $"Objective: {objectiveSystem.CurrentObjectiveId}\n" +
            $"Last Presence: {presenceDirector.LastEventId}";
    }
}
```

## Update Flow

### Per frame

Conceptual order:

1. `PlayerController.Update`
   - Read input.
   - Move player.
   - Update `PlayerState.IsRunning`.

2. `AgitationSystem.Update`
   - Read `PlayerState`.
   - Raise/lower agitation.
   - Update `OxygenMultiplier`.

3. `OxygenSystem.Update`
   - Read agitation multiplier.
   - Read environment multiplier.
   - Subtract oxygen.
   - Notify HUD.
   - If it reaches zero, call `GameManager.FailRun()`.

4. `PlayerInteractor.Update`
   - If the player presses `E`, run the current interaction.

### Oxygen formula

```text
drainPerSecond =
    baseDrainPerSecond
    * agitationMultiplier
    * environmentMultiplier

oxygen -= drainPerSecond * Time.deltaTime
```

Example:

```text
Interior + normal:
0.4 * 1.0 * 1.0 = 0.4 per second

Interior + agitated:
0.4 * 1.8 * 1.0 = 0.72 per second

Exterior + agitated:
0.4 * 1.8 * 1.5 = 1.08 per second
```

## Prefab Organization

### GameLifetimeScope (VContainer composition root)

A single in-scene GameObject hosts a `LifetimeScope` subclass per ADR-0009 §DI:

```csharp
using VContainer;
using VContainer.Unity;
using UnityEngine;

public class GameLifetimeScope : LifetimeScope
{
    [SerializeField] private OxygenConfig _oxygenConfig;
    [SerializeField] private AgitationConfig _agitationConfig;
    [SerializeField] private LlmTransportConfig _llmTransportConfig;
    [SerializeField] private DialogueAIConfig _dialogueAiConfig;
    // ScriptableObject and prefab-bound configs ↑. No cross-system [SerializeField] refs.

    protected override void Configure(IContainerBuilder builder)
    {
        // ScriptableObject configs
        builder.RegisterInstance(_oxygenConfig);
        builder.RegisterInstance(_agitationConfig);
        builder.RegisterInstance(_llmTransportConfig);
        builder.RegisterInstance(_dialogueAiConfig);

        // Core systems — all MonoBehaviour, found in scene and registered via ComponentInScene
        builder.RegisterComponentInHierarchy<GameManager>();
        builder.RegisterComponentInHierarchy<OxygenSystem>();
        builder.RegisterComponentInHierarchy<AgitationSystem>();
        builder.RegisterComponentInHierarchy<EnvironmentSystem>();
        builder.RegisterComponentInHierarchy<PresenceDirector>();
        builder.RegisterComponentInHierarchy<ObjectiveSystem>();
        builder.RegisterComponentInHierarchy<HudController>();
        builder.RegisterComponentInHierarchy<DebugOverlay>();
        builder.RegisterComponentInHierarchy<AudioManager>();
        builder.RegisterComponentInHierarchy<LightingAndVFXController>();
        builder.RegisterComponentInHierarchy<FlagSystem>();
        builder.RegisterComponentInHierarchy<NarrativeDirector>();
        builder.RegisterComponentInHierarchy<SaveSystem>();
        builder.RegisterComponentInHierarchy<TerminalSystem>();
        builder.RegisterComponentInHierarchy<DialogueSystem>();

        // Plain-C# collaborators
        builder.Register<DialogueLogic>(Lifetime.Scoped);

        // Transport seam (swappable in test scopes for MockTransport)
        builder.Register<IDialogueTransport, OllamaHttpTransport>(Lifetime.Scoped);
    }
}
```

References:
- Wire `CFG-*` configs and prefab fields on the scope itself in the Inspector.
- Systems consume each other through constructor injection or `[Inject]` properties; no manual `[SerializeField] private FlagSystem _flagSystem;` on consumers.
- Do not use a global bus. Do not use `DontDestroyOnLoad` in the PoC.
- The legacy `GameSystemsRoot` prefab is superseded by this scope (reviewer rule `GAMEPLAY-CODE-DI-LIFETIMESCOPE-ONLY-AT-ROOT`).

### Player

```text
Player
  CharacterController
  PlayerController
  PlayerInteractor
  VisualRoot
    SpriteRenderer
```

Setup:
- Tag: `Player`.
- Interactor collider as trigger.
- Layer: `Player`.

### PresenceTrigger

```text
PresenceTrigger_Lights_Corridor
  BoxCollider(isTrigger = true)
  PresenceEventTrigger
```

Fields:
- `director`
- `eventDefinition`

### ZoneTrigger

```text
ZoneTrigger_Exterior
  BoxCollider(isTrigger = true)
  EnvironmentZoneTrigger(zone = Exterior)
```

```text
ZoneTrigger_Airlock
  BoxCollider(isTrigger = true)
  EnvironmentZoneTrigger(zone = Airlock)
```

```text
ZoneTrigger_Interior
  BoxCollider(isTrigger = true)
  EnvironmentZoneTrigger(zone = Interior)
```

### Interactables

```text
OxygenStation
  Collider(isTrigger = false)
  OxygenStationInteractable

EnergyModule
  Collider(isTrigger = false)
  PickupInteractable

PowerPanel
  Collider(isTrigger = false)
  PanelInteractable
```

## Fast Prototyping in Unity

### Step 1: Create a blank scene

- Create `SCN_PoC_C7`.
- Block out with cubes: cabin, corridor, maintenance, airlock, exterior.
- Add simple lights.
- Add a fixed camera or a basic follow camera.

### Step 2: Create GameLifetimeScope

- Add the bootstrap GameObject with `GameLifetimeScope` (ADR-0009).
- Add the system MonoBehaviours as siblings under the same scene root; the scope picks them up via `RegisterComponentInHierarchy<T>`.
- Create `OxygenConfig` and `AgitationConfig`, drag them onto the scope's serialized fields.
- Press Play; verify oxygen drops, the scope logs `Configure` without missing-registration errors.

### Step 3: Create Player

- Add `CharacterController`.
- Add `PlayerController`.
- Add `PlayerInteractor`.
- Set tag `Player`.
- Test walking and running.

### Step 4: Wire oxygen and agitation

- Running must raise agitation.
- Agitation must increase drain.
- Standing still must lower agitation.
- Confirm with logs or temporary UI.

### Step 5: Add interior/exterior

- Create zone triggers.
- Exterior must increase drain.
- Exterior must slowly raise agitation.

### Step 6: Add interactions

- Oxygen station.
- Module pickup.
- Final panel.
- Complete the run on inserting the module.

### Step 7: Add presence

- Create the 5 fixed events as ScriptableObjects.
- Place triggers in corridor, airlock, exterior, and antenna.
- Add `PresenceAgitationTrigger` for `PRES_EXTERIOR_BEACON`.
- Use simple audio, lights, and glitches.
- Each event must add agitation.

### Step 8: Quick balance

Suggested initial values:

```text
maxOxygen = 100
baseDrainPerSecond = 0.4
exteriorMultiplier = 1.5
agitatedThreshold = 40
runningGainPerSecond = 10
exteriorGainPerSecond = 4
calmLossPerSecond = 8
agitatedOxygenMultiplier = 1.8
oxygenStationRefill = 35
```

The PoC must be completable in:
- 3 minutes if the player goes straight.
- 4 to 5 minutes if they explore a little.
- Less if they run too much and waste oxygen.

## Recommended Implementation Order

1. `GameManager`
2. `PlayerController`
3. `OxygenSystem`
4. Oxygen HUD
5. `DebugOverlay`
6. `AgitationSystem`
7. `EnvironmentSystem` + triggers
8. `IInteractable` + oxygen station
9. Module pickup + final panel
10. `PresenceDirector` + `PresenceEventTrigger` + `PresenceAgitationTrigger`
11. Airlock checkpoint
12. Lights, audio, and glitch

## Basic Debug

The debug overlay is part of the technical scope of the PoC. Add temporary shortcuts only in development builds or with `debugMode`.

Debug shortcuts read keyboard state via the Input System low-level API (`Keyboard.current`), so the project stays compliant with ADR-0010 and `UNITY-PATTERN-INPUT-SYSTEM` even in debug paths. No legacy `Input.GetKeyDown`.

```csharp
using UnityEngine;
using UnityEngine.InputSystem;

private void Update()
{
    if (!debugMode) return;

    Keyboard keyboard = Keyboard.current;
    if (keyboard == null) return;

    if (keyboard.oKey.wasPressedThisFrame)
        oxygenSystem.Refill(100f);

    if (keyboard.aKey.wasPressedThisFrame)
        agitationSystem.SetAgitation(80f);

    if (keyboard.pKey.wasPressedThisFrame)
        presenceDirector.Play(testPresenceEvent);

    if (keyboard.cKey.wasPressedThisFrame)
        checkpointController.RestartFromAirlockCheckpoint();
}
```

Always show in `DebugOverlay`:
- Temporary numeric oxygen.
- Temporary numeric agitation.
- Current zone.
- Game state.
- Last presence `eventId`.

Also useful:
- Draw trigger gizmos.
- Log the `eventId` when presence fires.

## Mistakes to Avoid

- Building a full inventory system for a single module.
- Building AI for the presence.
- Building a global event bus before it is needed.
- Using singletons for every system.
- Hiding important rules inside animations or timeline.
- Letting the UI compute gameplay.
- Letting interactables modify many systems at once.

## Done Criteria

The base implementation is done when:
- The player can move through interior and exterior.
- Oxygen drops while in `Playing`.
- Running raises agitation.
- Agitation multiplies drain.
- Exterior multiplies drain.
- The station refills only once.
- The 5 fixed presence events exist as ScriptableObjects.
- A trigger fires a presence event.
- `PRES_EXTERIOR_BEACON` can fire from the agitation threshold outside.
- An event plays sound, alters lights or glitch, and raises agitation.
- The debug overlay shows oxygen, agitation, zone, state, and last event.
- Retrying from failure restores the airlock checkpoint.
- Picking up the module and using the panel completes the PoC.
- Reaching zero oxygen fails the PoC.
