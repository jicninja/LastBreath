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
- `asset-design.md` — `art/**`, `src/Assets/_Project/Art/**`, registry `art_assets:` (ADR-0008).
- `level-design.md` — scene composition, prefabs, layout YAML (ADR-0007).
- `harness-loop.md` — cross-cutting; moment-of-completion (review, runtime-probe, promotion). ADR-0011.
- `exec-plans.md` — ExecPlans under `docs/exec-plans/` (self-contained execution documents; ADR-0012). Canonical loop: `docs/process/exec-plans.md`.

**Before writing code against any external library / engine API: query the `context7` MCP** for the docs of the version this project uses, so you don't emit deprecated patterns from training memory. This is a *don't-write-stale* rule, not an *auto-upgrade* rule — never bump versions as a side effect; propose upgrades in a plan. Full rule in `AGENTS.md` § Global rules and § MCP servers.

If `CLAUDE.md` and `AGENTS.md` ever conflict, `AGENTS.md` wins (it is the source of truth).
