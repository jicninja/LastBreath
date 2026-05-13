---
id: ADR-0005-save-system-architecture
type: decision
status: accepted
date: 2026-05-12
related: [PLAN-004, SYS-SAVE, ADR-0004]
---

# ADR 0005: Save system as DTO snapshots, not asset serialization

## Context

The graphic-adventure model adopted in ADR-0004 implies a save system that restores *all* progression state, not just position and oxygen: flags, fired one-shot narrative cues, consumed interactables, environment zone, presence cooldowns, current objective, player position. Two patterns exist:

- **DTO snapshots**: each system implements `ISaveable<TDto>` with `CaptureState()` / `RestoreState(dto)`; a `SaveSystem` orchestrator aggregates DTOs into one root object and writes JSON. Disk format is decoupled from runtime types.
- **Hipple-style asset serialization**: runtime state already lives in ScriptableObjects (per the Hipple pattern rejected in ADR-0004); save = walk all runtime SOs and serialize their values keyed by asset GUID.

Since ADR-0004 rejected runtime-state-in-SO, this ADR locks in the matching save model.

## Decision

Adopt **DTO snapshot save** with explicit per-system `ISaveable<T>` contracts.

- `SYS-SAVE` → `SaveSystem : MonoBehaviour`, holds `[SerializeField]` references to every saveable system, wired in `GameSystemsRoot`. No `FindObjectOfType`.
- `SaveData` is a plain `[Serializable]` root class with `version`, `saveId`, `sceneName`, `timestampUtc`, and one DTO field per saveable system. Serialized via `JsonUtility` (or `Newtonsoft` if dictionaries are needed). One save file per slot.
- Each saveable system implements `ISaveable<TDto>`: `CaptureState()` returns a fresh DTO; `RestoreState(dto)` writes runtime fields **without publishing events**.
- Add `GameState.Loading` to the existing `GameState` enum. All gameplay systems gate their `Update` on `State == Playing`. Restore order is therefore non-critical; at the end of restore, `SaveSystem` publishes a single `EVT-save-restored` and transitions to `Playing`.
- Dynamic world objects (interactables, doors) implement `IPersistentInteractable` with a designer-assigned `PersistenceId : string` (stable, unique per scene). An `InteractableRegistry : MonoBehaviour` collects them via registration in `OnEnable` / `OnDisable`. `SaveSystem` serializes the registry's snapshot.
- Save points are flag-driven: `FlagDefinition.isSavePoint = true` triggers `Save("autosave")` from a `SaveSystem` subscription to `EVT-flag-changed`. No autosave-by-time.
- Migrations: a single `Migrate(SaveData)` function bumps `version` across format changes. Save format and runtime types evolve independently.

## Alternatives considered

- **Hipple-style asset serialization** ("walk all runtime SOs"). Rejected because (1) requires a GUID-keyed resolver that DTO snapshots do not need; (2) couples disk format to asset structure — renaming a SO field breaks saves silently; (3) confuses asset-pre-Play state with last-saved state in editor (the runtime-state-in-asset bug rejected in ADR-0004); (4) requires a marker convention to distinguish tuning SOs (`OxygenConfig` — never saved) from runtime SOs (`oxygen` — saved), and the distinction must be enforced manually; (5) inverse migration is harder because the source-of-truth is the asset shape, not a versioned format. Appendix documents the implementation if reversed.
- **Reflection-based auto-save** (scan all `[Saveable]` fields). Rejected: implicit, fragile under refactor, every renamed field is a silent data-loss bug.
- **Save = serialize the entire scene** (`JsonUtility.ToJson` over the hierarchy). Rejected: pulls in transform/component noise, ties save shape to scene hierarchy, defeats migration.
- **PlayerPrefs**. Rejected: not designed for structured state, no migration, no slots.

## Consequences

