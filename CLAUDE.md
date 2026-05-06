# CLAUDE.md

**All work in this repo MUST be done in English.** Code, identifiers, file names, comments, commit messages, docs, plans, and chat responses — English only.

This repo uses `AGENTS.md` as the single entry-point for all agents (Claude Code, Codex, Gemini).

**Read `AGENTS.md` before acting.** It contains:

- Required reading (`docs/registry/architecture.yaml`, GDD, SDD, TDD, engine-reference).
- Role table and what each role may touch (`.claude/agents/`).
- Global rules (stable IDs, canonical glossary, no accented characters in code, plans before code).

Additional specific rules live in `.claude/rules/`:

- `gameplay-code.md` — C# under `src/Assets/_Project/**`.
- `prototype-code.md` — C# under `src/Assets/_Sandbox/**`.
- `test-standards.md` — EditMode/PlayMode tests.
- `design-docs.md` — frontmatter, IDs, and doc prose.

If `CLAUDE.md` and `AGENTS.md` ever conflict, `AGENTS.md` wins (it is the source of truth).
