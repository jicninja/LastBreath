---
id: ADR-0001-language-policy-english-only
type: decision
status: accepted
date: 2026-05-05
related: [PLAN-002, SPEC-AI-WORKFLOW-2026-05-05]
---

# ADR 0001: Language policy is English-only

## Context

The project began with mixed-language artefacts: Spanish prose in some early notes, English in `AGENTS.md`, Spanish-rooted IDs in `docs/registry/architecture.yaml` (`MECH-OXIGENO`, `MECH-AGITACION`, `MECH-PRESENCIA`, `MECH-EXPLORACION`, `MECH-ILUMINACION`, `MECH-LINTERNA`). The solo developer is fluent in both, but every artefact this project produces — code, identifiers, file names, comments, commit messages, docs, plans, and chat responses — needs a single canonical language to prevent drift and to make external collaboration (other agents, contributors, future-self after a long break) frictionless.

The competing rule was the registry's "stable IDs": once an ID exists, it never renames, even if it stops being used. Renaming Spanish IDs to English would violate that rule.

## Decision

**English is the only language used anywhere in this repo.** All new content (code, IDs, file names, comments, commit messages, docs, chat) is in English. The pre-existing Spanish IDs in `architecture.yaml` are deprecated (`status: deprecated`, with `replaced_by:` pointing at the new English ID where applicable) and English replacements are added as new entries:

| Old (deprecated) | New (active) |
|---|---|
| MECH-OXIGENO | MECH-OXYGEN |
| MECH-AGITACION | MECH-AGITATION |
| MECH-PRESENCIA | MECH-PRESENCE |
| MECH-EXPLORACION | MECH-INTERACTION (re-scoped — see ADR 0002 context) |
| MECH-ILUMINACION | (none — demoted) |
| MECH-LINTERNA | MECH-FLASHLIGHT |

The deprecated entries stay in the registry forever. The stable-ID rule is preserved — IDs are not renamed; new IDs are added and old ones marked deprecated.

## Alternatives considered

- **Grandfather the Spanish IDs.** Keep them as-is, accept the language inconsistency, write new IDs in English. *Rejected because* every reviewer pass would need to remember the exception, and the inconsistency would be a constant tax on cognitive load. The "english-only" rule is simpler than "english-only except these six legacy IDs."
- **Rename the Spanish IDs in place.** Edit them to English without leaving deprecation markers. *Rejected because* it violates the immutability rule that protects against ID drift across docs and (eventually) code. Renaming would make any historical reference (commit messages, archived plans) silently invalid.
- **Hybrid: aliases.** Keep both Spanish and English forms as resolvable IDs in the registry. *Rejected because* it creates two ways to refer to the same thing forever, doubling the surface that has to stay in sync.

## Consequences

- **Easy:** new artefacts have one canonical vocabulary. Reviewers can grep for non-ASCII identifiers as a violation signal. Future contributors don't need Spanish.
- **Hard:** historical commits and any external references (issues, notes outside the repo) that mention `MECH-OXIGENO` etc. will need translation when read aloud. Acceptable tax — those references are rare and resolved by the deprecation note.
- **Accepted loss:** the registry now carries six deprecated entries that bloat its line count. This is the price of the immutability rule and is worth paying.

## Notes

This ADR was written after plan 002 executed the rewrite. It backfills the rationale for an ID rewrite that future-readers will otherwise find inexplicable.
