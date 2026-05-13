# Last Breath — AGENTS.md

Entry point for any agent (Claude Code, Codex, Gemini) working on this repo.

## Language policy

**All work in this repo is in English.** Code, identifiers, file names, comments, commit messages, docs, plans, and chat responses — English only. The legacy docs in Spanish will be migrated as they are touched.

## What this is

PoC of a Unity + URP game. Solo dev, small scope (3–5 minutes of gameplay).
Living documentation lives in `docs/`. The Unity project lives in `src/` (does not exist yet).

## Before acting — required reading

1. `docs/registry/architecture.yaml` — canonical IDs of pillars, systems, classes, configs, scenes, and layouts. **Never invent an ID.**
2. `docs/gdd/last-breath-poc-gdd.md` — design and pillars.
3. `docs/sdd/last-breath-poc-sdd.md` — system architecture.
4. `docs/tdd/last-breath-poc-tdd.md` — concrete classes and reference code.
5. `docs/engine-reference/unity/` — Unity version, best practices, and forbidden APIs. Companions: `docs/engine-reference/blender/VERSION.md` (Blender pin) and `docs/engine-reference/mcp/VERSIONS.md` (MCP server pins). All three are bound by ADR-0009.
6. `docs/registry/glossary.md` — canonical terms. Use these spellings exactly.
7. `docs/decisions/` — binding architectural decisions (ADRs). Several rules in `.claude/rules/gameplay-code.md` cite specific ADRs as their rationale; read the ADR before touching flags, save, narrative, or dialogue code.
8. `docs/process/harness-engineering.md` — canonical loop for review, runtime-probe, and feedback-promotion (ADR-0011). Binds every authoring role at session close.
9. `docs/process/exec-plans.md` — canonical loop for ExecPlans (the artifact a coding agent reads to execute multi-session implementation work end-to-end). Binds the `EXEC-PLAN-*` rule family. ADR-0012.

For level-design work also read:

- `docs/process/level-design.md` — the canonical session loop (iterate via MCP, end-of-session snapshot, commit bundle).
- `docs/process/unity-mcp.md` — the authoring surface (`unity-mcp` setup, capability matrix, gotchas).
- `docs/decisions/0007-level-design-authoring-flow.md` — the decision that shapes the level-designer role and rules.

For asset-design work (3D assets in Blender → Unity) also read:

- `docs/process/asset-design.md` — the canonical Blender-side loop, manifest schema, approval gate.
- `docs/process/blender-mcp.md` — the authoring surface (`blender-mcp` setup, capability matrix, role allowlists).
- `docs/decisions/0008-asset-pipeline.md` — the decision that shapes the asset-designer role, the staging area, and the sync verifier.

If the change touches a specific system, read only the relevant section (the docs are organized under navigable headings).

## Roles

Each role lives in `.claude/agents/`. Hard rules on what each can touch:

| Role | Reads | May modify | Does NOT touch |
|---|---|---|---|
| `game-designer` | GDD, registry | `docs/gdd/**`, `docs/registry/architecture.yaml` (`pillars`, `mechanics`, `scenes` only) | SDD, TDD, code |
| `systems-designer` | GDD, SDD, registry | `docs/sdd/**`, `docs/registry/**` | TDD, code |
| `gameplay-programmer` | SDD, TDD, registry, engine-reference | `src/**`, `docs/tdd/**` | GDD, SDD |
| `unity-specialist` | TDD, engine-reference | `src/**` (Unity config, prefabs, .asmdef), `docs/engine-reference/unity/VERSION.md` (only when package versions move) | gameplay logic, design docs |
| `level-designer` | GDD scene flow, SDD `§EnvironmentSystem`, registry, `docs/process/level-design.md`, `docs/process/unity-mcp.md`, `docs/process/blender-mcp.md` `§4` (read-only verbs only) | `docs/levels/**`, `src/Assets/Scenes/**.unity` composition, `src/Assets/_Project/Prefabs/Level/**`, `src/Assets/_Project/Config/Levels/**`, `src/Assets/_Project/Art/**` only via `[MenuItem("LastBreath/Art/Import Approved Assets")]`, `docs/registry/architecture.yaml` (`scenes` and `layouts` only) | gameplay code, engine config, design intent, narrative copy, `blender-mcp` author verbs, `art/**` |
| `asset-designer` | GDD scene/prop intent, registry (`art_assets:`), `docs/process/asset-design.md`, `docs/process/blender-mcp.md`, `docs/decisions/0008-asset-pipeline.md` | `art/**`, `docs/registry/architecture.yaml` (`art_assets:` only) | `.unity`, `docs/levels/**`, `src/Assets/_Project/Art/**`, gameplay code, engine config, design docs, narrative copy, `manifest.approved: true` (only the user writes this) |
| `qa-tester` | everything | `docs/plans/**` (test plans/results), `tests/**` | systems |
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
- **ExecPlan is the format for execution work (ADR-0012)**. When implementation of a Plan begins (or when a multi-session change starts), the executing role opens `docs/exec-plans/EXEC-NNN-<title>.md` with the twelve mandatory sections from the skeleton template. The ExecPlan is self-contained (`EXEC-PLAN-SELF-CONTAINED`), living while `active` (`EXEC-PLAN-LIVING-DOCUMENT`), and produces observable behaviour (`EXEC-PLAN-OBSERVABLE-OUTCOME`). Full text: `.claude/rules/exec-plans.md`. Canonical loop and skeleton template: `docs/process/exec-plans.md`.
- **Verify before declaring done**: if you add a class, it must compile; if you add a gameplay rule, it must have at least one test or a verifiable acceptance in the plan.
- **No stale APIs — consult Context7 before writing**: before you emit code that calls into an external API, engine package, or framework feature (Unity, URP, Input System, Godot, .NET BCL, third-party packages, npm libs, etc.), query the `context7` MCP for the docs of the version the project actually uses. Default to current, idiomatic, non-deprecated patterns. This rule is about **what you write**, not about upgrading what already exists: never bump a package or engine version as a side effect — propose it in a plan first.
- **Harness loop is binding (ADR-0011)**: every session that produced a gameplay or level diff closes by running the matching `/review-*` skill (or recording a skip in `docs/registry/review-log.md`); every gameplay change references a runtime-probe artifact in its plan acceptance; recurring observations are promoted to a rule, a linter, or an ADR before the session closes. Full text: `.claude/rules/harness-loop.md`. Canonical loop: `docs/process/harness-engineering.md`.

