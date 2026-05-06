# Rules — Design Docs

Applies to `docs/gdd/**`, `docs/sdd/**`, and `docs/tdd/**`.

## Frontmatter

Every new doc (not the three legacy ones) carries frontmatter:

```yaml
---
id: SYS-OXYGEN          # must exist in architecture.yaml
type: system            # pillar | mechanic | system | class | config | scene
layer: sdd              # gdd | sdd | tdd
status: poc             # poc | active | deprecated
related: [PILLAR-01, CFG-OXYGEN]
---
```

## IDs

- Once created, an ID is never renamed. If something stops existing: `status: deprecated` and the registry entry stays.
- Inventing an ID in a doc without registering it in `architecture.yaml` is a process error.

## Structure of a system doc (SDD)

1. **Responsibility** — one sentence. If you need "and also", split it.
2. **Inputs** — events it listens to + data it reads.
3. **Outputs** — events it publishes with payload.
4. **Invariants** — what can never happen.
5. **Acceptance** — verifiable list of observable behavior.
6. **Notes** — only what does not fit above.

## Canonical glossary

The canonical glossary lives in `docs/registry/glossary.md`. Use it. Do not invent synonyms.

## Prose

- All prose, identifiers, and file names in English.
- Short sentences. Bullet > paragraph when possible.
- No emojis unless the user explicitly asks.
- No meta-comments ("this doc was created to..."). The doc justifies itself by its content.

## Sync

- A GDD change that impacts a system requires opening a plan in `docs/plans/` and notifying the systems-designer.
- An SDD change that alters an event contract requires deprecating the old event in `architecture.yaml` and creating a new one.
