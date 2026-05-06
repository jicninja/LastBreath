# Last Breath - GDD PoC

## PoC Goal

Build a 3 to 5 minute playable experience that demonstrates the core fantasy of *Last Breath*: explore a hostile space station while oxygen runs out, the character's anxiety accelerates the danger, and an invisible presence alters the environment without ever appearing.

The PoC must validate tension, atmosphere, and simple decision-making. It does not aim to validate combat, extensive narrative, or complex systems.

## High Concept

*Last Breath* is a 2.5D HD adventure game of exploration and psychological horror in which the player must cross a damaged section of a space station to retrieve an energy module before running out of oxygen. The main threat is unseen: an incomprehensible presence manipulates lights, sounds, and objects, causing agitation and making breathing the most important resource.

## Design Pillars

### 1. Oxygen is time, tension, and decision

Oxygen is not just a health bar. It is the dramatic clock of the scene. Every action must feel weighed: push forward, investigate, hide, or fall back to a safe zone.

### 2. The threat is never visually confirmed

The presence does not appear on screen. Its power lies in what it causes: interference, impossible sounds, light changes, doors that fail, wrong reflections, and objects that move when the player is not looking.

### 3. Solitude must feel playable

The station must communicate abandonment. Few characters, little interface, few interactive elements. Every noise or environmental shift matters because there is no excess of stimuli.

### 4. Exploration with clear risk

The player must always understand the immediate objective but never feel safe executing it. The space exterior is more dangerous: less margin, more drain, muffled sound, and greater exposure.

### 5. Minimal scope, high impact

The PoC must be built from a small number of reusable systems: oxygen, agitation, presence triggers, simple interactions, and two connected zones.

## Core Gameplay Loop

1. The player receives a simple objective.
2. Explores a closed zone with limited oxygen.
3. Interacts with objects to open the way or gather information.
4. The presence alters the environment and increases agitation.
5. Agitation accelerates oxygen consumption.
6. The player decides whether to push, calm down, or fall back.
7. Completes the objective and returns to a safe zone before running out of air.

## Main Mechanics

### Oxygen

Function:
- Main resource of the PoC.
- Drops continuously over time.
- Drops faster if the character is agitated.
- On reaching zero, the player collapses and restarts from the last checkpoint.

Suggested rules for the PoC:
- Base duration: 4 minutes at normal drain.
- Initial oxygen: 100%.
- Normal drain: 0.4% per second.
- Agitated drain: between 0.7% and 1.2% per second.
- Feedback: breathing, helmet fog, UI pulse, muffled audio.
- Values subject to playtest iteration (see Validation section).

Minimal implementation:
- A circular or bar oxygen indicator.
- Drain states: normal, agitated, recovering.
- Alerts at 50%, 25%, and 10%.

Checkpoints:
- A single checkpoint when activating the airlock (step 4 of the flow).
- Before the airlock: restart from the cabin.
- After the airlock: restart from the interior side of the airlock with 70% oxygen and low agitation.

### Agitation

Function:
- Represents fear, panic, and physical strain.
- Rises with presence events, running, being outside, or staying in the dark.
- Drops if the player stays still in relatively safe zones.

Suggested rules:
- Internal scale 0 to 100.
- 0-39: stable breathing.
- 40-69: increased oxygen drain, louder breathing audio.
- 70-100: light visual interference, slightly heavier controls, high drain.

Actions that raise agitation:
- Running.
- Hearing nearby knocks.
- Seeing lights go out in sequence.
- Activating a door that does not respond.
- Going outside.

Actions that reduce agitation:
- Staying still for 3 seconds **inside a marked safe zone** (lit station interior). Does not reduce inside the airlock or the exterior.
- Closing a hatch between the player and an altered area.
- Using a breathing station once.

Visualization:
- Agitation is **not shown as a bar or number**. It is communicated only through audible breathing, helmet fog, vignette, and the oxygen HUD pulse.
- The player must read their state from the character's body, not from a UI.

Design note:
Agitation should pressure, not over-punish. Avoid heavy loss of control. Horror must come from making the wrong call under pressure, not from fighting the input.

### Invisible Presence

Function:
- A system of environmental events that creates tension.
- Does not physically chase the player in the PoC.
- Has no 3D model or visible animation.

