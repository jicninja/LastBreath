---
name: unity-patterns
user-invocable: true
description: Loads canonical Unity patterns from docs/process/unity-patterns.md into the caller's context. Invoke before writing C# under src/Assets/_Project/**.
---

# unity-patterns skill

## Purpose

Single canonical source for "how to structure Unity C# in this project." Loads relevant pattern sections into context. Never writes.

## Usage

**Args:**
- `topic` (optional): one of the section slugs in `docs/process/unity-patterns.md`. Examples:
  - `project-layout`
  - `monobehaviour-split`
  - `scriptable-object-config`
  - `update-loop`
  - `event-symmetry`
  - `coroutine-alternatives`
  - `input-system`
  - `addressables`
  - `serialization`
  - `cross-scene`
  - `gc`
  - `editor-only`
  - `testability`

If `topic` is omitted, the skill returns the table of contents and asks the caller to pick one or more topics.

## Behaviour

1. Read `docs/process/unity-patterns.md`.
2. If `topic` is provided, extract the matching section(s) and return them verbatim.
3. If `topic` is missing, return the table of contents.
4. **Never** edit, write, or modify any file.

## Constraints

- This skill is read-only.
- The doc is the contract. If the skill description and the doc disagree, the doc wins and the skill is broken.
- Genericity: never inject project-specific mechanic names into the loaded sections; the source doc is project-agnostic by design.
