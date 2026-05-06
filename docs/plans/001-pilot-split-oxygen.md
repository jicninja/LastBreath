# Plan 001 - Pilot: split the Oxygen system into the agentic-first format

## Context

The repo already has three monolithic docs (`last-breath-poc-gdd.md`, `last-breath-poc-sdd.md`, `last-breath-poc-tdd.md`) and a new skeleton:

- Root `AGENTS.md` with roles and rules.
- `.claude/agents/` with 6 roles, `.claude/rules/` with 4 rule files.
- `docs/registry/architecture.yaml` with stable IDs (PILLAR-01..05, MECH-*, SYS-*, CLASS-*, CFG-*, EVT-*).
- `docs/engine-reference/unity/` with VERSION, best practices, and deprecated APIs.

The next step is to **validate the split format with a single pilot system** before migrating the rest. We pick **Oxygen** because it is the heart of the PoC (PILLAR-01) and it touches several systems (SYS-OXYGEN, SYS-AGITATION, SYS-ENVIRONMENT, SYS-HUD, SYS-AUDIO).

## Goal

Produce, for the Oxygen domain only, the following new files following the format defined in `.claude/rules/design-docs.md`:

```
docs/
  gdd/
    mechanics/
      oxygen.md             # MECH-OXIGENO
  sdd/
    systems/
      oxygen-system.md      # SYS-OXYGEN
  tdd/
    classes/
      OxygenSystem.md       # CLASS-OxygenSystem
    configs/
      OxygenConfig.md       # CFG-OXYGEN
  glossary.md               # canonical terms
  index.md                  # root index: id -> path
```

The three legacy docs are NOT deleted or edited in this plan. They are only referenced. Migrating the rest comes in later plans (002-agitation, 003-presence, etc.) if the format works.

## Non-goals

- Do not touch `src/` or C# code.
- Do not edit legacy GDD/SDD/TDD (read-only).
- Do not migrate other systems yet.
- Do not create hooks, custom skills, or CI.

## Steps

### Step 1 - Glossary and root index

**File:** `docs/glossary.md`

- No frontmatter (it is an index, not memory).
- Table format: `term | canonical definition | forbidden synonyms`.
- Terms to include: oxygen, agitation, presence, airlock, corridor, panel, flashlight, interior, exterior, breathing-station, presence-event, safe-zone.
- One line per term.

**File:** `docs/index.md`

- No frontmatter.
- Table: `ID | Type | Path | Status`.
- For now, only Oxygen-domain entries + links to the three legacy docs with a note "legacy, split in later plans".

### Step 2 - Mechanic doc (GDD layer)

**File:** `docs/gdd/mechanics/oxygen.md`

Frontmatter:
```yaml
---
id: MECH-OXIGENO
type: mechanic
layer: gdd
status: poc
related: [PILLAR-01, PILLAR-04, SYS-OXYGEN, CFG-OXYGEN]
---
```

Structure (extract from the legacy GDD lines around "Oxygen" + "Breathing station" in "Concrete Examples"):

1. **One-line pitch** - what the player feels.
2. **Pillars implemented** - links to PILLAR-01, PILLAR-04 with a short quote.
3. **Observable behavior** - what they see, hear, feel. No numbers or formulas.
4. **Player decisions** - what tradeoffs it introduces.
5. **Playable examples** - short scenarios (breathing station, running through the corridor, etc.).
6. **References** - link to `docs/sdd/systems/oxygen-system.md` and to the legacy GDD anchor.

Rules: no balance numbers (those live in SDD/TDD), no C# class names.

### Step 3 - System doc (SDD layer)

**File:** `docs/sdd/systems/oxygen-system.md`

Frontmatter:
```yaml
---
id: SYS-OXYGEN
type: system
layer: sdd
status: poc
related: [MECH-OXIGENO, CLASS-OxygenSystem, CFG-OXYGEN, SYS-AGITATION, SYS-ENVIRONMENT, SYS-HUD]
---
```

**Mandatory** structure (defined in `.claude/rules/design-docs.md`):

1. **Responsibility** - one sentence. "Hold and publish the player's current oxygen as a function of zone and agitation."
2. **Inputs** - events it subscribes to (EVT-zone-changed, EVT-agitation-changed) + data it reads (CFG-OXYGEN).
3. **Outputs** - events it publishes with payload (EVT-oxygen-changed, EVT-oxygen-depleted).
4. **Invariants** - `current >= 0`, `current <= max`, `current` changes only in `Update`.
5. **Acceptance** - verifiable bullets. Examples:
   - On entering `exterior`, drain per second rises within <=1 frame.
   - When agitation >= 0.8, the drain multiplier applies on the next Update.
   - On reaching 0, fires EVT-oxygen-depleted exactly once.
   - Interacting with the breathing station raises oxygen up to `max` with no overshoot.