Event types:
- Audio: metallic knocks, radio whispers, breathing that is not the player's.
- Light: flickers, brief blackouts, lights that point at a door.
- Space: objects that change position off-camera.
- Interface: small glitches in the HUD or radio.
- Interaction: a door takes too long to open, a panel resets.

Suggested rules:
- Events controlled by triggers or simple thresholds, not complex AI.
- Each event has a pacing goal: anticipate, scare, block, or push.
- No visual jumpscare with a monster.
- The presence never explains its rules.
- `PRES_EXTERIOR_BEACON` must fire from agitation >70 while the player is outside. If the player does not reach that threshold before grabbing the module, fire it as a fallback at the start of the return trip.

Fixed list for the PoC:

| ID | Moment | Effect | Purpose |
| --- | --- | --- | --- |
| `PRES_CORRIDOR_LIGHTS` | Corridor C-7 | Lights flicker toward the door, metallic knock, flashlight fails for 1 second | Show that the environment reacts |
| `PRES_AIRLOCK_BREATH` | Airlock | Radio plays the player's own breathing with delay | Anticipate the exit to the exterior |
| `PRES_EXTERIOR_BEACON` | Exterior with agitation >70; fallback when the return starts | A beacon goes out and a hatch appears open when looking back | Make the exterior feel exposed |
| `PRES_ANTENNA_BLACKOUT` | Antenna panel | 2-second total blackout and a voice on the radio | PoC climax |
| `PRES_RETURN_DOOR` | Return to the airlock | Door takes 6 seconds and nearby knocks are heard | Turn waiting into a risk decision |

If an extra event competes for production time with these five, cut the extra event.

### Exploration

Function:
- The player navigates compact spaces, reads the environment, and solves simple interactions.
- Exploration should have small but meaningful decisions.

PoC interactions:
- Open/close hatches.
- Activate panels.
- Pick up an energy module.
- Use a limited breathing station.
- Read a short terminal message or audio log.

Structure:
- Station interior: safer, more narrative.
- Airlock: transition and emotional point of no return.
- Space exterior: more dangerous, higher drain, lower visibility.

Anti-block rule:
- If the player goes more than 45 seconds without progressing the objective, trigger a minimal diegetic hint.
- The hint must be contextual: a subtle panel flicker, a noise from the correct door, a short radio line, or a highlight visible only with the flashlight.
- Do not add big arrows, long tutorials, or explanatory pauses.
- The goal is to avoid being blocked in playtest, not to solve the scene for the player.

### Lighting

Premise: the station's power is down. There is only dim emergency lighting. That is why the player must restore power.

Per-zone regimen:
- **Station interior**: dim ambient red emergency light. Allows navigation but not reading details. Interactive objects are not visible at a glance without the flashlight.
- **Airlock**: practically dark. The flashlight becomes essential.
- **Space exterior**: total darkness outside the flashlight cone and the walkway beacons. If the presence kills a beacon, that stretch depends on the helmet cone.

The presence manipulates this lighting:
- Flickers the emergency lights.
- Kills exterior beacons.
- Makes the flashlight fail momentarily.

### Flashlight

Function:
- Main tool to **discover interactables** in an environment lit only by emergency light.
- Without the flashlight, panels, terminals, the energy module, and the breathing station are hard or impossible to locate.
- The flashlight is mounted on the helmet: the cone aims wherever the character looks.

PoC rules:
- No battery. Not managed as a resource.
- On/off toggle on a single input.
- Fixed light cone (no narrow/wide beam).
- Interactables visually highlight only when inside the cone (subtle edge highlight, not exaggerated glow).
- The presence may turn off the flashlight for 1-3 seconds as a punctual event. The player cannot reactivate it during those seconds.

Why it does not add a third resource:
- No battery, so it does not compete with oxygen or agitation.
- The cost of using it is **time**: aim the cone, sweep the room, find the object. That time is paid by oxygen still dropping.
- Keeps the loop on two coupled resources.

Design decision:
- The player never controls environmental lights, only the helmet light. Reinforces the idea that the presence manipulates the world and you only have your own cone.

## First Playable Scene

### Name

"Module C-7: Power Outage"

### Target duration

3 to 5 minutes.

### Player goal

Retrieve an energy module from an exterior antenna and partially restore power to corridor C-7.

### Minimal map

1. Cabin / initial safe zone.
2. Corridor C-7.
3. Maintenance room.
4. Airlock.
5. Station exterior.
6. Antenna panel.
7. Return to the maintenance room.

### Scene flow

#### 1. Start in safe zone