- **Easy:** disk format is fully under our control. Adding a runtime field to a system without saving it is one line (do not add it to the DTO). Migrations are localized in `Migrate(SaveData)`. EditMode-testable: `Capture → Restore → assert equality` per system.
- **Hard:** boilerplate scales linearly with systems — every saveable system needs its DTO and `Capture/Restore` methods. Forgetting to add a new field to the DTO causes silent state loss.
- **Accepted loss:** the "save = one line" magic of asset serialization is given up. We pay ~30 lines of DTO + capture + restore per saveable system in exchange for explicitness and migration control.
- **Mandatory tests** (per `.claude/rules/test-standards.md`):
  - `SaveRoundtrip_PerSystem_StateMatches` — EditMode, one per saveable system.
  - `SaveSchema_AllSystemsRegistered` — EditMode, fails if a system implements `ISaveable<T>` but is not referenced by `SaveSystem`.

- **Invariants** (enforced by reviewer rules added in PLAN-004):
  - During `GameState.Loading`, no system publishes events. Rule: `SAVE-NO-EVENTS-DURING-LOADING`.
  - Only `SaveSystem` writes to disk; no other system touches `File.*` or `PlayerPrefs`. Rule: `SAVE-ONLY-SAVESYSTEM-TOUCHES-DISK`.
  - `IPersistentInteractable.PersistenceId` is unique per scene and never reused after deprecation.

## Notes

Out of scope for the PoC: multi-slot UI (one autosave + one manual is enough), save thumbnails, async/background save, encryption, cloud sync, cross-scene saves (save records `sceneName` but PoC scope is one scene).

## Appendix: how Hipple-style save would look

Documented for future reference. *Not* the chosen path.

Premise: every saveable piece of state lives in a runtime ScriptableObject (per the rejected Hipple pattern in ADR-0004). A save then becomes "snapshot every runtime SO":

```csharp
[Serializable] public class HippleEntry { public string guid; public string json; }
[Serializable] public class HippleWrapper { public int version; public List<HippleEntry> entries; }

public class HippleSaveSystem : MonoBehaviour
{
    [SerializeField] private SaveRegistry _registry;   // pre-baked GUID → SO map, build-time

    public void Save(string slot)
    {
        var entries = _registry.All
            .Where(so => so is IRuntimeStateful)        // marker interface required
            .Select(so => new HippleEntry {
                guid = _registry.GuidOf(so),
                json = JsonUtility.ToJson(so)            // serializes _runtimeValue fields
            }).ToList();
        File.WriteAllText(PathFor(slot), JsonUtility.ToJson(new HippleWrapper {
            version = 1, entries = entries
        }));
    }

    public void Load(string slot)
    {
        var w = JsonUtility.FromJson<HippleWrapper>(File.ReadAllText(PathFor(slot)));
        foreach (var e in w.entries)
            if (_registry.TryResolve(e.guid, out var so))
                JsonUtility.FromJsonOverwrite(e.json, so);
    }
}
```

What this hides:

1. **GUID resolver.** At runtime, `AssetDatabase` is unavailable. The `SaveRegistry` must be pre-baked at build time (a SO listing every runtime SO with its GUID). Every new flag/cue forces a registry rebake.
2. **Marker interface.** `IRuntimeStateful` is mandatory to avoid serializing tuning configs (`OxygenConfig` → never save). Forgetting to mark a SO yields silent state loss; marking a tuning SO by mistake yields silent state corruption.
3. **Migration.** With no versioned DTO, you cannot rename or restructure SO fields without breaking saves. Renames must preserve field name with `[FormerlySerializedAs]`. Removing a field requires a custom migration step that operates on raw JSON.
4. **Asset-state-in-editor.** Without manual `OnEnable` reset (see ADR-0004 Appendix), running Save → exit Play → start Play sees the SOs *already* in the saved state. The "load on demand" flow becomes "load to overwrite an already-mutated state."

For graphic-adventure scope (dozens of flags, slow schema churn) the model is tractable. For frequent refactoring or systems with non-trivial DTOs (interactable registry, nested cooldown maps), the explicit DTO model wins on every axis except first-day setup speed.
