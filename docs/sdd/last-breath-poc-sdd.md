# Last Breath - Software Design Document PoC

## Technical Goal

Define a simple architecture for a 3 to 5 minute PoC in Unity + URP. The focus is fast iteration, separated systems, and avoiding unnecessary infrastructure.

The PoC must enable:
- A playable interior/exterior scene.
- Oxygen that drops over time.
- Agitation that modifies drain.
- Trigger-driven presence events.
- Simple interactions.
- Clear flow for start, play, success, and failure.

## Architecture Principles

- Use `MonoBehaviour` for runtime systems.
- Use `ScriptableObject` only for editable data and balance.
- Communicate systems with explicit references and simple C# events.
- Avoid singletons except `GameManager` if it simplifies the PoC.
- Avoid complex AI, complex inventory, and a generic event bus.
- Keep every system to a single clear responsibility.
- Prefer small scenes and Inspector-configurable prefabs.

## General Architecture

The architecture splits into four simple layers:

1. Core
   - Holds the global state of the PoC.
   - Coordinates start, pause, success, death, and restart.

2. Gameplay Systems
   - Oxygen, agitation, interactions, presence, and environment conditions.
   - Contain the playable rules.

3. Presentation
   - UI, audio, lights, camera, visual effects.
   - Reacts to gameplay events.

4. Content
   - Triggers, interactables, zones, presence events, and balance data.
   - Configured mainly through prefabs and ScriptableObjects.

## Main Systems

### GameManager

Responsibility:
- Hold the global game state.
- Initialize the playable scene.
- Listen for death/success conditions.
- Trigger restart, PoC end, or pause.

Must not:
- Compute oxygen drain.
- Execute presence events directly.
- Contain UI-specific logic.

Suggested API:
- `StartRun()`
- `PauseGame()`
- `ResumeGame()`
- `FailRun(FailReason reason)`
- `CompleteRun()`
- `SetGameState(GameState state)`

Events:
- `OnGameStateChanged(GameState state)`
- `OnRunFailed(FailReason reason)`
- `OnRunCompleted()`

### PlayerController

Responsibility:
- Read player input from the `Gameplay` action map of `PlayerControls.inputactions` (Input System 1.11.2 — see ADR-0010).
- Drive the `CharacterController` on the **XZ plane** of a perspective 3D scene; Y is locked at 0 in the PoC.
- Expose `PlayerState` to other systems (read-only consumers).

Movement plane:
- Axis mapping is fixed: `Move.x → world X`, `Move.y → world Z`. The character is a billboard sprite, but movement is genuine 3D with depth. Y is locked: no jump, no gravity in the PoC.
- Run is hold-to-sprint and only applies while `Move` is non-zero.

Inputs (read):
- `InputActionReference` for `Move`, `Run`, `Interact`, `Pause`. No `Input.GetAxis*`, no `Input.GetKey*`. Bindings live in the committed action asset; the controller never names key codes inline. See `UNITY-PATTERN-INPUT-SYSTEM`.
- `GameManager.CurrentState` via `[Inject]`. When `CurrentState != Playing`, the action map is disabled and the controller short-circuits its `Update`. Composes with the terminal-suppression invariant (`§TerminalSystem` and `§DialogueSystem`) and with `GAMEPLAY-CODE-SAVE-NO-EVENTS-DURING-LOADING`.

Dependencies:
- VContainer `[Inject]` for `GameManager`. `[SerializeField]` for `CharacterController`, `PlayerMovementConfig` (`CFG-PLAYER-MOVEMENT`), and the four `InputActionReference` slots.
- No direct reference to `CameraSystem`. Camera follow is push-driven from the rig (`CameraRig.Follow = playerTransform`); the controller does not know it is being watched.

State exposed (`PlayerState`):
- `IsMoving` — `bool`, true when the latest `Move` value has non-zero magnitude past the deadzone.
- `IsRunning` — `bool`, true when `IsMoving && Run.IsPressed()`.
- `MoveSpeed`, `RunSpeed` — `float`, read from `CFG-PLAYER-MOVEMENT`.
- `CurrentZone` — `EnvironmentZone`, updated by `EnvironmentSystem` (not by the controller).

Billboard:
- The character's visual root carries a `PlayerBillboard` MonoBehaviour that is **not** part of `PlayerController`. The billboard rotates only around world Y in `LateUpdate` so the sprite faces the camera horizontally. See `§CameraSystem` and ADR-0010 §Decision item 3.

Must not:
- Modify oxygen directly.
- Play presence events.
- Decide death conditions.
- Own its own rotation. Rotation is the billboard's job.
- Call `Camera.main` or `FindObjectOfType<Camera>()`. The controller is camera-agnostic.

### CameraSystem

Responsibility:
- Own the gameplay virtual camera and the URP `Volume` that hosts depth of field. Follow the `PlayerController` smoothly on X and Z, with Y fixed. Drive the DOF override so the player stays in focus while the background blurs. See ADR-0010.

Projection and rig:
- **Perspective**, FOV ~35°. Cinemachine 3 `CinemachineCamera` with a `CinemachinePositionComposer` extension. Damping X ~0.3, Z ~0.5, Y = 0. No look-ahead. The exact values live in `CFG-CAMERA-RIG`.
- Orthographic is forbidden by ADR-0010. Re-introducing it requires an amendment.

Depth of field:
- One URP global `Volume` with a `DepthOfField` override in **Bokeh** mode. `focusDistance` is driven every frame by `CameraDofDriver` as `Vector3.Distance(camera.position, playerTransform.position)`. Other DOF fields (`aperture`, `focalLength`, `bladeCount`) live in `CFG-CAMERA-DOF`.
- The driver is read-only on game state. It does not touch `OxygenSystem`, `AgitationSystem`, `GameManager`, or any save path.