The player wakes up in a small emergency cabin. Dim red emergency light, low alarm, and oxygen at 100%. A broken radio plays an incomplete line: "Do not open if you hear your own voice."

The player turns on the helmet flashlight to find the cabin door. This is the first lesson: **without the flashlight you cannot see interactables**.

On-screen objective: "Restore power in C-7."

Purpose:
- Establish tone.
- Give control.
- Teach the flashlight as a search tool.
- Show oxygen without immediate extreme pressure.

#### 2. Corridor C-7

The player exits to the corridor. Only red emergency light. They must sweep with the flashlight to find the control panel. A door at the end has no power. The panel indicates that the module must be reset from the exterior.

Presence event:
- The corridor emergency lights flicker from back to front.
- A knock is heard on the opposite side of the wall.
- The flashlight briefly fails when the cone passes over a closed hatch.
- Agitation rises moderately.

Purpose:
- Teach that the environment reacts.
- Teach that the flashlight can also fail.
- Give clear direction: find exterior access.

#### 3. Maintenance room

The player finds a breathing station with a single charge and a terminal with a brief message.

Suggested message:
"The antenna responds, but someone is sending the signal back from inside."

Decision:
- Use the station now to recover oxygen.
- Save it for the return.

Visibility:
- The station must be on the player's forced path, lit differently from the rest, with a clear prompt: "Refill oxygen (1 use)".
- If the player misses it, the most important decision of the PoC is lost.

Purpose:
- Introduce simple resource management.
- Deliver a small narrative beat without breaking pacing.

#### 4. Airlock

The player activates the airlock. The camera tightens, sound muffles, and breathing comes to the front. **This is where the only PoC checkpoint is saved.**

Presence event:
- The radio plays the player's breathing with half a second of delay.
- Before opening the exterior door, the player must hold an "Open airlock" input while the echo of their own breathing plays. Makes the player complicit in breaking the rule "Do not open if you hear your own voice".
- The exterior door takes longer than usual to open.

Purpose:
- Build anticipation before the exterior.
- Raise agitation without showing a threat.
- Pay off the radio callback from the start.

#### 5. Space exterior

The player walks along an exterior walkway toward the antenna panel. Visibility is low, particles drift, and movement is slower.

Rules:
- Oxygen drains faster.
- Agitation rises slowly while the player is outside.
- No recovery station.

Presence event:
- A beacon goes out as the player approaches.
- Looking back, a hatch that was closed appears open.

Purpose:
- Make the player want to finish the task and return.

#### 6. Antenna panel

The player removes the energy module. As they do, **everything goes dark for 2 seconds: walkway beacons and the helmet flashlight**. Absolute black.

Presence event:
- Only the player's own voice is heard on the radio saying: "Don't come back yet," over the duplicated breathing.
- When the flashlight returns, one walkway beacon stays out.
- Agitation rises hard.
- Objective triggers: "Return to maintenance".

Purpose:
- PoC climax.
- Maximum impact by removing the only light source the player controls.
- Turn the return into a tense sequence.

#### 7. Return

The player goes back to the airlock. The door takes time to pressurize. Oxygen is low or medium depending on prior choices.

Resolution:
- Insert the module in the maintenance room.
- Power partially returns.
- The corridor lights up.
- In the exterior window nothing is visible, but a knock is heard from outside.
- Cut to black.

Purpose:
- Strong close without revealing the presence.
- Confirm that the threat continues.

## Player Experience

### Tension

Tension must build in layers:
- First, the player understands oxygen is dropping.
- Then, they discover that fear accelerates the problem.
- Finally, they learn the presence can alter the environment exactly when calm is most needed.

### Pacing

Recommended structure:
- Minute 0-1: control, objective, safe exploration.
- Minute 1-2: first strong event, decision about the resource.
- Minute 2-3: exit to the exterior and rising risk.
- Minute 3-4: module retrieval and return under pressure.
- Minute 4-5: resolution and unsettling close.

### Key feelings

The player should feel:
- "I have to move, but I do not want to get agitated."
- "I saw nothing, but something was there."
- "Outer space is not freedom, it is exposure."
- "Going back to the station does not mean I am safe."

## PoC Scope

### Includes