6. **Implementation notes** - which decisions stay open for the TDD.
7. **References** - links to `docs/tdd/classes/OxygenSystem.md`, `docs/tdd/configs/OxygenConfig.md`, the registry, and the legacy SDD anchor.

### Step 4 - Class doc (TDD layer)

**File:** `docs/tdd/classes/OxygenSystem.md`

Frontmatter:
```yaml
---
id: CLASS-OxygenSystem
type: class
layer: tdd
status: poc
related: [SYS-OXYGEN, CFG-OXYGEN]
---
```

Structure:

1. **Expected path in `src/`** - `src/Assets/_Project/Scripts/Gameplay/Oxygen/OxygenSystem.cs`.
2. **Type** - `MonoBehaviour`.
3. **Dependencies** - `[SerializeField]` fields and why.
4. **Public API** - properties, methods, events. Table `name | type | purpose`.
5. **Update loop** - pseudocode or snippet of the per-frame computation. Reuse the legacy TDD code.
6. **Drain formula** - copy from the legacy TDD ("Oxygen formula" section).
7. **Required tests** - list of EditMode/PlayMode tests. Map 1:1 with the SDD acceptance criteria.
8. **References** - legacy TDD with anchor.

### Step 5 - Config doc (TDD layer)

**File:** `docs/tdd/configs/OxygenConfig.md`

Frontmatter:
```yaml
---
id: CFG-OXYGEN
type: config
layer: tdd
status: poc
related: [SYS-OXYGEN, CLASS-OxygenSystem]
---
```

Structure:

1. **Type** - `ScriptableObject`.
2. **Expected path** - `src/Assets/_Project/ScriptableObjects/OxygenConfig.asset` and script in `src/Assets/_Project/Scripts/Gameplay/Oxygen/OxygenConfig.cs`.
3. **Fields** - table `name | type | range | default | description`. Extract from the legacy TDD.
4. **Validations** - `OnValidate` clamps.
5. **How to create the asset** - menu `Create > LastBreath > OxygenConfig`.
6. **References** - legacy TDD with anchor.

### Step 6 - Verification

- Every new file has valid frontmatter.
- Every declared `id` exists in `docs/registry/architecture.yaml`.
- Every cross-link resolves to a real file or anchor.
- `docs/index.md` lists all new files.
- `docs/glossary.md` covers the terms used.
- No legacy file was modified.

Quick check command (run at the end):
```bash
grep -rh "^id:" docs/gdd/mechanics docs/sdd/systems docs/tdd/classes docs/tdd/configs | sort
grep -E "^\s*-?\s*id:" docs/registry/architecture.yaml | sort
```
The IDs declared in the new docs must all appear in the registry.

## Success criterion

After running the plan, an agent that receives the task "touch OxygenSystem" can:

1. Read root `AGENTS.md`.
2. Read `docs/registry/architecture.yaml` and filter by SYS-OXYGEN.
3. Load **only** the 4 Oxygen-domain docs (mechanic, system, class, config) - total < 400 lines.
4. Have everything they need without opening the three legacy docs.

If that works, the format is viable and can be repeated for Agitation (plan 002), Presence (003), etc.

## For the agent that executes this plan

- Active role: **systems-designer** for the split SDD, **gameplay-programmer** for the split TDD, **game-designer** for the split GDD. No role touches code in this plan.
- Before starting, read:
  - Root `AGENTS.md`.
  - `.claude/rules/design-docs.md`.
  - The full `docs/registry/architecture.yaml`.
  - Legacy GDD sections "Oxygen", "Main Mechanics > Oxygen", "Concrete Gameplay Examples".
  - Legacy SDD section "OxygenSystem".
  - Legacy TDD sections "OxygenConfig", "OxygenSystem", "Oxygen formula".
- Do not invent new IDs. If you need one, stop and propose it first.
- Do not edit legacy docs.
- Do not create files outside the paths listed in this plan.
- When done, leave a brief "test plan" at the end of this same file (under "Results") with: created files, IDs used, broken links detected (if any).

## Results

_(fill in when executing the plan)_
