---
id: PROCESS-ADD-MECHANIC
type: reference
layer: process
status: active
related: [PROCESS-UNITY-PATTERNS, GAMEPLAY-CODE, TEST-STANDARDS]
---

# Adding a mechanic

How to add a new mechanic to Last Breath. Read end-to-end the first time. After that, jump to the section you need.

## 1. When to add a mechanic vs. fold into an existing one

Use this decision tree before opening any file. Stop at the first branch that matches.

- Does the player have a *verb* against it? **No** -> it is a system, not a mechanic. Stop. Document it under `docs/sdd/systems/` only and skip the rest of this recipe.
- Does it have *state with rules* (formulas, thresholds, transitions)? **No** -> it is a sub-rule of an existing mechanic. Add a clause to that mechanic's section instead of creating a new doc.
- Does it map 1:1 to a single pillar with no rules of its own? **Yes** -> it is pillar prose, not a mechanic. Extend the relevant `PILLAR-*` description.
- Otherwise -> continue with the recipe below.

If you reached this line, you have a real mechanic. Proceed to Section 2.

## 2. ID convention

IDs mirror `docs/registry/architecture.yaml`. They are immutable: once published an ID is never renamed; if the thing dies, set `status: deprecated` and keep the entry.

| Layer | Prefix | Example | Casing |
|-------|--------|---------|--------|
| Mechanic (GDD) | `MECH-` | `MECH-FOO` | UPPERCASE, English |
| System (SDD) | `SYS-` | `SYS-FOO` | UPPERCASE, English |
| Class (TDD) | `CLASS-` | `CLASS-FooSystem` | PascalCase suffix |
| Config (TDD) | `CFG-` | `CFG-FOO` | UPPERCASE, English |
| Event | `EVT-` | `EVT-foo-changed` | kebab-case suffix |

Rules:
- One mechanic, one `MECH-*`. One system, one `SYS-*`. A mechanic may be implemented by several systems; cross-link via `implemented_by` in the registry.
- New IDs must be added to `architecture.yaml` in the same plan that introduces them. Inventing an ID in a doc without registering it is a process error.
- ASCII only. No accents, no Unicode punctuation.

## 3. GDD section template

File: `docs/gdd/mechanics/{{name-kebab}}.md`. Frontmatter is mandatory; the body uses this skeleton.

```markdown
---
id: MECH-{{NAME}}
type: mechanic
layer: gdd
status: poc
related: [PILLAR-{{NN}}, SYS-{{NAME}}, CFG-{{NAME}}]
---

### {{Name}}

Function:
- ...

Suggested rules:
- ...

Visualisation:
- ...

Design note:
...
```

Rules for the GDD layer:
- No balance numbers, no formulas. Those live in SDD/TDD.
- No C# class names. Use the canonical glossary term.
- Keep the four blocks. If one is empty, write `- (none)` rather than dropping the heading.

## 4. SDD system template

File: `docs/sdd/systems/{{name-kebab}}.md`. The six sections below are mandatory and ordered.

```markdown
---
id: SYS-{{NAME}}
type: system
layer: sdd
status: poc
related: [MECH-{{NAME}}, CFG-{{NAME}}]
---

# {{Name}}System

## Responsibility
One sentence.

## Inputs
- Events listened to: ...
- Data read: ...

## Outputs
- Events published: ...

## Invariants
- What can never happen.

## Acceptance
- Verifiable list of observable behaviour.

## Notes
Only what does not fit above.
```

Rules for the SDD layer:
- "Responsibility" is one sentence. If you need "and also", split into two systems.
- Every published event listed under "Outputs" must exist in `architecture.yaml` with the same ID.
- "Acceptance" bullets must be testable from outside the system (observable behaviour, not implementation details).

## 5. TDD class template

File: `docs/tdd/classes/{{Name}}System.md`. One file per `CLASS-*`.

````markdown
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
public class {{Name}}System : MonoBehaviour { ... }
```

## Public API
- Methods, events, properties.

## Dependencies
- Serialised refs.
- Subscriptions.

## Test plan
- EditMode tests for formulas.
- PlayMode smoke for events.
````

Rules for the TDD layer:
- The class signature in the doc must match the C# file once it exists. If they drift, the doc is wrong by convention.
- The "Test plan" bullets map 1:1 to entries under `tests/EditMode/` and `tests/PlayMode/`.
- A `CFG-*` config gets either its own `docs/tdd/configs/{{Name}}Config.md` or an anchor inside this same TDD doc (`#{{name-kebab}}config`).