- One controllable character.
- One compact linear scene.
- One interior zone and one exterior zone.
- Basic oxygen system.
- Basic agitation system.
- Helmet flashlight with toggle (no battery).
- Per-zone ambient emergency lighting.
- 5 fixed presence events via triggers.
- 3 to 5 simple interactions.
- One breathing station with limited use.
- Basic ambient audio.
- Minimal oxygen HUD.
- One checkpoint at the airlock.
- Pause with frozen time (Resume / Quit).
- Subtitles for key sound events (knocks, whispers, voice on radio).
- One closed PoC ending.

### Does not include

- Combat.
- Complex inventory.
- Dialogue trees.
- Visible enemy.
- Chase AI.
- Multiple endings.
- Save/load.
- Procedural systems.
- Long cutscenes.
- Multi-step puzzles.
- Extensive lore.

## Concrete Gameplay Examples

### Situation 1: The breathing station

The player reaches maintenance with 68% oxygen. Sees a breathing station with a single charge. If used now, oxygen rises to 90%, but there is no help on the way back from outside. If saved, the player enters the exterior with less margin but can recover on return.

Simple decision, clear consequence.

### Situation 2: Running through the corridor

The player runs to save time. Reaches the airlock sooner, but agitation rises to 55 and drain increases. Breathing gets louder and the HUD pulses faster. The player learns that speed and safety are not the same.

### Situation 3: Blackout outside

When removing the module, the beacons and the helmet flashlight go off. Absolute black for 2 seconds. No enemy appears. Only the duplicated breathing on the radio is heard. When the light returns, a beacon is out and the way back feels longer.

The player feels they lost the only tool they controlled. Tension without revealing the threat.

### Situation 4: Slow door

Returning to the airlock, the door takes 6 seconds to open. The player can do nothing but wait and listen to metallic knocks. Agitation rises, oxygen drops faster, and the player understands that danger is also in the wait.

### Situation 5: False safety

After inserting the module, the lights return. The music drops. The player seems safe. Then a knock is heard from the exterior window, from the impossible side. Cut to black.

The PoC ends in mystery, not in explanation.

## Minimum Audio

Audio is the main vehicle of the fantasy. Closed list of assets required for the PoC:

Player breathing:
- Stable (agitation 0-39).
- Accelerated (40-69).
- Heavy / at the limit (70-100).

Character and suit:
- Helmet fog (short loop).
- Protagonist voice recorded for the line "Don't come back yet".

Presence:
- Metallic knocks (2 variants).
- Radio whispers (2 variants).
- Echo of own breathing with delay (airlock and exterior).

Ambience:
- Cabin low alarm (loop).
- Station interior ambience.
- Muffled exterior ambience.

Total target: ~12 assets. If something must be cut, cut ambience before presence.

## Production Priorities

### First playable cut

Before producing the full scene, validate a grey-box version with:
- Corridor.
- Airlock.
- Short exterior.
- Antenna panel.
- Return to maintenance.
- Oxygen, agitation, flashlight, breathing station, and 2 presence events.

Temporarily cut terminals, audio logs, fine glitches, pause, and extra animations if they delay this first playable pass.

### Priority 1

- Character control.
- Oxygen timer.
- Clear HUD.
- Fully navigable scene.
- Functional main objective.

### Priority 2

- Agitation tied to drain.
- Trigger-based ambient events.
- Breathing station.
- Breathing and knock audio.

### Priority 3

- Visual glitches.
- Narrative details.
- Lighting polish.
- Extra animations.

## Success Criteria

The PoC works if:
- 4 of 5 players understand the objective in less than 30 seconds.
- 4 of 5 players complete the scene between 3 and 5 minutes.
- No player is blocked for more than 45 seconds without knowing what to do.
- At least 3 of 5 players hesitate before using or saving the breathing station.
- At least 4 of 5 players perceive that the presence is active even though it never appears.
- At least 4 of 5 players describe the exterior as more dangerous than the interior.
- After finishing, at least 3 of 5 players want to know what the presence was.

## Validation

Minimum playtest plan:
- 5 players, no prior guidance, individual sessions.
- Observer does not intervene unless the player is fully blocked.

Metrics to record:
- Time to understand the objective.
- Maximum time blocked without progress.
- % oxygen when inserting the module.
- Whether they used the breathing station and at what point.
- Reaction to the climax (blackout + voice on radio).
- Whether they finished in 3-5 min or required a restart.

Decisions to iterate based on results:
- Drain rates (0.4% / 0.7-1.2% per second).
- Agitation thresholds (40 / 70).
- Wait duration on the return door (6 s).
