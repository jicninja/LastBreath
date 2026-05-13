# docs/

Living documentation for Last Breath PoC. Read `AGENTS.md` at the repo root first.

## Layout

| Path | Owner role | What lives here |
|---|---|---|
| `gdd/` | game-designer, narrative-director | Game design — pillars, mechanics, scene flow, narrative |
| `sdd/` | systems-designer | System architecture — responsibilities, events, invariants |
| `tdd/` | gameplay-programmer | Concrete classes and reference C# |
| `registry/` | systems-designer | `architecture.yaml` (canonical IDs) + `glossary.md` (canonical terms) |
| `process/` | any | Cross-cutting workflows and canonical loops |
| `plans/` | the role starting the change | Plan contracts before code (`NNN-name.md`) |
| `exec-plans/` | implementing role | Living execution records once a plan starts (`EXEC-NNN-name.md`) |
| `levels/` | level-designer | Level specs, session logs, screenshots, and layout artifacts |
| `specs/` | any | Proposed design specs awaiting implementation plans |
| `engine-reference/` | unity-specialist, asset-designer | Unity, Blender, and MCP version pins plus API constraints |
| `decisions/` | any | ADR-style architectural decisions; read before touching the code paths they bind |

## Conventions

- Frontmatter on every new doc (id, type, layer, status, related).
- IDs come from `registry/architecture.yaml`. Never invent one.
- Plans are contract documents; ExecPlans are execution documents.
- English only. Canonical terms only (see `registry/glossary.md`).