## 6. Registry block template

Paste this into `docs/registry/architecture.yaml` under the matching top-level keys (`mechanics`, `systems`, `configs`). Do not invent new top-level keys.

```yaml
mechanics:
  - id: MECH-{{NAME}}
    title: {{Name}}
    kind: experience
    pillars: [{{pillars}}]
    doc: docs/gdd/mechanics/{{name-kebab}}.md
    implemented_by: [SYS-{{NAME}}]
    config: [CFG-{{NAME}}]
    status: active

systems:
  - id: SYS-{{NAME}}
    name: {{Name}}System
    doc: docs/sdd/systems/{{name-kebab}}.md
    classes: [CLASS-{{Name}}System]
    config: [CFG-{{NAME}}]
    publishes: []
    subscribes: []

configs:
  - id: CFG-{{NAME}}
    name: {{Name}}Config
    type: ScriptableObject
    doc: docs/tdd/classes/{{Name}}System.md#{{name-kebab}}config
```

Rules:
- `pillars: [...]` must reference existing `PILLAR-*` IDs.
- `publishes` / `subscribes` are filled with `EVT-*` IDs as the system gains events. Empty lists are valid for a stub.
- `status` starts at `active` for the registry entry even when the docs are still `poc`. Use `deprecated` to retire, never delete.

## 7. Plans (out of scope for this recipe)

This recipe **does not** generate a plan stub. Plans live under `docs/plans/` and are authored deliberately via the `superpowers:writing-plans` skill when a change warrants one (multi-file changes, structural moves, contract changes). Many mechanic additions do not need a plan: a single mechanic with its system and test fits the "5-minute PoC carve-out" in `AGENTS.md`.

When a plan **is** warranted, write it through `superpowers:writing-plans` and reference the artefacts produced by this recipe (the GDD, SDD, TDD, registry block, and EditMode test) as the plan's affected files. Do not duplicate the recipe's templates inside the plan.

The `scaffold-mechanic` skill therefore writes only the four content artefacts (GDD, SDD, TDD, test) and prints the registry block. It does not touch `docs/plans/` or `docs/superpowers/`.

## 8. EditMode test template

File: `tests/EditMode/{{Name}}SystemTests.cs`. One conceptual assertion per `[Test]`.

```csharp
using NUnit.Framework;
using {{RootNamespace}}.{{Name}};

namespace {{RootNamespace}}.{{Name}}.Tests
{
    public class {{Name}}SystemTests
    {
        [Test]
        public void Tick_BaselineCondition_ProducesExpectedResult()
        {
            // Arrange-Act-Assert
            Assert.Fail("Implement the first formula assertion for {{Name}}System.");
        }
    }
}
```

Rules:
- Naming convention: `MethodName_Scenario_ExpectedResult`. The test name reads as a sentence describing what broke when it fails.
- `{{RootNamespace}}` is project-defined. It defaults to `LastBreath` per `docs/process/unity-patterns.md` Section 1 ("Project layout & .asmdef boundaries").
- No `Thread.Sleep`, no disk, no network, no `PlayerPrefs` (`docs/process/test-standards` rules apply).
- Replace the `Assert.Fail(...)` with a real assertion before merging the change.

## 9. Acceptance checklist

What `code-reviewer` will look for on the change that introduces the mechanic. The change is not mergeable until every box is ticked.

- [ ] `MECH-<NAME>` present in `architecture.yaml` with `status: active`, valid `pillars: [...]`, `implemented_by` pointing at an existing system.
- [ ] `SYS-<NAME>` present and points to one or more `CLASS-*`.
- [ ] `docs/gdd/mechanics/<name-kebab>.md` exists with the GDD section template filled.
- [ ] `docs/sdd/systems/<name-kebab>.md` exists with the SDD template filled.
- [ ] `docs/tdd/classes/<Name>System.md` exists with the TDD template filled.
- [ ] `tests/EditMode/<Name>SystemTests.cs` exists with at least one passing assertion.
- [ ] No game-specific synonyms used (canonical glossary).
- [ ] All identifiers are ASCII / English.