Inputs (read):
- `PlayerController.transform` (follow target; the rig holds the reference, not the player).
- `Camera.main` for the billboard side (resolved by `PlayerBillboard`, not by the rig).

Outputs:
- None. The camera is presentation infrastructure. It does not publish events.

Invariants:
- Perspective only.
- The camera never tilts or rolls. Y rotation matches the player's facing only through the billboard, never through the rig.
- DOF runs every frame; the driver no-ops if `Camera.main` or the target is null (editor edge case only — production always wires both via the `LifetimeScope`).
- The rig never reads input. Player movement happens; the rig follows.

Acceptance:
- Player walks XZ → camera position lerps in X and Z, Y unchanged.
- Player stops → DOF `focusDistance` settles to player distance within ~0.3 s.
- `EditMode`: `CameraRig.ComputeFollowPosition(target, previous, dt)` is a pure function; a round-trip test asserts no Y drift and convergence at the configured damping.

### OxygenSystem

Responsibility:
- Hold the current oxygen value.
- Decrease oxygen each frame during gameplay.
- Apply drain multipliers.
- Notify changes and thresholds.

Inputs:
- Agitation multiplier from `AgitationSystem`.
- Environment multiplier from `EnvironmentSystem`.
- Global state from `GameManager`.

Base rule:

`oxygenDrain = baseDrainRate * agitationMultiplier * environmentMultiplier`

Internal states:
- `Stable`
- `Warning`
- `Critical`
- `Depleted`

Suggested API:
- `ResetOxygen()`
- `Consume(float amount)`
- `Refill(float amount)`
- `SetExternalMultiplier(float multiplier)`
- `SetAgitationMultiplier(float multiplier)`

Events:
- `OnOxygenChanged(float current, float max)` — payload matches `EVT-oxygen-changed` in `architecture.yaml`. Consumers derive the normalized value themselves (`current / max`).
- `OnOxygenWarning(OxygenWarningLevel level)`
- `OnOxygenDepleted()`

### AgitationSystem

Responsibility:
- Hold the player's agitation level.
- Raise agitation due to running, presence events, and dangerous zones.
- Reduce agitation in safe conditions.
- Translate agitation into an oxygen multiplier.

Inputs:
- `PlayerController.IsRunning`
- Events from `PresenceDirector`
- Zone type from `EnvironmentSystem`
- Darkness or danger triggers.

Output:
- Drain multiplier for `OxygenSystem`.
- Events for UI/audio/effects.

Suggested API:
- `AddAgitation(float amount, AgitationSource source)`
- `ReduceAgitation(float amount)`
- `SetZonePressure(float amountPerSecond)`
- `GetOxygenMultiplier()`

Events:
- `OnAgitationChanged(float normalizedValue)`
- `OnAgitationTierChanged(AgitationTier tier)`

### PresenceDirector

Responsibility:
- Run the presence events defined for the scene.
- Prevent too many events from firing together.
- Notify agitation generated by each event.

PoC implementation:
- Triggers placed in the scene call the director.
- The director validates whether the event can run.
- The event activates audio, lights, glitches, or doors.
- The event adds agitation.

Must not:
- Have pathfinding.
- Simulate a physical entity.
- Chase the player.

Suggested API:
- `TriggerEvent(PresenceEventDefinition eventDefinition)`
- `CanTrigger(PresenceEventDefinition eventDefinition)`
- `StopAllEvents()`

Events:
- `OnPresenceEventFired(string eventId, float intensity)` — published once when an event begins. Payload matches `EVT-presence-event-fired` in `architecture.yaml`. `intensity` is the designer-set `PresenceEventDefinition.intensity` (0..1) so audio/lighting/dialogue subscribers can scale their reaction.

Internal-only:
- The director may keep a private `OnPresenceEventFinished` notification for its own cleanup, but that is not part of the public event contract.

### PlayerInteractor

Responsibility:
- Detect nearby interactables from the player.
- Show the interaction prompt.
- Run simple actions.

Recommended model:
- Interface `IInteractable`.
- Each interactable object implements its own action.

Examples:
- `DoorInteractable`
- `PanelInteractable`
- `OxygenStationInteractable`
- `PickupInteractable`
- `TerminalInteractable`

Suggested API:
- `SetFocusedInteractable(IInteractable interactable)`
- `TryInteract()`

Suggested interface:

```csharp
public interface IInteractable
{
    string Prompt { get; }
    bool CanInteract { get; }
    void Interact(PlayerContext context);
}
```

### EnvironmentSystem

Responsibility:
- Know whether the player is in interior, airlock, or exterior.
- Apply environment multipliers.
- Notify condition changes.

Zones:
- `Interior`: normal drain, stable agitation.
- `Airlock`: transition, optional limited input.
- `Exterior`: higher drain, gradual agitation, muffled audio.

Suggested API:
- `SetZone(EnvironmentZone zone)`
- `GetOxygenMultiplier()`
- `GetAgitationPressure()`

Events:
- `OnZoneChanged(EnvironmentZone zone)`

### ObjectiveSystem

Responsibility:
- Hold the current PoC objective and notify when one completes (`SYS-OBJECTIVE`). Owns the player-facing objective chain. The player-facing verb itself lives in `SYS-INTERACTOR`; this system only translates completed interactions into objective progression.

Inputs:
- `EVT-interaction-completed { interactable_id }` — the trigger for evaluating whether the current objective is satisfied.
- `CFG-OBJECTIVE` (`ObjectiveDefinition`) — the per-objective definition: `objectiveId`, completion predicate, optional `nextObjectiveId`.

