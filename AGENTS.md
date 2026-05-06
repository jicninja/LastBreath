# Last Breath — AGENTS.md

Entry point for any agent (Claude Code, Codex, Gemini) working on this repo.

## Language policy

**All work in this repo is in English.** Code, identifiers, file names, comments, commit messages, docs, plans, and chat responses — English only. The legacy docs in Spanish will be migrated as they are touched.

## What this is

PoC of a Unity + URP game. Solo dev, small scope (3–5 minutes of gameplay).
Living documentation lives in `docs/`. The Unity project lives in `src/` (does not exist yet).

## Before acting — required reading

1. `docs/registry/architecture.yaml` — canonical IDs of pillars, systems, classes, and configs. **Never invent an ID.**
2. `docs/gdd/last-breath-poc-gdd.md` — design and pillars.
3. `docs/sdd/last-breath-poc-sdd.md` — system architecture.
4. `docs/tdd/last-breath-poc-tdd.md` — concrete classes and reference code.
5. `docs/engine-reference/unity/` — version, best practices, and forbidden APIs.
6. `docs/registry/glossary.md` — canonical terms. Use these spellings exactly.

If the change touches a specific system, read only the relevant section (the docs are organized under navigable headings).

## Roles

Each role lives in `.claude/agents/`. Hard rules on what each can touch:

| Role | Reads | May modify | Does NOT touch |
|---|---|---|---|
| `game-designer` | GDD, registry | `docs/gdd/**`, `docs/registry/architecture.yaml` (`pillars`, `mechanics`, `scenes` only) | SDD, TDD, code |
| `systems-designer` | GDD, SDD, registry | `docs/sdd/**`, `docs/registry/**` | TDD, code |
| `gameplay-programmer` | SDD, TDD, registry, engine-reference | `src/**`, `docs/tdd/**` | GDD, SDD |
| `unity-specialist` | TDD, engine-reference | `src/**` (Unity config, prefabs, .asmdef), `docs/engine-reference/unity/VERSION.md` (only when package versions move) | gameplay logic, design docs |
| `qa-tester` | everything | `docs/plans/**` (test plans/results), `docs/qa/bug-reports/**`, `tests/**` | systems |
| `narrative-director` | GDD | `docs/gdd/**` (narrative only), `src/Assets/_Project/Localization/**` (strings only, when it exists) | mechanics, systems, code outside localization |
| `code-reviewer` | rules, registry, plans, Unity patterns, diff | nothing (read-only) | all writes |

If a change crosses boundaries (e.g., adding a new mechanic → touches GDD + SDD + TDD), the agent that starts must **leave a plan** in `docs/plans/NNN-name.md` before touching code, and the other roles consume that plan.

## Global rules

- **English only** in code, docs, identifiers, file names, comments, and chat.
- **Stable IDs**: once created in `architecture.yaml`, an ID is never renamed. If something is removed, mark it `status: deprecated` and keep the entry.
- **Canonical glossary**: always use the registry terms (`oxygen`, `agitation`, `presence`). Do not invent synonyms.
- **No accented characters in code or file names**. In prose (markdown) they are allowed but the existing docs do not use them — keep consistency.
- **Do not touch `.pen` with Read/Grep**: they are encrypted files, only via the `pencil` MCP.
- **Plans before code** for any change touching more than one class. The plan lives in `docs/plans/NNN-title.md`.
- **Verify before declaring done**: if you add a class, it must compile; if you add a gameplay rule, it must have at least one test or a verifiable acceptance in the plan.

## File conventions

- New docs: kebab-case, in the folder of the role that writes them (`docs/gdd/`, `docs/sdd/`, `docs/tdd/`, `docs/plans/`, `docs/process/`, `docs/decisions/`, etc.).
- Mandatory frontmatter on new design docs:
  ```yaml
  ---
  id: SYS-OXYGEN          # or PILLAR-01, CLASS-OxygenSystem, etc.
  type: system            # pillar | mechanic | system | class | config | scene
  layer: sdd              # gdd | sdd | tdd
  status: poc             # poc | active | deprecated
  related: [PILLAR-01, CFG-OXYGEN]
  ---
  ```

- Other doc families keep the same fields but use their own `type`, `layer`, and `status` values (for example `type: plan`, `type: decision`, `type: reference`, `type: glossary`, or `type: spec`).

## Before opening a plan or new doc

Run the doc audit so the plan picks up every relevant existing MD instead of duplicating one:

```
python3 scripts/audit-md.py --quiet
```

It prints `ORPHANS` (docs nothing references — likely already cover what you are about to write) and `BROKEN_REFS` (links to MDs that no longer exist). Read the orphans for your area before drafting; link or supersede them rather than re-documenting.

## When NOT to use this flow

Solo-dev PoC. If the change is 5 minutes and a single class, do it and update the affected doc. Do not open a plan to fix a typo. Ceremony is proportional to blast radius.
