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

- Unity with URP.
- A single main scene: `SCN_PoC_C7`.
- 2.5D movement over a simple 3D environment.
- 2D sprites for the character and some elements.
- Trigger-driven presence events, not AI.
- Simple input: movement, run, interact.

## Script Structure

```text
Assets/
  LastBreath/
    Scripts/
      Core/
        GameManager.cs
        GameState.cs
        PocCheckpointController.cs
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
    Completed,
    Failed,
    Paused
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

### Minimum checkpoint

The PoC has a single checkpoint: when activating the airlock before going outside.

Recommended state:
- Player position: interior side of the airlock.
- Oxygen: 70%.
- Agitation: low.
- Zone: `Airlock`.
- Energy module: not picked up.
- Objective: retrieve module.
- Events before the airlock: already fired.
- Oxygen station: keeps whether it was used or not.

Simple implementation:
- Save references to a `Transform airlockCheckpoint`.
- On failure, show a `Failed` screen with a "Retry" option.
- On retry, reposition the player, restore oxygen/agitation, and reset only the interactables after the airlock.
- Do not build a general save/load.

### PocCheckpointController

Minimal version to retry from the airlock.

```csharp
using UnityEngine;

public class PocCheckpointController : MonoBehaviour
{
    [SerializeField] private GameManager gameManager;
    [SerializeField] private PlayerController player;
    [SerializeField] private OxygenSystem oxygenSystem;
    [SerializeField] private AgitationSystem agitationSystem;
    [SerializeField] private EnvironmentSystem environmentSystem;
    [SerializeField] private ObjectiveSystem objectiveSystem;
    [SerializeField] private Transform airlockCheckpoint;

    public void RestartFromAirlockCheckpoint()
    {
        player.transform.position = airlockCheckpoint.position;
        oxygenSystem.SetOxygen(70f);
        agitationSystem.SetAgitation(10f);
        environmentSystem.SetZone(EnvironmentZone.Airlock);
        objectiveSystem.RemoveItem("energy_module");
        objectiveSystem.SetObjective("recover_module");
        gameManager.SetState(GameState.Playing);
    }
}
```

Reset module, panel, and later events with explicit references if the playtest requires it. Avoid a generic save system.

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

public class PlayerController : MonoBehaviour
{
    [SerializeField] private CharacterController controller;
    [SerializeField] private float walkSpeed = 2.5f;
    [SerializeField] private float runSpeed = 4.0f;

    public PlayerState State { get; } = new PlayerState();

    private void Update()
    {
        Vector2 input = new Vector2(
            Input.GetAxisRaw("Horizontal"),
            Input.GetAxisRaw("Vertical")
        );

        input = Vector2.ClampMagnitude(input, 1f);

        bool wantsRun = Input.GetKey(KeyCode.LeftShift);
        State.IsMoving = input.sqrMagnitude > 0.01f;
        State.IsRunning = State.IsMoving && wantsRun;

        float speed = State.IsRunning ? runSpeed : walkSpeed;
        Vector3 movement = new Vector3(input.x, 0f, input.y);

        controller.Move(movement * speed * Time.deltaTime);
    }
}
```

Notes:
- For 2.5D with a side camera, you can constrain Z or X depending on the layout.
- If using Rigidbody, keep the same idea but move in `FixedUpdate`.

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
    public float Normalized => CurrentOxygen / config.maxOxygen;

    public event Action<float> OnOxygenChanged;
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
        OnOxygenChanged?.Invoke(Normalized);
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
        OnOxygenChanged?.Invoke(Normalized);

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

    public void Play(PresenceEventDefinition definition)
    {
        if (definition.triggerOnce && triggeredEvents.Contains(definition.eventId))
            return;

        triggeredEvents.Add(definition.eventId);
        LastEventId = definition.eventId;
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

Simple version with trigger:

```csharp
using UnityEngine;

public class PlayerInteractor : MonoBehaviour
{
    private IInteractable currentInteractable;

    private void Update()
    {
        if (currentInteractable == null)
            return;

        if (Input.GetKeyDown(KeyCode.E) && currentInteractable.CanInteract)
        {
            PlayerController player = GetComponentInParent<PlayerController>();
            currentInteractable.Interact(player);
        }
    }

    private void OnTriggerEnter(Collider other)
    {
        currentInteractable = other.GetComponent<IInteractable>();
    }

    private void OnTriggerExit(Collider other)
    {
        IInteractable interactable = other.GetComponent<IInteractable>();

        if (interactable == currentInteractable)
            currentInteractable = null;
    }
}
```

Notes:
- For mouse click, replace this with a camera raycast.
- For the PoC, trigger + `E` key is faster and enough.

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

### GameSystemsRoot

In-scene prefab with:

```text
GameSystemsRoot
  GameManager
  PocCheckpointController
  OxygenSystem
  AgitationSystem
  EnvironmentSystem
  PresenceDirector
  ObjectiveSystem
  HudController
  DebugOverlay
```

References:
- Wire everything in the Inspector.
- Do not use a global bus.
- Do not use `DontDestroyOnLoad` in the PoC.

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

### Step 2: Create GameSystemsRoot

- Add main scripts.
- Create `OxygenConfig` and `AgitationConfig`.
- Wire references in the Inspector.
- Verify oxygen drops in Play Mode.

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

```csharp
private void Update()
{
    if (!debugMode)
        return;

    if (Input.GetKeyDown(KeyCode.O))
        oxygenSystem.Refill(100f);

    if (Input.GetKeyDown(KeyCode.A))
        agitationSystem.SetAgitation(80f);

    if (Input.GetKeyDown(KeyCode.P))
        presenceDirector.Play(testPresenceEvent);

    if (Input.GetKeyDown(KeyCode.C))
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
