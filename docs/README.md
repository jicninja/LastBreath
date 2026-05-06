# docs/

Living documentation for Last Breath PoC. Read `AGENTS.md` at the repo root first.

## Layout

| Path | Owner role | What lives here |
|---|---|---|
| `gdd/` | game-designer, narrative-director | Game design — pillars, mechanics, scene flow, narrative |
| `sdd/` | systems-designer | System architecture — responsibilities, events, invariants |
| `tdd/` | gameplay-programmer | Concrete classes and reference C# |
| `registry/` | systems-designer | `architecture.yaml` (canonical IDs) + `glossary.md` (canonical terms) |
| `process/` | any | Cross-cutting workflows (adding a mechanic, promoting a prototype, Unity patterns) |
| `plans/` | the role starting the change | Plans before code (`NNN-name.md`) |
| `engine-reference/` | unity-specialist | Engine version, best practices, deprecated APIs |
| `superpowers/specs/` | brainstorming | Approved design specs that turn into plans |

## Conventions

- Frontmatter on every new doc (id, type, layer, status, related).
- IDs come from `registry/architecture.yaml`. Never invent one.
- English only. Canonical terms only (see `registry/glossary.md`).
