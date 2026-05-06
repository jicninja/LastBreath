# tests/process/reviewer/

Synthetic diffs that exercise the `code-reviewer` subagent. Each fixture is a unified diff with a YAML preamble naming the rule it must trigger.

## How to run

Manual for now (no CI yet). For each fixture:

1. Apply the diff to a scratch worktree (or simulate by piping to the reviewer's stdin if the harness supports it).
2. Dispatch the `code-reviewer` subagent.
3. Assert the response contains the expected `rule_id`.

| Fixture | Expected `rule_id` |
|---|---|
| `forbidden-api.diff` | `GAMEPLAY-CODE-NO-FINDOBJECTOFTYPE` |
| `missing-event-unsubscribe.diff` | `GAMEPLAY-CODE-EVENT-SYMMETRY` |
| `unregistered-class.diff` | `REGISTRY-DRIFT-UNREGISTERED-CLASS` |
| `out-of-scope.diff` | `PLAN-ADHERENCE-OUT-OF-SCOPE` |
| `formula-without-test.diff` | `TEST-STANDARDS-FORMULA-NEEDS-EDITMODE` |
| `monobehaviour-formula.diff` | `UNITY-PATTERN-MONOBEHAVIOUR-SPLIT` |

## When to run

- After any change to `.claude/agents/code-reviewer.md`.
- After any change to `.claude/rules/*.md`.
- After any change to `docs/process/unity-patterns.md`.
- Before declaring this plan done.

## Maintenance

If a fixture stops triggering, either tighten the rule or improve the reviewer prompt. **Do not delete the fixture** unless the rule itself is being retired.
