# .claude/rules/

Hard rules layered on top of `AGENTS.md`. Each file is scoped to a path or activity.

| File | Scope |
|---|---|
| `asset-design.md` | `art/**`, `src/Assets/_Project/Art/**`, registry `art_assets:` (ADR-0008) |
| `design-docs.md` | `docs/{gdd,sdd,tdd}/**` |
| `gameplay-code.md` | C# under `src/Assets/_Project/**` |
| `harness-loop.md` | Cross-cutting; moment-of-completion (ADR-0011) |
| `level-design.md` | `docs/levels/**`, `src/Assets/Scenes/**.unity`, level prefabs and configs (ADR-0007) |
| `prototype-code.md` | C# under `src/Assets/_Sandbox/**` |
| `test-standards.md` | EditMode and PlayMode tests |

## How rules interact with the reviewer

The `code-reviewer` subagent reads every file in this directory and checks the diff against them. Each rule is identified by a stable `rule_id` (e.g., `GAMEPLAY-CODE-NO-FINDOBJECTOFTYPE`); see `.claude/agents/code-reviewer.md` for the full list.
