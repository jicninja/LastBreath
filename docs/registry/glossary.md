---
id: GLOSSARY
type: glossary
layer: registry
status: active
---

# Canonical Glossary

Project-wide canonical terms. Use these spellings exactly; do not invent synonyms.

## Resources

- **oxygen** — the main resource that depletes over time and ends the run at zero.
- **agitation** — the player's stress meter (0–100) that modulates oxygen drain.

## Threat

- **presence** — the unseen entity. Communicated only through environmental events; never visually confirmed.

## Spaces

- **interior** — the lit station interior; safer.
- **exterior** — the space-side walkway; higher drain, lower visibility.
- **airlock** — the transition between interior and exterior. Holds the only PoC checkpoint.
- **corridor** — connective interior space (e.g., Corridor C-7).

## Player tools and surfaces

- **flashlight** — the helmet light. The only light source the player controls.
- **panel** — a wall-mounted interactable that gates progress.

## Events and registry vocabulary

- **event** — a typed signal published by one system, consumed by zero or more subscribers. Identified by an `EVT-*` ID in `docs/registry/architecture.yaml`.
- **publisher** — the single system allowed to emit a given event. Each `EVT-*` has exactly one publisher.
- **subscriber** — any system that listens to a given event. An event may have many subscribers.
- **payload** — the typed data carried with an event. Documented in `architecture.yaml` and in the publisher's SDD section.
- **channel** — a `ScriptableObject` event bus typed by payload, used for cross-scene fire-and-forget signalling. Pattern documented in `docs/process/unity-patterns.md` §3.
- **registry drift** — code introduces a class, event, or system that has no entry in `architecture.yaml`. The `code-reviewer` flags this under `REGISTRY-DRIFT-*`.

## Roles

The seven roles defined in `AGENTS.md` and `.claude/agents/`:

- **game-designer** — owns `docs/gdd/**` (mechanic prose, scene flow, pillars).
- **systems-designer** — owns `docs/sdd/**` and `docs/registry/**` (system contracts, IDs).
- **gameplay-programmer** — owns `src/**` and `docs/tdd/**` (C# code, class docs).
- **unity-specialist** — owns Unity config in `src/**` (asmdef, packages, project settings).
- **qa-tester** — owns `tests/**` and test plans in `docs/plans/**`.
- **narrative-director** — owns narrative sections in `docs/gdd/**` (audio logs, panels, HUD copy).
- **code-reviewer** — read-only auditor; owns nothing. Dispatched at the end of every code change.

## Anti-glossary (do not use)

- "monster", "creature", "entity" — say `presence`.
- "stress", "fear meter", "panic" — say `agitation`.
- "air", "lungs" — say `oxygen`.
- "outside", "vacuum", "EVA" — say `exterior`.
- "message", "signal", "notification" (in code/architecture context) — say `event`.
- "listener", "handler" (in architecture context) — say `subscriber`.
