---
name: level-design-session
user-invocable: true
description: Run a level-design session end-to-end — open the scene via unity-mcp, iterate, then perform the canonical snapshot ritual (DumpSpec, Validate, screenshots, session log, idempotency check). Enforces the order from docs/process/level-design.md §4. Use to start, resume, or close a session.
---

# level-design-session skill

## Purpose

Codifies the level-design loop from `docs/process/level-design.md` `§4` so every session ships the full audit bundle in the right order. The loop is rigid; the iteration in the middle is free.

## Args

- `scene_id` (required) — the `SCENE-*` ID being authored. Example: `SCENE-CORREDOR-C7`. Must exist in `docs/registry/architecture.yaml`.
- `goal` (required) — one sentence describing the session's intent. Becomes the `## Goal` line of the session log.
- `phase` (optional, default `auto`) — `start` | `iterate` | `snapshot` | `auto`. `auto` reads the latest session log and resumes from where the previous run stopped.

## Behaviour

### Phase `start`

1. Resolve `name_kebab` from `scene_id` by looking up the `scenes:` entry in `architecture.yaml` (`doc` field points at `docs/levels/<name_kebab>/README.md`). Abort if the scene has not been scaffolded yet — direct the user to `scaffold-level`.
2. Determine the next session number: `NNNN = max(existing session-*.md) + 1`, zero-padded to four digits.
3. Open `docs/levels/<name_kebab>/sessions/session-NNNN.md` and write the four-section template from `docs/process/level-design.md` `§6`, filling `## Goal` with the user-provided goal. Leave the other sections empty.
4. Verify `unity-mcp` is connected:
    - Call a no-op MCP verb (e.g., `scene.get_active`).
    - If it fails, surface the error to the user and stop. Do not degrade to YAML edits.
5. Open the scene via MCP: `scene.open("src/Assets/Scenes/<SceneName>.unity")`.
6. Print to the user: the path of the new session log, the active scene, the goal.

### Phase `iterate`

Free iteration via `unity-mcp`. The skill does not script this phase; the `level-designer` drives it. Allowed verbs are listed in `docs/process/unity-mcp.md` `§3`. The skill resumes control when the user signals "I am happy" (or equivalent).

### Phase `snapshot`

The snapshot ritual is rigid. Perform every step in order. If any step fails, surface the error and stop — do not skip steps or reorder them.

1. **Save the scene.** Call `scene.save()` via MCP. The `.unity` is now on disk.
2. **Validate.** Call `menu.invoke("LastBreath/Level/Validate")`. If `ValidationReport.IsOk == false`, print the report and stop; the level-designer fixes the violations in MCP and re-runs `snapshot`.
3. **Dump spec.** Call `menu.invoke("LastBreath/Level/Dump Spec")`. The dumper writes `docs/levels/<name_kebab>/<name_kebab>.layout.yaml` and prints the path.
4. **Idempotency check.** Call `menu.invoke("LastBreath/Level/Apply Spec")` against a scratch scene path provided by `LevelSpec`. If the rebuilt scene differs from the committed scene on load-bearing fields, print the diff and stop. The level-designer either rolls the change back or files a bug against `LevelSpec.DumpSpec` (a missing field is a dumper bug, not a level bug).
5. **Screenshots.** Call `viewport.screenshot(<overview path>)` and `viewport.screenshot(<fpv path>)` with the paths from `docs/process/level-design.md` `§3` (`docs/levels/<name_kebab>/img/session-NNNN-overview.png` and `session-NNNN-fpv.png`). The level-designer frames each view before the call.
6. **Fill the session log.** Update `sessions/session-NNNN.md`:
    - `## What landed` — three to ten bullets, written from the live iteration.
    - `## What got rejected` — short but real.
    - `## Open questions` — one bullet per outstanding question.
    - `## Hand-offs` — `(none)` or one `<role>: <one sentence>` line if the next step needs another role.
7. **Stage the commit bundle.** List the files to stage:
    - `src/Assets/Scenes/<SceneName>.unity` and any new/changed `.prefab` / `.asset` under `src/Assets/_Project/Prefabs/Level/**` or `src/Assets/_Project/Config/Levels/**`.
    - `docs/levels/<name_kebab>/<name_kebab>.layout.yaml`.
    - `docs/levels/<name_kebab>/img/session-NNNN-overview.png` and `session-NNNN-fpv.png`.
    - `docs/levels/<name_kebab>/sessions/session-NNNN.md`.
   Do not commit on the user's behalf — the user reviews the diff and commits.
8. **Dispatch the reviewer.** Suggest `/review-level` (advisory) and, before merge, `/review-level --strict`.

### Phase `auto`

Read the latest `sessions/session-NNNN.md`. If `## What landed` is empty, resume from `iterate`. If it has bullets and the spec / screenshots are committed, the session is closed — print "session NNNN already snapshotted; start a new one with `phase: start`".

## Failure modes

- `unity-mcp` not connected: surface and stop. Do not fall back to YAML.
- `Validate` fails: surface and stop. Do not commit a scene that fails invariants.
- Idempotency check fails: surface and stop. Either roll back or file a dumper bug.
- Scene has not been scaffolded: surface and direct to `scaffold-level`.

## Constraints

- Never edits `src/Assets/_Project/Scripts/**`.
- Never edits `docs/registry/architecture.yaml` outside `scenes:` / `layouts:` (and only when adding entries, never renaming).
- Never commits on the user's behalf.
- Never skips a snapshot step. The order is the contract.

## See also

- `docs/process/level-design.md` — the canonical loop this skill enforces.
- `docs/process/unity-mcp.md` — the verbs the iterate phase uses.
- `.claude/agents/level-designer.md` — the role that invokes this skill.
- `.claude/skills/scaffold-level/` — sibling skill for first-time scene bring-up.
- `.claude/skills/review-level/` — sibling skill dispatched at the end of every session.
