# docs/engine-reference/

Engine-version-pinned references. Read these when writing code or Unity config.

## Files

- `unity/VERSION.md` — current Unity LTS version this project targets. Read first.
- `unity/current-best-practices.md` — accepted patterns for the pinned version.
- `unity/deprecated-apis.md` — APIs forbidden in this codebase. The `code-reviewer` subagent flags any usage.

## When to consult

- Before writing C# under `src/Assets/_Project/**`.
- Before adding a new package to the Unity manifest.
- When reviewing a diff for forbidden API usage.

## Update policy

- `unity-specialist` owns these files.
- A Unity LTS bump requires a plan and updates to all three files in lockstep.