Outputs:
- `EVT-objective-completed { objective_id }` — emitted exactly once per objective when its predicate matches.

Invariants:
- One objective is active at a time; progression is linear.
- Does not touch UI directly. The HUD subscribes to `EVT-objective-completed` and reads the current objective text from this system.
- Does not open doors, modify flags, or fire presence events. Other systems may listen to `EVT-objective-completed` and react.

Acceptance:
- Completing the interaction tied to objective N (`interactable_id` matches the definition's predicate) emits exactly one `EVT-objective-completed` and advances the active objective to `nextObjectiveId`.
- A second `EVT-interaction-completed` for the same `interactable_id` after objective N has already advanced does NOT re-fire `EVT-objective-completed`.
- The HUD's "current objective" string changes within the same frame as `EVT-objective-completed`.

PoC objectives:
1. Restore power in C-7.
2. Reach the airlock.
3. Retrieve the energy module.
4. Return to maintenance.
5. Insert the module.

### HudController

Responsibility:
- Show oxygen, critical state, interaction prompt, and current objective.
- Listen to system events.
- Contain no playable logic.

Minimum elements:
- Oxygen indicator.
- Subtle agitation indicator.
- Current objective text.
- Contextual prompt.
- Failure/success screen.

### AudioManager

Responsibility:
- Play breathing, knocks, radio, and interior/exterior ambience.
- Switch audio mix by zone and agitation.
- Receive events from gameplay systems.

Suggested layers:
- `AmbienceInterior`
- `AmbienceExterior`
- `Breathing`
- `Heartbeat`
- `Radio`
- `PresenceStingers`

### LightingAndVFXController

Responsibility:
- Run light flickers, brief blackouts, glitches, and URP effects.
- Respond to presence events.
- Expose simple actions for triggers.

Must not:
- Decide when an event happens.
- Modify oxygen or agitation.

### FlagSystem

Custodian of persistent boolean world state for graphic-adventure unlocks (see `SYS-FLAGS`, ADR-0004).

Responsibility:
- Hold the runtime value of every `FlagDefinition` (`CFG-FLAG`) and publish transitions.

Inputs:
- Public API only. Callers (`FlagSetter`, gameplay code) invoke `Set(FlagDefinition, bool)` and `IsSet(FlagDefinition)`.
- `SaveSystem` calls a silent restore path that does not publish.
- No event subscriptions.

Outputs:
- `EVT-flag-changed { flag_id, value }` on every value transition.

Invariants:
- A flag is identified by reference to its `FlagDefinition`; the `flag_id` string is for the public payload and debugging, never as the in-code key.
- `Set` is idempotent: setting a flag to its current value is a no-op and publishes no event.
- All flags reset to `FlagDefinition.defaultValue` on `Awake` unless restored by `SaveSystem`.

Acceptance:
- Setting a flag fires `EVT-flag-changed` exactly once.
- Setting an already-set flag fires no event.
- `IsSet(definition)` returns the last value passed to `Set`.
- A save restore writes flag values without firing `EVT-flag-changed` (silent restore, ADR-0005).

Notes:
- `FlagGate` and `FlagSetter` are designer-wire components that consume the public API. Per ADR-0004, `UnityEvent` is allowed only on these designer-wire components, never on systems.

### NarrativeDirector

Evaluates `NarrativeCueDefinition` assets against current flag state and publishes narrative cues (see `SYS-NARRATIVE`, ADR-0004). Mirror of `PresenceDirector`.

Responsibility:
- Watch flag transitions and fire narrative cues whose required-flag conditions are satisfied.

Inputs:
- `EVT-flag-changed`.
- A serialized list of `NarrativeCueDefinition` (`CFG-NARRATIVE-CUE`) assets at scene load.
- `FlagSystem` (read-only via API) to evaluate `requiredFlags`.

Outputs:
- `EVT-narrative-cue-fired { cue_id }`.

Invariants:
- A cue with `oneShot = true` fires at most once per save.
- `setsFlags` is applied AFTER `EVT-narrative-cue-fired` is published, so subscribers see the cue before the cascade.
- During `GameState.Loading`, the director does not evaluate or fire.

Acceptance:
- A flag transition that satisfies a cue's `requiredFlags` fires that cue.
- A cue whose `setsFlags` are all already true does not infinitely re-trigger; re-entry is prevented by `oneShot` or by checking already-true.
- Restoring a save does not re-fire cues that had already fired; the fired-one-shots set is captured in `NarrativeDto.firedOneShots`.

### SaveSystem

Orchestrator of capture and restore for all gameplay state (see `SYS-SAVE`, ADR-0005). Only system permitted to touch disk.

Responsibility:
- Aggregate per-system DTOs into a versioned `SaveData` snapshot, write to disk, and drive the inverse restore.

Inputs:
- `EVT-flag-changed` (for save-point detection).
- Direct calls to every saveable system's `CaptureState()` / `RestoreState(dto)` via `ISaveable<TDto>`.
- `GameManager` to drive the `Loading` state during restore.

Outputs:
- `EVT-save-completed { slot }` after a write.
- `EVT-save-restored {}` after a restore completes and before the transition back to `Playing`.

Invariants:
- Only `SaveSystem` writes to disk; no other system touches `File.*` or `PlayerPrefs`.
- During `GameState.Loading`, no system publishes events (gameplay systems gate their `Update` and event-raises on `State == Playing`).
- Save format is versioned (`SaveData.version`); migrations live in a single `Migrate(SaveData)` function.

Acceptance:
- Capture, write, read, restore yields a state observationally equal to the moment of capture.
- Restoring a save whose `sceneName` matches the current scene works without a scene reload.
- Setting a flag whose `FlagDefinition.isSavePoint == true` triggers `Save("autosave")` automatically.

Save-point flow:
- `SaveSystem` subscribes to `EVT-flag-changed`. When the value becomes `true` and `flag.isSavePoint == true`, it captures and writes. The flag itself is the trigger; the save is the side-effect. No autosave-by-time.

Notes:
- Dynamic world objects (interactables, doors) implement `IPersistentInteractable` with a designer-assigned `PersistenceId`. An `InteractableRegistry` collects them via `OnEnable` / `OnDisable` and is serialized as part of `SaveData`. Per-system DTO shapes are documented in TDD `§SaveData`.

### TerminalSystem

Owns the per-terminal chat UI lifecycle and the per-terminal inbox of pending AI messages (see `SYS-TERMINAL`, ADR-0006).

Responsibility:
- Manage the open/close lifecycle of the chat UI bound to a `TerminalInteractable`, and hold the inbox of scripted AI messages waiting at each terminal.

Inputs:
- `PlayerInteractor` focuses a `TerminalInteractable` on trigger overlap; the interact key on a focused terminal opens the chat UI.
- `EVT-dialogue-response-ready` — renders the response text into the currently open terminal when `terminal_id` matches.
- `EVT-ai-message-delivered` — badges an inbox entry as new on the target terminal.

Outputs:
- `EVT-terminal-opened { terminal_id }` when the chat UI opens.
- `EVT-terminal-closed { terminal_id }` when the chat UI closes.

Invariants:
- At most one terminal is open at any time. A second open call while a terminal is already open is a no-op (the request is dropped, no event fires).
- While a terminal is open, `PlayerController` movement and interaction input is suppressed; the player stands still. `OxygenSystem` and `AgitationSystem` continue to tick (intentional, per PILLAR-04).
- `TerminalInteractable` is a peer of `PanelInteractable`; both implement `IInteractable`. `TerminalInteractable` does not extend `PanelInteractable`.
- Inbox state per terminal is owned by `TerminalSystem` in memory and serialized through `SYS-DIALOGUE`'s DTO. `TerminalSystem` itself is NOT `ISaveable<T>`.
- During `GameState.Loading`, open/close requests are dropped and no terminal event is published. The chat UI is closed at the start of restore (see ADR-0005, `SAVE-NO-EVENTS-DURING-LOADING`).

Acceptance:
- Walking up to a `TerminalInteractable` and pressing interact opens the chat UI and fires `EVT-terminal-opened` exactly once.
- Closing the chat UI (esc key or close button) fires `EVT-terminal-closed` exactly once.
- A `EVT-dialogue-response-ready` whose `terminal_id` matches the currently open terminal renders into its panel; responses addressed to other terminals are ignored by this surface (they may still be routed by `SYS-DIALOGUE`).
- The unread-inbox count on a terminal increments when `EVT-ai-message-delivered` fires with that `terminal_id`.

Notes:
- The "chat UI" is concretely a uGUI + TextMeshPro custom surface, owned by a `TerminalChatView` MonoBehaviour bound to `TerminalSystem` via `[SerializeField] private TerminalChatView _chatView`. Components: `TerminalChatPanel.prefab` (Canvas root), `ChatHistoryView` (scrolling transcript), `ChatInputField` (TMP_InputField + Send + Enter binding), `AvailabilityIndicator` (status line driven by `AvailabilityState`), and `ChatEntry.prefab` in three role variants (`player`, `ship-ai-online`, `ship-ai-garbled`). The `ship-ai-garbled` variant uses TMP rich-text glitch tags / random char substitution. Concrete component shapes declared in TDD `### Terminal chat UI components`. UI framework choice (uGUI over UI Toolkit, custom over third-party package) ratified by `SPEC-2026-05-12-ship-ai-context-and-runtime` decision 5.
- The chat UI renders three distinct turn outcomes, all surfaced through `EVT-dialogue-response-ready`: (a) normal speech entry when `tags` lack both `silent` and (`nonsequitur` + `false-claim`); (b) garbled glitch entry when `tags` include both `nonsequitur` and `false-claim`; (c) "NO RESPONSE" indicator pulse with no chat entry when `tags` include `silent`.

### DialogueSystem

Drives the ship-AI live channel and routes scripted AI messages to terminal inboxes (see `SYS-DIALOGUE`, ADR-0006, ADR-0002).

Responsibility:
- Resolve player turns via `IDialogueTransport`, maintain AI internal state (`mandate`, `integrity`, `budget`), route flag-triggered messages to terminal inboxes, and persist conversation history.

Inputs:
- `EVT-terminal-opened` — tracks which terminal is the active live-channel surface.
- `EVT-flag-changed` — evaluates inbox routing rules. The routing table is a serialized list of `DialogueCueDefinition` assets (`CFG-DIALOGUE-AI` references them; see "decision" below). Each cue maps a flag transition to a target `terminalId` and a body string.
- `EVT-oxygen-changed`, `EVT-agitation-changed`, `EVT-zone-changed`, `EVT-presence-event-fired` — update the snapshot used by `DialogueLogic` to build the per-turn context.
- `EVT-interaction-completed` — feeds two things: (a) caches the most recent non-null `IFocusLabel.FocusLabel` as the run's `lastSignificantInteraction`; (b) appends a `RecentEvent(ProtocolBreach, JustNow)` to the `recentEvents` queue when the source interactable is marked as protocol-breaching. Subscription added by `SPEC-2026-05-12-ship-ai-context-and-runtime`.
- Direct method call `SubmitTurnAsync(string text)` invoked by `TerminalSystem` when the player submits a line in the chat UI. Not an event.

Outputs:
- `EVT-dialogue-response-ready { terminal_id, speech, tags }` after each live turn resolves (success or fallback).
- `EVT-ai-message-delivered { terminal_id, message_id }` when a flag-triggered AI message is routed to a terminal inbox.

Invariants:
- All access to the LLM goes through `IDialogueTransport`. No class outside `SYS-DIALOGUE` calls a transport directly (reviewer rule `GAMEPLAY-CODE-DIALOGUE-NO-DIRECT-LLM`). **`IDialogueTransport.SendAsync` is invoked only when `DialogueLogic.EvaluateAvailability(...)` returns `Online`** (per ADR-0006 amendment 2026-05-12; "Decision — availability gating" below).
- The prompt context sent to the model is built from an explicit allowlist of fields; arbitrary state is never auto-included (reviewer rule `GAMEPLAY-CODE-DIALOGUE-PROMPT-MUST-WITHHOLD`).
- The AI internal state (`mandate`, `integrity`, `budget`) is private to `DialogueLogic`. It surfaces in events only through the `tags` payload (e.g., `["refusal","policy"]`) and the `speech` text — never as numeric fields. `HudController` does not subscribe to mandate/integrity/budget.
- During `GameState.Loading`, no `EVT-dialogue-response-ready` or `EVT-ai-message-delivered` is published, and `IDialogueTransport.SendAsync` is not invoked. Restored exchanges are the truth (ADR-0005, `SAVE-NO-EVENTS-DURING-LOADING`; ADR-0006).
- `DialogueSystem` is `ISaveable<DialogueDto>`. The DTO holds: bounded exchanges (last N turns), per-terminal inbox entries, `mandate` / `integrity` / `budget`, `turnCount`, the `recentEvents` queue (cap 10, FIFO; restored with all `age` demoted to `EarlierThisRun`), and `lastSignificantInteraction`. DTO shape declared in TDD `§Dialogue`.
- Endpoint configuration, model names, and any transport credentials are never captured in `DialogueDto` (reviewer rule `GAMEPLAY-CODE-DIALOGUE-NO-SECRETS-IN-SAVE`).
- `DialogueSystem` is a MonoBehaviour adapter; the formula-bearing logic lives in `DialogueLogic`, a plain C# class (ADR-0002).

Acceptance:
- `SubmitTurnAsync` with a non-empty string returns a valid response (success, fallback, garbled, or silent) within the configured transport timeout budget.
- Two consecutive turns produce two `EVT-dialogue-response-ready` events with monotonically-increasing turn indices.
- A flag transition that satisfies a `DialogueCueDefinition` routing rule produces `EVT-ai-message-delivered` exactly once per `(flag transition, terminal)` pair.
- `Capture → Restore` round-trip: a saved conversation reloads with identical `exchanges`, `inbox`, `mandate`, `integrity`, `budget`, `turnCount`, and `lastSignificantInteraction`. `recentEvents` are restored with the same tags but all `age` values demoted to `EarlierThisRun`. No transport call occurs during restore.
- A transport timeout produces a `EVT-dialogue-response-ready` whose `speech` is the configured offline fallback and whose `tags` include `"false-claim"`, marking the failure as in-fiction degradation (ADR-0006).
- A `Garbled` availability turn produces a `EVT-dialogue-response-ready` whose `speech` is `_aiConfig.garbledReplies[turnCount % length]` and whose `tags` are `["nonsequitur","false-claim"]`. `IDialogueTransport.SendAsync` is not called. `integrity` is ticked down per the configured curve.
- A `Silent` availability turn produces a `EVT-dialogue-response-ready` whose `speech` is empty and whose `tags` are `["silent"]`. `IDialogueTransport.SendAsync` is not called. `integrity` is unchanged. The exchange is appended to history with empty `aiSpeech`.

Decision — inbox routing config:
- A new ScriptableObject `DialogueCueDefinition` (`CFG-DIALOGUE-AI` references a list of these) is used for inbox routing, separate from `NarrativeCueDefinition` (`CFG-NARRATIVE-CUE`) which feeds `NarrativeDirector`.
- Rationale: `NarrativeCueDefinition` exists to fire audio/HUD cues from flag transitions; inbox messages have a different consumer (`DialogueSystem`), different payload (target `terminalId`, body string, `message_id`), and a different lifetime model (waits in an inbox until read, not fire-and-forget). Reusing one SO would conflate two consumers and risk `NarrativeDirector` firing an audio cue while `DialogueSystem` also delivers the same body as an inbox entry. The extra config type is cheaper than the conflation.

Decision — availability gating (ratified by SPEC-2026-05-12-ship-ai-context-and-runtime, codified in ADR-0006 amendment 2026-05-12):
- The ship AI is not always-on. Whether a turn results in a normal LLM call, a canned garbled reply, or a silent no-reply is a function of the active zone and the current flag values, designer-tunable via `MotherAvailabilityRule` ScriptableObjects (`CFG-AVAILABILITY-RULE`).
- `DialogueLogic.EvaluateAvailability(ctx, _availabilityRules, _flagSystem.Snapshot())` runs **before** any transport call. It returns one of `Online | Garbled | Silent`. Default is `Online` when no rule matches.
- Rule shape: `(zone, requiredFlags, forbiddenFlags) → AvailabilityState` ordered by `priority` (higher wins; ties resolved by file order, with a startup warning logged for designers).
- Branches:
  - `Online` → existing flow: `BuildContext → BuildPrompt → SendAsync → ParseResponse`.
  - `Garbled` → no transport call. `DialogueSystem` selects `_aiConfig.garbledReplies[turnCount % length]` (deterministic, replays identically across save/restore for the same turn), tags the synthesized response `["nonsequitur","false-claim"]`, ticks `integrity` down. Failure looks like AI degradation — on-genre with ADR-0006.
  - `Silent` → no transport call. Empty-speech response with `tags=["silent"]`. Does NOT touch `integrity` (silence is environmental, not internal failure). The exchange is still appended to history so the player's input survives in the save and the next turn's `recentExchanges` includes the silent attempt.
- This strengthens `GAMEPLAY-CODE-DIALOGUE-NO-DIRECT-LLM`: `SendAsync` is now confined to `SYS-DIALOGUE` AND to the `Online` branch.

## Communication Between Systems

### General rule

Use direct references for stable scene dependencies and C# events for notifications.

Example:
- `OxygenSystem` holds a reference to `AgitationSystem` or receives a multiplier via event.
- `HudController` listens to `OxygenSystem.OnOxygenChanged`.
- `PresenceDirector` calls `AgitationSystem.AddAgitation`.

### Communication matrix

| Source | Target | Reason |
| --- | --- | --- |
| `GameManager` | All systems | Enable/disable gameplay by state |
| `AgitationSystem` | `OxygenSystem` | Update drain multiplier |
| `EnvironmentSystem` | `OxygenSystem` | Apply interior/exterior drain |
| `EnvironmentSystem` | `AgitationSystem` | Apply zone pressure |
| `PresenceDirector` | `AgitationSystem` | Increase agitation per event |
| `PresenceDirector` | `AudioManager` | Play presence sounds |
| `PresenceDirector` | `LightingAndVFXController` | Run visual alterations |
| `PlayerInteractor` | `IInteractable` | Run object action |
| `ObjectiveSystem` | `HudController` | Show current objective |
| `OxygenSystem` | `GameManager` | Report oxygen depleted |
| `FlagSystem` | All systems (via `FlagGate` / `FlagSetter`) | Persistent boolean state for graphic-adventure unlocks |
| `NarrativeDirector` | `AudioManager`, `HudController` | Trigger narrative cues from flag transitions |
| `SaveSystem` | All saveable systems | Capture/restore state; orchestrates Loading |
| `FlagSystem` | `SaveSystem` | Save-point flags trigger autosave |
| `TerminalSystem` | `DialogueSystem` | Terminal lifecycle drives which terminal is the active live-channel surface |
| `DialogueSystem` | `TerminalSystem` | Live-channel responses and inbox deliveries render into the addressed terminal |
| `DialogueSystem` | `AudioManager`, `HudController` | Dialogue tags surface as audio cues and HUD prompts (e.g., `warning` may dim the HUD; `refusal` may play a denial sound) |
| `FlagSystem` | `DialogueSystem` | Flag transitions route scripted AI messages into terminal inboxes |

### Minimum shared events

```csharp
public enum GameState
{
    Boot,
    Intro,
    Playing,
    AirlockTransition,
    Paused,
    Loading,
    Completed,
    Failed
}

public enum EnvironmentZone
{
    Interior,
    Airlock,
    Exterior
}

public enum AgitationTier
{
    Calm,
    Tense,
    Panicked
}
```

## Managers

### Recommended managers for the PoC

- `GameManager`: global state.
- `SaveSystem`: snapshot/restore at flag save-points (replaces the legacy `PocCheckpointController`, kept only as a deprecated registry entry; ADR-0005).
- `OxygenSystem`: main resource.
- `AgitationSystem`: mechanical tension.
- `PresenceDirector`: presence events.
- `EnvironmentSystem`: interior/exterior conditions.
- `ObjectiveSystem`: PoC progress.
- `HudController`: HUD.
- `DebugOverlay`: development diagnostic.
- `AudioManager`: audio.

`PlayerInteractor` lives in the `Player` prefab, not on the `LifetimeScope`.

### Usage rule

Managers must exist once per playable scene and are **registered on the scene's VContainer `LifetimeScope`** (ADR-0009 §DI). Cross-system references resolve through the container — never through a manual prefab walk, never through `FindObjectOfType`, never through a static `Instance`.

The composition root for the main playable scene is `GameLifetimeScope` (a `LifetimeScope` subclass; see TDD `§GameLifetimeScope`). It lives on a single bootstrap GameObject in the scene root and registers every system listed above plus the dialogue / save / narrative families:

```text
GameLifetimeScope (VContainer composition root)
  registers:
    GameManager                       (Lifetime.Scoped)
    OxygenSystem                      (Lifetime.Scoped)
    AgitationSystem                   (Lifetime.Scoped)
    PresenceDirector                  (Lifetime.Scoped)
    EnvironmentSystem                 (Lifetime.Scoped)
    ObjectiveSystem                   (Lifetime.Scoped)
    HudController                     (Lifetime.Scoped)
    DebugOverlay                      (Lifetime.Scoped)
    AudioManager                      (Lifetime.Scoped)
    LightingAndVFXController          (Lifetime.Scoped)
    FlagSystem                        (Lifetime.Scoped)
    NarrativeDirector                 (Lifetime.Scoped)
    SaveSystem                        (Lifetime.Scoped)
    TerminalSystem                    (Lifetime.Scoped)
    DialogueSystem                    (Lifetime.Scoped)
    IDialogueTransport                (Lifetime.Scoped → OllamaHttpTransport; MockTransport in tests)
    DialogueLogic                     (Lifetime.Scoped, plain C#)
```

`[SerializeField]` remains valid for **inspector-bound configs** (the `CFG-*` ScriptableObjects: `OxygenConfig`, `AgitationConfig`, `FlagDefinition`, `LlmTransportConfig`, …) and for **prefab references** the scope itself holds. Cross-system runtime references (e.g., `DialogueSystem` needing `FlagSystem`, `GameManager`, `OxygenSystem`, `AgitationSystem`) come through constructor injection or `[Inject]` properties resolved by the scope, not through nine `[SerializeField]` slots on the consumer.

For the PoC, the scope does not need to survive between scenes via `DontDestroyOnLoad`, unless a main menu is added. The legacy "GameSystemsRoot prefab" pattern is superseded by this scope; the identifier survives only as a historical anchor in older drafts of this document.

## Scene Structure

### Recommended option for the PoC

A single playable scene:

```text
SCN_PoC_C7
```

Contents:
- Initial interior.
- Corridor.
- Maintenance.
- Airlock.
- Exterior.
- Antenna.
- Final.

Advantages:
- Less technical overhead.
- Fewer persistence problems.
- Faster iteration in Unity.
- Easy testing of the full flow.

### Optional scenes

If a menu is needed:

```text
SCN_Boot
SCN_MainMenu
SCN_PoC_C7
```

For the first PoC, `SCN_MainMenu` can be omitted. A restart button on the failure screen is enough.

## ScriptableObject Usage

Use ScriptableObjects for data that the team wants to tune without touching code.

### OxygenConfig

Data:
- `maxOxygen`
- `baseDrainRate`
- `warningThreshold`
- `criticalThreshold`
- `exteriorDrainMultiplier`
- `refillStationAmount`

Use:
- Assigned to `OxygenSystem`.
- Enables fast balance.

### AgitationConfig

Data:
- `maxAgitation`
- `runningIncreasePerSecond`
- `calmDecreasePerSecond`
- `interiorDecreasePerSecond`
- `exteriorIncreasePerSecond`
- `tenseThreshold`
- `panicThreshold`
- `tenseOxygenMultiplier`
- `panicOxygenMultiplier`

Use:
- Assigned to `AgitationSystem`.

### PresenceEventDefinition

Data:
- `eventId`
- `cooldown`
- `agitationAmount`
- `audioCue`
- `vfxCue`
- `lightCue`
- `duration`
- `canRepeat`

Use:
- Assigned to presence triggers.
- Executed by `PresenceDirector`.

### ObjectiveDefinition

Data:
- `objectiveId`
- `displayText`
- `nextObjectiveId`

Use:
- Assigned to `ObjectiveSystem`.
- Optional for the PoC; can also be hardcoded since there are only 5 steps.

### When not to use ScriptableObjects

Do not create ScriptableObjects for everything. Avoid them if:
- The data exists only once.
- It will not be balanced.
- They add setup overhead.
- A temporary hardcode speeds up validation without risk.

## Game State Flow

```text
Boot
  -> Intro
  -> Playing
      -> AirlockTransition
      -> Playing
      -> Completed
      -> Failed
  -> Paused
      -> Playing
  -> Loading           # entered when SaveSystem.Load is invoked
      -> Playing       # exits to Playing after restore completes and SaveRestored is published
```

### Boot

Initializes references and configures systems.

### Intro

Shows initial control, HUD, and objective. Can last only a few seconds.

### Playing

Main state. Movement, oxygen, agitation, interactions, and presence are active.

### AirlockTransition

Brief state for pressurization/depressurization.

Optional:
- Block movement.
- Switch audio.
- Switch zone to `Exterior` or `Interior`.

### Completed

Triggered when inserting the energy module and playing the PoC ending.

### Failed

Triggered when oxygen reaches zero or a critical condition kills the player.

### Paused

Pauses gameplay. May be omitted if the PoC has no pause menu.

### Loading

Entered when `SaveSystem.Load` is invoked, either from a fresh launch with an existing autosave or from a manual reload.

- During `Loading`, all gameplay systems gate their `Update` and event publishing on `State == Playing`, so no system raises events while restore is in progress.
- `SaveSystem` walks each saveable system in any order, calls `RestoreState(dto)` on each via `ISaveable<TDto>`, then publishes `EVT-save-restored` exactly once.
- After `EVT-save-restored`, `GameManager` transitions back to `Playing`.

### Minimum checkpoint

Superseded by `SYS-SAVE` — see TDD `§SaveData`.

The checkpoint mechanism is now `SYS-SAVE`. State to restore is documented in TDD `§SaveData` and the per-system DTOs declared alongside each `ISaveable<TDto>` implementation. The save trigger is the airlock save-point flag (`FlagDefinition.isSavePoint = true`), wired per ADR-0005. Rationale lives in ADR-0005; the SDD does not duplicate it.

Prior text described a struct sketch; the canonical model is now the DTO snapshot pattern documented in ADR-0005.

## PoC Gameplay Flow

1. `GameManager` enters `Intro`.
2. `ObjectiveSystem` shows "Restore power in C-7".
3. `GameManager` enters `Playing`.
4. `OxygenSystem` starts consuming oxygen.
5. `PlayerController` reports movement and running.
6. `AgitationSystem` adjusts agitation.
7. `OxygenSystem` applies the agitation multiplier.
8. Triggers call `PresenceDirector`.
9. `PresenceDirector` runs audio/lights/glitches and raises agitation.
10. `EnvironmentSystem` switches to `Exterior` when leaving the airlock.
11. `OxygenSystem` increases drain due to exterior.
12. The player picks up the module.
13. `ObjectiveSystem` advances the objective.
14. The player inserts the module in maintenance.
15. `GameManager` enters `Completed`.

## Recommended Folder Structure

```text
src/Assets/
  LastBreath/
    Art/
    Audio/
    Materials/
    Prefabs/
      GameSystems/
      Interactables/
      Player/
      Presence/
      UI/
    Scenes/
    ScriptableObjects/
      Configs/
      PresenceEvents/
      Objectives/
    Scripts/
      Core/
      Gameplay/
      Interactions/
      Presentation/
      ScriptableObjects/
      Utilities/
```

## Key Prefabs

### Player

Components:
- `PlayerController`
- Collider / CharacterController
- Sprite renderer or visual root
- Interaction detector

### LifetimeScope (VContainer composition root)

A single `LifetimeScope` subclass (`GameLifetimeScope`) per playable scene holds the cross-system wiring. See `§Managers → Usage rule` for the registration list and ADR-0009 §DI for the rationale. The scope is the only class permitted to call `FindObjectOfType` (in `Awake`, for engine-bridge bootstrap such as scene-root cameras); systems themselves receive dependencies via constructor injection or `[Inject]` properties.

Historical note: earlier drafts called this prefab `GameSystemsRoot`. That name is retained in older session logs and plan documents but is **not** the live identifier — `GameLifetimeScope` is.

### PresenceTrigger

Components:
- Trigger collider.
- Reference to `PresenceEventDefinition`.
- Flags: `triggerOnce`, `requiresObjective`, `delay`.

### PresenceAgitationTrigger

Suggested single use:
- Fire `PRES_EXTERIOR_BEACON` when agitation exceeds 70 while the player is in `Exterior`.
- If it does not fire before the module is picked up, use a `PresenceTrigger` on the return path as a fallback.
- Do not use `Update`; listen to `AgitationSystem.OnAgitationChanged`.

### Interactables

Prefabs:
- `DoorInteractable`
- `PanelInteractable`
- `OxygenStationInteractable`
- `EnergyModulePickup`
- `TerminalInteractable`

## Implementation Rules

### Per-frame updates

Only these systems should use `Update`:
- `PlayerController`
- `OxygenSystem`
- `AgitationSystem`
- `PlayerInteractor`

The rest should react via events or triggers.

### Dependencies

Preference (ADR-0009):
1. VContainer registration on the scene `LifetimeScope`, resolved by constructor injection or `[Inject]` for cross-system references.
2. Inspector `[SerializeField]` references for `CFG-*` ScriptableObjects and prefab fields the scope itself holds.
3. C# events for fan-out notifications (one publisher, many subscribers).
4. Local `GetComponent` in `Awake` for own-GameObject components.

Avoid:
- Looking up managers with `FindObjectOfType` outside the `LifetimeScope.Awake` bootstrap.
- Singletons / static `Instance` properties for any system.
- A generic global event bus.
- Coroutines hidden in many objects without control. Prefer `UniTask` + explicit cancellation tokens.

### Minimum debug

Add an overlay for development only with:
- Numeric oxygen.
- Numeric agitation.
- Current zone.
- Current objective.
- Last `presenceEventId` fired.

Temporary shortcuts allowed in `debugMode`:
- Refill oxygen.
- Force high agitation.
- Fire a test presence event.
- Restart from checkpoint.

The debug overlay is not part of the final experience but is part of the technical scope of the PoC because it speeds up balance and internal playtest.

### Minimum manual testing

Checklist:
- Oxygen drops only in `Playing`.
- Running raises agitation.
- Agitation increases drain.
- Exterior increases drain.
- Oxygen station can be used only once.
- Presence events do not repeat if `triggerOnce`.
- Reaching zero triggers `Failed`.
- Inserting the module triggers `Completed`.

## Suggested Implementation Plan

### Phase 1: Vertical basic

- `GameManager`
- `PlayerController`
- `OxygenSystem`
- Oxygen HUD
- Scene with start and temporary end

### Phase 2: Mechanical tension

- `AgitationSystem`
- Drain multiplier
- Running and exterior affect agitation
- Simple breathing audio

### Phase 3: Interactions

- `PlayerInteractor`
- Door
- Panel
- Module pickup
- Oxygen station

### Phase 4: Presence

- `PresenceDirector`
- `PresenceTrigger`
- `PresenceAgitationTrigger` for `PRES_EXTERIOR_BEACON`
- 5 fixed ambient events
- Simple lights, audio, and glitches

### Phase 5: Flow polish

- Objectives in UI
- Airlock transition
- Time balance
- Failure/success screens

## Technical Risks

### Risk: too many systems for a PoC

Mitigation:
- Implement minimum versions first.
- Do not create interfaces except `IInteractable`.
- Hardcode objectives if it speeds things up.

### Risk: presence events hard to debug

Mitigation:
- Each event has an `eventId`.
- Optional log in debug mode.
- Triggers visible with gizmos.

### Risk: unfair oxygen balance

Mitigation:
- All main values in `OxygenConfig` and `AgitationConfig`.
- Debug commands to refill oxygen and force states.

### Risk: circular dependency between oxygen and agitation

Mitigation:
- `AgitationSystem` does not know the oxygen value.
- `OxygenSystem` only reads or receives a multiplier.
- Death is decided by `OxygenSystem` and executed by `GameManager`.

## Technical Success Criteria

The architecture works if:
- Drain can be tuned without touching code.
- A new presence event can be added from the Inspector.
- A new interactable can be added by implementing `IInteractable`.
- The full PoC can be played in a single scene.
- No central system depends on final art.
- A dev can understand the main flow in less than an hour.
