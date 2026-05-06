# .claude/rules/

Hard rules layered on top of `AGENTS.md`. Each file is scoped to a path or activity.

| File | Scope |
|---|---|
| `gameplay-code.md` | C# under `src/Assets/_Project/**` |
| `prototype-code.md` | C# under `src/Assets/_Sandbox/**` |
| `test-standards.md` | EditMode and PlayMode tests |
| `design-docs.md` | `docs/{gdd,sdd,tdd}/**` |

## How rules interact with the reviewer

The `code-reviewer` subagent reads every file in this directory and checks the diff against them. Each rule is identified by a stable `rule_id` (e.g., `GAMEPLAY-CODE-NO-FINDOBJECTOFTYPE`); see `.claude/agents/code-reviewer.md` for the full list.