## MCP servers

Configured in `.mcp.json` (project-scoped, committed). Versions are pinned in `docs/engine-reference/mcp/VERSIONS.md` and mirrored in `docs/registry/architecture.yaml::tooling.mcp_servers`. Bumping any MCP is plan-gated, identical to the Unity package bump policy; before drafting the bump plan, query `context7` for the upstream README (per the global `no-stale-APIs` rule below).

| Server | Use for |
|---|---|
| `context7` | Up-to-date docs and idiomatic usage for any external library, engine package, or framework API. Query before writing code against it. |
| `pencil` | Only way to read/write `.pen` design files. Never use Read/Grep on them. |
| `unity-mcp` | The authoring surface for `level-designer`. Live-edits the Unity editor (open scene, create/move/delete nodes, instantiate prefabs, capture screenshots, invoke menu items). See `docs/process/unity-mcp.md` for setup and capability matrix. Drives the session loop in `docs/process/level-design.md`. Only the `level-designer` role uses it. |
| `blender-mcp` | The authoring surface for `asset-designer`. Drives Blender (open scene, run Python, download Polyhaven assets, export `.glb`, capture viewport screenshots). `asset-designer` has the full ADR-0008-allowed scope; `level-designer` has a strict read-only subset (`get_scene_info`, `get_object_info`, `get_viewport_screenshot`, `*_status`) for cross-tool verification. See `docs/process/blender-mcp.md` for setup, capability matrix, and per-role allowlists. |

On first session in a fresh clone, Claude Code will ask to approve `.mcp.json` — accept it. To auto-approve without prompting, the user (not an agent) can add to their personal `.claude/settings.local.json`: `{ "enableAllProjectMcpServers": true }`.

## Mechanical enforcement (hooks and pre-commit)

Several rules in `.claude/rules/` are also enforced by scripts and hooks. The agent does **not** need to remember them — the tooling fires automatically.

| Surface | Fires | Enforces |
|---|---|---|
| `SessionStart` hook → `scripts/art-staging-queue.py` | Every session start | Surfaces pending art approvals so the user can run `/art-approval-queue`. |
| `SessionStart` hook → `scripts/check-runtime-versions.py --quiet` | Every session start | Advisory drift check between `architecture.yaml::tooling`, the engine-reference VERSION files, `.mcp.json`, `src/ProjectSettings/ProjectVersion.txt`, and `src/Packages/manifest.json`. Surfaces stale pins so the next plan can fix them. Skips cleanly before bootstrap. ADR-0009. |
| `PostToolUse` hook → `scripts/check-art-sync.py --quiet` | After any `mcp__blender-mcp__` write verb (`download_*`, `generate_*`, `import_generated_asset*`, `set_texture`) | `ASSET-DESIGN-SYNC-PARITY` (advisory). Surfaces drift between Blender source and Unity import without blocking the tool call. |
| `pre-commit` hook → `scripts/check-manifest-schema.py` + `scripts/check-art-sync.py` | On `git commit` when staged paths touch `art/**`, `src/Assets/_Project/Art/**`, or `docs/levels/**/*.layout.yaml` | `ASSET-DESIGN-MANIFEST-REQUIRED`, `ASSET-DESIGN-LICENSE-DOCUMENTED`, `ASSET-DESIGN-PROVENANCE-DOCUMENTED`, `ASSET-DESIGN-SYNC-PARITY`. Blocks the commit if any validator returns non-zero. |
| `scaffold-asset` skill → `scripts/add-art-asset-to-registry.py` | When the user runs `/scaffold-asset` | Idempotently writes the new `art_assets:` entry into `docs/registry/architecture.yaml`. No manual paste. |

The `PostToolUse` hook and the `SessionStart` hook are wired in `.claude/settings.json` (committed). The pre-commit hook lives under `scripts/git-hooks/pre-commit`; opt in per clone with one command:

```
git config core.hooksPath scripts/git-hooks
```

Emergency bypass (rare; reviewers should still catch the violation):

```
LASTBREATH_SKIP_ART_HOOK=1 git commit ...
```

## File conventions

- New docs: kebab-case, in the folder of the role that writes them (`docs/gdd/`, `docs/sdd/`, `docs/tdd/`, `docs/plans/`, `docs/exec-plans/` for ExecPlans, `docs/process/`, `docs/decisions/`, etc.).
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
