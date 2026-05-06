---
id: PLAN-002-restructure-docs-and-add-reviewer
type: plan
status: done
done_date: 2026-05-05
related: [SPEC-AI-WORKFLOW-2026-05-05]
---

# Restructure Docs and Add Reviewer — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Execute the AI-augmented workflow design from spec `docs/superpowers/specs/2026-05-05-ai-augmented-workflow-design.md`: move legacy monoliths into layer subfolders, rewrite registry IDs to English, add canonical Unity patterns reference, ship a `code-reviewer` subagent and slash command, modify `gameplay-programmer.md` to require pre-code pattern consult and post-code reviewer dispatch, ship a generic mechanic recipe + scaffold skill, and verify with synthetic violation fixtures.

**Architecture:** Pure docs/process work — no application code is created. Outputs are markdown files (rules, agent definitions, skill prompts, reference docs), one YAML registry edit, and a small fixtures suite. All changes are committable as independent units in spec §13 order. The reviewer subagent has read-only tools by definition; the scaffold skill writes only new files (no overwrites).

**Tech Stack:** Markdown + YAML for content, `git` for version control, `grep`/`find` for verification, no build system. Unity references are doc-only; no C# or Unity project work in this plan.

**Spec ref:** `docs/superpowers/specs/2026-05-05-ai-augmented-workflow-design.md`. Each task below maps to spec §11 acceptance criteria (cited inline as `AC-N`).

**Conventions for this plan:**
- "Verify: <command>" lines mean run that command and confirm it produces the stated expected output before checking the box.
- "Commit:" blocks use a HEREDOC for safety.
- All commit messages stay in English (per `AGENTS.md` policy).

---

## Task 0: Prerequisites — initialize git repository

**Files:**
- Create: `.gitignore`

The repo currently has no `.git`. Spec §12 promotes `git init` to a hard prerequisite because reviewer checks (§5.1, §9.1, §7.1) rely on `git diff` and `git log`.

- [ ] **Step 1: Confirm repo is not yet a git repo**

```bash
ls -la /Users/ignaciocastro/ia/LastBreath/.git
```
Expected: `No such file or directory`.

- [ ] **Step 2: Initialize git**

```bash
cd /Users/ignaciocastro/ia/LastBreath && git init -b main
```
Expected: `Initialized empty Git repository in /Users/ignaciocastro/ia/LastBreath/.git/`.

- [ ] **Step 3: Create `.gitignore`**

Write `.gitignore` with the minimal Unity + macOS noise blocklist:

```
# Unity
[Ll]ibrary/
[Tt]emp/
[Oo]bj/
[Bb]uild/
[Bb]uilds/
[Ll]ogs/
[Uu]ser[Ss]ettings/
*.csproj
*.sln
*.unityproj
*.suo
*.user
*.userprefs

# macOS
.DS_Store
.AppleDouble
.LSOverride

# Editors
.vscode/
.idea/

# Sandbox scratch (per .claude/rules/prototype-code.md)
src/Assets/_Sandbox/scratch/
```

- [ ] **Step 4: Stage existing files and confirm tree**

```bash
cd /Users/ignaciocastro/ia/LastBreath && git add . && git status --short | head -30
```
Expected: list of `A` entries for AGENTS.md, CLAUDE.md, .claude/**, docs/**.

- [ ] **Step 5: Initial commit**

```bash
cd /Users/ignaciocastro/ia/LastBreath && git commit -m "$(cat <<'EOF'
chore: initial commit — Last Breath PoC docs and agent setup

Brings the existing AGENTS.md entry-point, six role agents under
.claude/agents/, four rules files under .claude/rules/, the legacy
GDD/SDD/TDD monoliths, the architecture registry, plan 001
(split-oxygen), and the Unity engine-reference into git.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```
Expected: `[main (root-commit) <hash>] chore: initial commit ...`.

- [ ] **Step 6: Verify**

```bash
cd /Users/ignaciocastro/ia/LastBreath && git log --oneline | head -3
```
Expected: one line, the initial commit.

---

## Task 1: Move legacy monoliths into layer subfolders

**AC-1.** Move three docs out of flat `docs/` into `docs/{gdd,sdd,tdd}/`. Use `git mv` so history is preserved.

**Files:**
- Move: `docs/last-breath-poc-gdd.md` → `docs/gdd/last-breath-poc-gdd.md`
- Move: `docs/last-breath-poc-sdd.md` → `docs/sdd/last-breath-poc-sdd.md`
- Move: `docs/last-breath-poc-tdd.md` → `docs/tdd/last-breath-poc-tdd.md`

- [ ] **Step 1: Create the layer directories**

```bash
mkdir -p /Users/ignaciocastro/ia/LastBreath/docs/gdd /Users/ignaciocastro/ia/LastBreath/docs/sdd /Users/ignaciocastro/ia/LastBreath/docs/tdd
```

- [ ] **Step 2: Move the three files with `git mv`**

```bash
cd /Users/ignaciocastro/ia/LastBreath \
  && git mv docs/last-breath-poc-gdd.md docs/gdd/last-breath-poc-gdd.md \
  && git mv docs/last-breath-poc-sdd.md docs/sdd/last-breath-poc-sdd.md \
  && git mv docs/last-breath-poc-tdd.md docs/tdd/last-breath-poc-tdd.md
```

- [ ] **Step 3: Verify all three new paths exist and old paths are gone**

```bash
cd /Users/ignaciocastro/ia/LastBreath \
  && ls docs/gdd/last-breath-poc-gdd.md docs/sdd/last-breath-poc-sdd.md docs/tdd/last-breath-poc-tdd.md \
  && ! ls docs/last-breath-poc-*.md 2>/dev/null
```
Expected: three lines listing the new paths; the negated `ls` returns non-zero (no flat files remain).

- [ ] **Step 4: Confirm registry paths now resolve**

```bash
cd /Users/ignaciocastro/ia/LastBreath \
  && grep -E "doc: docs/(gdd|sdd|tdd)/" docs/registry/architecture.yaml | head -5 \
  && for p in $(grep -oE "docs/(gdd|sdd|tdd)/[^#[:space:]]+" docs/registry/architecture.yaml | sort -u); do test -f "$p" && echo "OK $p" || echo "MISSING $p"; done
```
Expected: every line prefixed `OK`. No `MISSING`.

- [ ] **Step 5: Commit**

```bash
cd /Users/ignaciocastro/ia/LastBreath && git commit -m "$(cat <<'EOF'
docs: move GDD/SDD/TDD into layer subfolders

Moves the three legacy monoliths from flat docs/ into docs/{gdd,sdd,tdd}/
to match the paths already referenced by docs/registry/architecture.yaml
and AGENTS.md. Resolves the path mismatch flagged in spec
docs/superpowers/specs/2026-05-05-ai-augmented-workflow-design.md §4.1.

Per-system splits (per plan 001) will land incrementally inside
docs/{gdd/mechanics,sdd/systems,tdd/classes}/ in later plans; the
monoliths stay in their layer folder until each system is fully split.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: Add index READMEs and lift glossary

**AC-3, AC-10.** Discoverability layer.

**Files:**
- Create: `docs/README.md`
- Create: `docs/plans/README.md`
- Create: `docs/registry/glossary.md`
- Create: `docs/engine-reference/README.md`
- Create: `.claude/agents/README.md`
- Create: `.claude/rules/README.md`
- Modify: `.claude/rules/design-docs.md` (remove glossary section, add reference link)
- Modify: `AGENTS.md` (add link to glossary)

- [ ] **Step 1: Create `docs/registry/glossary.md` (lifted content)**

```markdown
---
id: GLOSSARY
type: glossary
layer: registry
status: active
---

# Canonical Glossary

Project-wide canonical terms. Use these spellings exactly; do not invent synonyms.

## Resources

- **oxygen** — the main resource that depletes over time and ends the run at zero.
- **agitation** — the player's stress meter (0–100) that modulates oxygen drain.

## Threat

- **presence** — the unseen entity. Communicated only through environmental events; never visually confirmed.

## Spaces

- **interior** — the lit station interior; safer.
- **exterior** — the space-side walkway; higher drain, lower visibility.
- **airlock** — the transition between interior and exterior. Holds the only PoC checkpoint.
- **corridor** — connective interior space (e.g., Corridor C-7).

## Player tools and surfaces

- **flashlight** — the helmet light. The only light source the player controls.
- **panel** — a wall-mounted interactable that gates progress.

## Anti-glossary (do not use)

- "monster", "creature", "entity" — say `presence`.
- "stress", "fear meter", "panic" — say `agitation`.
- "air", "lungs" — say `oxygen`.
- "outside", "vacuum", "EVA" — say `exterior`.
```

- [ ] **Step 2: Create `docs/README.md`**

```markdown
# docs/

Living documentation for Last Breath PoC. Read `AGENTS.md` at the repo root first.

## Layout

| Path | Owner role | What lives here |
|---|---|---|
| `gdd/` | game-designer, narrative-director | Game design — pillars, mechanics, scene flow, narrative |
| `sdd/` | systems-designer | System architecture — responsibilities, events, invariants |
| `tdd/` | gameplay-programmer | Concrete classes and reference C# |
| `registry/` | systems-designer | `architecture.yaml` (canonical IDs) + `glossary.md` (canonical terms) |
| `process/` | any | Cross-cutting workflows (adding a mechanic, promoting a prototype, Unity patterns) |
| `plans/` | the role starting the change | Plans before code (`NNN-name.md`) |
| `engine-reference/` | unity-specialist | Engine version, best practices, deprecated APIs |
| `superpowers/specs/` | brainstorming | Approved design specs that turn into plans |

## Conventions

- Frontmatter on every new doc (id, type, layer, status, related).
- IDs come from `registry/architecture.yaml`. Never invent one.
- English only. Canonical terms only (see `registry/glossary.md`).
```

- [ ] **Step 3: Create `docs/plans/README.md`**

```markdown
# docs/plans/

Plans before code. Numbered sequentially: `NNN-kebab-name.md`.

## When to open a plan

- Any change that touches more than one class or more than one doc layer.
- Any change that adds, renames, or removes a system, mechanic, or class.
- Any structural move (file renames, folder restructures).

## When NOT to open a plan

- Single-class trivial changes inside `_Sandbox/`.
- Single-file typo fixes in docs.
- Sandbox spikes that won't be promoted (per `.claude/rules/prototype-code.md`).

## Lifecycle

| Status | Meaning |
|---|---|
| `proposed` | Drafted, not approved. |
| `active` | Approved; in flight. Only one or two should be `active` at once. |
| `done` | Acceptance criteria all met; archive but keep the file. |
| `abandoned` | Cancelled before completion. Note the reason in the file. |

## Numbering

- Always increment from the highest existing `NNN`. Never reuse numbers.
- Numbering is global across all plans regardless of status.
```

- [ ] **Step 4: Create `docs/engine-reference/README.md`**

```markdown
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
```

- [ ] **Step 5: Create `.claude/agents/README.md`**

```markdown
# .claude/agents/

Role definitions used by Claude Code, Codex, and Gemini. The role table from `AGENTS.md` is the source of truth; this file is an index.

## Roles

| File | Reads | May modify | Does NOT touch |
|---|---|---|---|
| `game-designer.md` | GDD, registry | `docs/gdd/**` | SDD, TDD, code |
| `systems-designer.md` | GDD, SDD, registry | `docs/sdd/**`, `docs/registry/**` | TDD, code |
| `gameplay-programmer.md` | SDD, TDD, registry, engine-reference, `docs/process/unity-patterns.md` | `src/**`, `docs/tdd/**` | GDD, SDD |
| `unity-specialist.md` | TDD, engine-reference | `src/**` (Unity config, prefabs, .asmdef) | docs |
| `qa-tester.md` | everything | `docs/plans/**` (test plans), `tests/**` | systems |
| `narrative-director.md` | GDD | `docs/gdd/**` (narrative only) | the rest |
| `code-reviewer.md` | rules, registry, plans, `docs/process/unity-patterns.md`, the diff | nothing (read-only) | nothing |

## Adding a role

Open a plan in `docs/plans/`. New roles must be enumerable here and in the boundary table in `AGENTS.md`.
```

- [ ] **Step 6: Create `.claude/rules/README.md`**

```markdown
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
```

- [ ] **Step 7: Modify `.claude/rules/design-docs.md` — remove glossary section, replace with reference**

Replace the existing `## Canonical glossary` block (the section listing `oxygen`, `agitation`, etc.) with:

```markdown
## Canonical glossary

The canonical glossary lives in `docs/registry/glossary.md`. Use it. Do not invent synonyms.
```

Keep all other sections of `design-docs.md` intact.

- [ ] **Step 8: Modify `AGENTS.md` — add glossary link**

Inside the "Before acting — required reading" section, append a sixth bullet:

```markdown
6. `docs/registry/glossary.md` — canonical terms. Use these spellings exactly.
```

- [ ] **Step 9: Verify glossary is no longer duplicated**

Two checks. (a) Regression check — confirm the inline glossary line is gone from `design-docs.md`:

```bash
cd /Users/ignaciocastro/ia/LastBreath \
  && ! grep -F "\`oxygen\`, \`agitation\`, \`presence\`" .claude/rules/design-docs.md
```
Expected: success (no match).

(b) Lift-landed check — confirm the lifted glossary defines the canonical terms as bullets:

```bash
cd /Users/ignaciocastro/ia/LastBreath \
  && grep -q "^- \*\*oxygen\*\*" docs/registry/glossary.md \
  && grep -q "^- \*\*agitation\*\*" docs/registry/glossary.md \
  && grep -q "^- \*\*presence\*\*" docs/registry/glossary.md
```
Expected: success (three matches).

- [ ] **Step 10: Verify all six README files exist**

```bash
cd /Users/ignaciocastro/ia/LastBreath \
  && for f in docs/README.md docs/plans/README.md docs/registry/glossary.md docs/engine-reference/README.md .claude/agents/README.md .claude/rules/README.md; do test -f "$f" && echo "OK $f" || echo "MISSING $f"; done
```
Expected: six `OK` lines.

- [ ] **Step 11: Commit**

```bash
cd /Users/ignaciocastro/ia/LastBreath && git commit -am "$(cat <<'EOF'
docs: add index READMEs and lift canonical glossary

Adds README index files for docs/, docs/plans/, docs/engine-reference/,
.claude/agents/, .claude/rules/. Lifts the canonical glossary from
.claude/rules/design-docs.md into docs/registry/glossary.md so it is
discoverable as a registry artefact and referenced from AGENTS.md.

Spec: docs/superpowers/specs/2026-05-05-ai-augmented-workflow-design.md §4.1.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: Rewrite `architecture.yaml` (English IDs, deprecations, kind tags)

**AC-2.** Five active English mechanic IDs, six deprecated Spanish IDs, `MECH-INTERACTION` mapped to `SYS-INTERACTOR` only, `MECH-ILUMINACION` deprecated with no replacement, `PILLAR-05` tagged `kind: production`.

**Files:**
- Modify: `docs/registry/architecture.yaml`

- [ ] **Step 1: Add `kind:` field to all pillars**

Edit each pillar entry to add `kind: experience` for PILLAR-01..04 and `kind: production` for PILLAR-05. Example for PILLAR-01:

```yaml
  - id: PILLAR-01
    title: Oxygen is time, tension, and decision
    kind: experience
    doc: docs/gdd/last-breath-poc-gdd.md#1-oxygen-is-time-tension-and-decision
    status: active
```

PILLAR-05 becomes:

```yaml
  - id: PILLAR-05
    title: Minimal scope, high impact
    kind: production
    doc: docs/gdd/last-breath-poc-gdd.md#5-minimal-scope-high-impact
    status: active
```

- [ ] **Step 2: Mark all six Spanish mechanic IDs as deprecated**

For each existing entry (`MECH-OXIGENO`, `MECH-AGITACION`, `MECH-PRESENCIA`, `MECH-EXPLORACION`, `MECH-ILUMINACION`, `MECH-LINTERNA`), add `status: deprecated` and `replaced_by:` pointing at the new English ID (or omit `replaced_by` for `MECH-ILUMINACION` which has no replacement, and add `deprecation_reason: lighting is a presentation channel handled by SYS-LIGHTVFX and SYS-PRESENCE; the player has no verbs against environmental lighting`).

Example:

```yaml
  - id: MECH-OXIGENO
    title: Oxygen
    pillars: [PILLAR-01, PILLAR-04]
    doc: docs/gdd/last-breath-poc-gdd.md#oxygen
    implemented_by: [SYS-OXYGEN]
    config: [CFG-OXYGEN]
    status: deprecated
    replaced_by: MECH-OXYGEN
```

`MECH-ILUMINACION` becomes:

```yaml
  - id: MECH-ILUMINACION
    title: Lighting
    pillars: [PILLAR-03]
    doc: docs/gdd/last-breath-poc-gdd.md#lighting
    implemented_by: [SYS-LIGHTVFX]
    status: deprecated
    deprecation_reason: lighting is a presentation channel handled by SYS-LIGHTVFX and SYS-PRESENCE; the player has no verbs against environmental lighting.
```

- [ ] **Step 3: Insert the five new English mechanic entries**

Add (immediately after the deprecated block):

```yaml
  - id: MECH-OXYGEN
    title: Oxygen
    kind: experience
    pillars: [PILLAR-01, PILLAR-04]
    doc: docs/gdd/last-breath-poc-gdd.md#oxygen
    implemented_by: [SYS-OXYGEN]
    config: [CFG-OXYGEN]
    status: active
  - id: MECH-AGITATION
    title: Agitation
    kind: experience
    pillars: [PILLAR-01, PILLAR-02]
    doc: docs/gdd/last-breath-poc-gdd.md#agitation
    implemented_by: [SYS-AGITATION]
    config: [CFG-AGITATION]
    status: active
  - id: MECH-PRESENCE
    title: Invisible presence
    kind: experience
    pillars: [PILLAR-02, PILLAR-03]
    doc: docs/gdd/last-breath-poc-gdd.md#invisible-presence
    implemented_by: [SYS-PRESENCE]
    config: [CFG-PRESENCE-EVENT]
    status: active
  - id: MECH-INTERACTION
    title: Interaction
    kind: experience
    pillars: [PILLAR-04]
    doc: docs/gdd/last-breath-poc-gdd.md#exploration
    implemented_by: [SYS-INTERACTOR]
    status: active
  - id: MECH-FLASHLIGHT
    title: Flashlight
    kind: experience
    pillars: [PILLAR-03, PILLAR-04]
    doc: docs/gdd/last-breath-poc-gdd.md#flashlight
    implemented_by: [SYS-PLAYER]
    status: active
```

- [ ] **Step 4: Verify YAML still parses**

```bash
cd /Users/ignaciocastro/ia/LastBreath \
  && python3 -c "import yaml; d = yaml.safe_load(open('docs/registry/architecture.yaml')); print('mechanics:', len(d['mechanics']), 'active:', sum(1 for m in d['mechanics'] if m.get('status','active') == 'active'))"
```
Expected: `mechanics: 11 active: 5`.

- [ ] **Step 5: Verify English IDs resolve to existing systems**

```bash
cd /Users/ignaciocastro/ia/LastBreath \
  && python3 -c "
import yaml
d = yaml.safe_load(open('docs/registry/architecture.yaml'))
sys_ids = {s['id'] for s in d['systems']}
for m in d['mechanics']:
    if m.get('status','active') == 'active':
        for sid in m.get('implemented_by', []):
            assert sid in sys_ids, f'{m[\"id\"]} → unknown system {sid}'
            print(f'{m[\"id\"]} → {sid} OK')
"
```
Expected: five `OK` lines, no assertion errors.

- [ ] **Step 6: Commit**

```bash
cd /Users/ignaciocastro/ia/LastBreath && git commit -am "$(cat <<'EOF'
registry: rewrite mechanic IDs to English; tag pillar kind

Deprecates the six Spanish-language mechanic IDs (MECH-OXIGENO,
MECH-AGITACION, MECH-PRESENCIA, MECH-EXPLORACION, MECH-ILUMINACION,
MECH-LINTERNA) and adds five active English replacements:
MECH-OXYGEN, MECH-AGITATION, MECH-PRESENCE, MECH-INTERACTION,
MECH-FLASHLIGHT.

MECH-EXPLORACION is replaced by MECH-INTERACTION mapped to
SYS-INTERACTOR (drops SYS-OBJECTIVE — the 45-second anti-block hint
is a sub-rule of SYS-OBJECTIVE, not a mechanic).

MECH-ILUMINACION is demoted with no replacement: lighting is a
presentation channel handled by SYS-LIGHTVFX and SYS-PRESENCE, not
a player-facing mechanic.

Pillars now carry kind: experience (PILLAR-01..04) or kind:
production (PILLAR-05) so reviewers know which pillars apply to
playtest behaviour vs scope decisions.

Spec: docs/superpowers/specs/2026-05-05-ai-augmented-workflow-design.md §4.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: Update `.claude/rules/design-docs.md` scope

**AC-4.** The rule already had its glossary lifted in Task 2. Now broaden its scope to include `docs/tdd/**`.

**Files:**
- Modify: `.claude/rules/design-docs.md`

- [ ] **Step 1: Update the scope line**

The current file has the line ``Applies to `docs/gdd/**` and `docs/sdd/**`.`` (with backticks around the paths). Replace it with ``Applies to `docs/gdd/**`, `docs/sdd/**`, and `docs/tdd/**`.`` — preserve the backticks.

- [ ] **Step 2: Verify**

```bash
cd /Users/ignaciocastro/ia/LastBreath && grep -F "Applies to \`docs/gdd/**\`, \`docs/sdd/**\`, and \`docs/tdd/**\`." .claude/rules/design-docs.md
```
Expected: one matching line printed.

- [ ] **Step 3: Commit**

```bash
cd /Users/ignaciocastro/ia/LastBreath && git commit -am "$(cat <<'EOF'
rules: extend design-docs.md scope to docs/tdd/**

TDD docs carry the same frontmatter and ID conventions as GDD/SDD,
so the rule should govern them too. Closes the gap flagged in
spec §4.1.

Spec: docs/superpowers/specs/2026-05-05-ai-augmented-workflow-design.md §4.1.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: Write `docs/process/unity-patterns.md` (canonical reference)

**AC-13.** The 13 sections from spec §5.6. Reviewer + scaffold consume this.

**Files:**
- Create: `docs/process/unity-patterns.md`

- [ ] **Step 1: Create the directory and write the doc**

```bash
mkdir -p /Users/ignaciocastro/ia/LastBreath/docs/process
```

Write `docs/process/unity-patterns.md` with the 13 sections below. **Each section follows the same shape**: `Pattern name`, `When to use`, `Minimal example` (5–15 lines, mechanic-agnostic — `FooSystem` / `BarConfig` / `BazEvent` only), `Anti-pattern`, `Rule cross-ref`. Frontmatter:

```yaml
---
id: PROCESS-UNITY-PATTERNS
type: reference
layer: process
status: active
related: [GAMEPLAY-CODE, TEST-STANDARDS]
---
```

Then sections, each with a stable `rule_id` anchor for `code-reviewer` to cite:

1. `unity-pattern-project-layout` — `_Project/{Systems,Configs,Prefabs,Scenes,ScriptableObjects,Tests}/`, one .asmdef per top-level folder, no cycles.
2. `unity-pattern-monobehaviour-split` — pure logic in plain C# class; MonoBehaviour as thin Unity-side adapter that owns serialised refs and forwards `Update()`.
3. `unity-pattern-scriptable-object-config` — Config (data-only, no runtime state), Runtime Set, Event Channel.
4. `unity-pattern-update-loop` — `Update`/`FixedUpdate`/`LateUpdate`/`[DefaultExecutionOrder(N)]`. No `[ExecuteAlways]` in `_Project/`.
5. `unity-pattern-event-symmetry` — subscribe in `OnEnable`, unsubscribe in `OnDisable`. No lambda subs.
6. `unity-pattern-coroutine-alternatives` — state machines preferred, async/await with `destroyCancellationToken`.
7. `unity-pattern-input-system` — Action Asset committed, action references serialised on consumers.
8. `unity-pattern-addressables` — `AsyncOperationHandle` cached and released; no `Resources.Load`.
9. `unity-pattern-serialization` — `[SerializeField] private` default; `[field: SerializeField]` for inspector-set properties.
10. `unity-pattern-cross-scene` — DI root for siblings, ScriptableObject Runtime Set for "find me all X", Event Channel for fire-and-forget.
11. `unity-pattern-gc` — no allocations in `Update`; cache `WaitForSeconds`; pool what instantiates >1 Hz.
12. `unity-pattern-editor-only` — `#if UNITY_EDITOR`, `[Conditional("UNITY_EDITOR")]`.
13. `unity-pattern-testability` — formula-bearing logic in plain C# classes; MonoBehaviour wrapper for ticks; EditMode tests the plain class directly.

Each section ends with: `**Reviewer rule_id:** UNITY-PATTERN-<UPPERCASED-SLUG>` (e.g., `UNITY-PATTERN-MONOBEHAVIOUR-SPLIT`).

The Section 2 minimal example **must** be a plain-C# `FooLogic` class with one method, plus a `FooBehaviour : MonoBehaviour` that owns a `FooLogic` instance and forwards `Update()`. This is the example `code-reviewer` matches against in fixture `monobehaviour-formula.diff`.

- [ ] **Step 2: Verify section count and rule_ids**

```bash
cd /Users/ignaciocastro/ia/LastBreath \
  && grep -c "^## " docs/process/unity-patterns.md
```
Expected: `13` (or 14 if you include a closing notes section; 13 minimum).

```bash
cd /Users/ignaciocastro/ia/LastBreath \
  && grep -c "Reviewer rule_id: UNITY-PATTERN-" docs/process/unity-patterns.md
```
Expected: `13`.

- [ ] **Step 3: Verify genericity (no game-specific terms)**

```bash
cd /Users/ignaciocastro/ia/LastBreath \
  && ! grep -i "oxygen\|agitation\|presence\|flashlight\|airlock" docs/process/unity-patterns.md
```
Expected: zero matches; the negated grep returns success (exit 0 only when no match found).

- [ ] **Step 4: Commit**

```bash
cd /Users/ignaciocastro/ia/LastBreath && git add docs/process/unity-patterns.md && git commit -m "$(cat <<'EOF'
docs: add canonical Unity patterns reference

Adds docs/process/unity-patterns.md with 13 mechanic-agnostic patterns
covering project layout, MonoBehaviour-vs-plain-C# split, ScriptableObject
patterns, update-loop discipline, event symmetry, coroutine alternatives,
Input System, Addressables, serialization, cross-scene references, GC,
editor-only code, and testability.

Each section carries a stable Reviewer rule_id (UNITY-PATTERN-<slug>)
the code-reviewer subagent will cite when flagging pattern violations.

Spec: docs/superpowers/specs/2026-05-05-ai-augmented-workflow-design.md §5.6.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 6: Write `unity-patterns` skill

**AC-14.** Loader skill that surfaces sections from the doc by `topic`. Never writes.

**Files:**
- Create: `.claude/skills/unity-patterns/SKILL.md`

- [ ] **Step 1: Create the directory and write the skill**

```bash
mkdir -p /Users/ignaciocastro/ia/LastBreath/.claude/skills/unity-patterns
```

Write `.claude/skills/unity-patterns/SKILL.md`:

```markdown
---
name: unity-patterns
user-invocable: true
description: Loads canonical Unity patterns from docs/process/unity-patterns.md into the caller's context. Invoke before writing C# under src/Assets/_Project/**.
---

# unity-patterns skill

## Purpose

Single canonical source for "how to structure Unity C# in this project." Loads relevant pattern sections into context. Never writes.

## Usage

**Args:**
- `topic` (optional): one of the section slugs in `docs/process/unity-patterns.md`. Examples:
  - `project-layout`
  - `monobehaviour-split`
  - `scriptable-object-config`
  - `update-loop`
  - `event-symmetry`
  - `coroutine-alternatives`
  - `input-system`
  - `addressables`
  - `serialization`
  - `cross-scene`
  - `gc`
  - `editor-only`
  - `testability`

If `topic` is omitted, the skill returns the table of contents and asks the caller to pick one or more topics.

## Behaviour

1. Read `docs/process/unity-patterns.md`.
2. If `topic` is provided, extract the matching section(s) and return them verbatim.
3. If `topic` is missing, return the table of contents.
4. **Never** edit, write, or modify any file.

## Constraints

- This skill is read-only.
- The doc is the contract. If the skill description and the doc disagree, the doc wins and the skill is broken.
- Genericity: never inject game-specific terms (oxygen, agitation, etc.) into the loaded sections.
```

- [ ] **Step 2: Verify the skill file exists**

```bash
cd /Users/ignaciocastro/ia/LastBreath && test -f .claude/skills/unity-patterns/SKILL.md && head -5 .claude/skills/unity-patterns/SKILL.md
```
Expected: file exists; first lines show frontmatter with `name: unity-patterns`.

- [ ] **Step 3: Commit**

```bash
cd /Users/ignaciocastro/ia/LastBreath && git add .claude/skills/unity-patterns/ && git commit -m "$(cat <<'EOF'
skills: add unity-patterns loader

Adds .claude/skills/unity-patterns/SKILL.md, a read-only loader skill
that surfaces sections from docs/process/unity-patterns.md into the
caller's context by topic. Used by gameplay-programmer before writing
C# and by code-reviewer when checking pattern adherence.

Spec: docs/superpowers/specs/2026-05-05-ai-augmented-workflow-design.md §5.6.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 7: Write `code-reviewer` subagent

**AC-5, AC-16.** Read-only agent. Reads rules, registry, plans, unity-patterns. Outputs structured `status` / `violations` / `registry_drift` / `plan_adherence`.

**Files:**
- Create: `.claude/agents/code-reviewer.md`

- [ ] **Step 1: Write the agent definition**

```markdown
---
name: code-reviewer
description: Reviews gameplay code changes against rules, registry, active plan, and Unity patterns. Read-only — cannot edit code, cannot approve a PR. Dispatched by gameplay-programmer at end of every gameplay change, or by user via /review-gameplay.
tools: [Read, Grep, Bash]
---

# code-reviewer agent

## Tools — read-only

- `Read`: any file in the repo.
- `Grep`: any file in the repo.
- `Bash`: read-only commands only — `git diff`, `git log`, `git status`, `git show`, `find`, `wc`, `head`, `tail`, `ls`. **No** `git commit`, `git push`, `git checkout`, `git reset`, or any command that writes to the working tree.

## Forbidden

- `Edit`, `Write`, `NotebookEdit`. Not granted.
- Any shell command that mutates the working tree, the index, or remote state.
- Approving its own input. The reviewer cannot be invoked recursively.

## Inputs

- `mode`: `strict | advisory` (required).
- `plan`: `<NNN> | none | auto` (default `auto` — the reviewer picks the active plan whose scope intersects the diff, or falls back to `none`).
- `diff_range`: a git range. Default: working tree vs `HEAD`.

## Reads

- The diff over `diff_range`.
- All files under `.claude/rules/`.
- `docs/registry/architecture.yaml`.
- `docs/registry/glossary.md`.
- `docs/process/unity-patterns.md`.
- The active plan (if any) under `docs/plans/`.

## Output (structured)

```yaml
status: approved | issues_found
mode: strict | advisory
violations:
  - rule_id: <stable-id>
    file: <relative-path>
    line: <int>
    why: <one sentence>
registry_drift:
  - kind: unregistered_class | unregistered_event | unknown_id | spanish_id_in_new_code
    name: <identifier>
    file: <relative-path>
    fix: <suggested fix>
plan_adherence:
  in_scope: true | false | warning
  notes: <string>
non_blocking_notes:
  - <string>
```

## Rule sources

The reviewer recognises rules with stable `rule_id`s. Sources:

| Source file | Rule prefix |
|---|---|
| `.claude/rules/gameplay-code.md` | `GAMEPLAY-CODE-*` |
| `.claude/rules/test-standards.md` | `TEST-STANDARDS-*` |
| `.claude/rules/design-docs.md` | `DESIGN-DOCS-*` |
| `.claude/rules/prototype-code.md` | `PROTOTYPE-CODE-*` |
| `docs/process/unity-patterns.md` | `UNITY-PATTERN-*` |
| `docs/registry/architecture.yaml` | `REGISTRY-DRIFT-*` |
| Active plan in `docs/plans/` | `PLAN-ADHERENCE-*` |

## Modes

- `strict`: `approved` requires `violations: []` and `registry_drift: []`. `plan_adherence.in_scope: warning` is acceptable but the calling agent must echo the warning in its done-statement.
- `advisory`: same checks; `approved` may carry non-empty `non_blocking_notes`. Used by `/review-gameplay`.

## Algorithm

1. Run `git diff <diff_range>` and parse changed files.
2. Read all rule sources listed above.
3. For each changed file under `src/Assets/_Project/**`:
   - Apply `GAMEPLAY-CODE-*` checks (forbidden APIs, event symmetry, no `Resources.Load`, no global singletons, etc.).
   - Apply `UNITY-PATTERN-*` checks (project layout, MonoBehaviour-vs-plain-C# split, allocations in `Update`, lambda subscriptions, etc.).
   - For new classes: verify the class ID exists in `architecture.yaml` under some system; if not, emit `REGISTRY-DRIFT-UNREGISTERED-CLASS`.
4. For each changed file under `src/Assets/_Sandbox/**`: apply `PROTOTYPE-CODE-*` checks (relaxed; only the still-firm rules).
5. For each changed test file: apply `TEST-STANDARDS-*` checks (no `Thread.Sleep`, naming convention, no inter-test dependencies).
6. For each changed doc under `docs/{gdd,sdd,tdd}/**`: apply `DESIGN-DOCS-*` checks (frontmatter present, IDs registered, glossary terms only).
7. If `plan != none`: read the plan, build the set of in-scope file globs, check that every changed file matches; if not, set `plan_adherence.in_scope: false` (or `warning` if mode is `strict` and the change is single-file).
8. Compose the structured output.

## Genericity

This agent definition contains zero references to `oxygen`, `agitation`, `presence`, `flashlight`, or any specific mechanic. Verifiable by `grep -i "oxygen\|agitation\|presence\|flashlight" .claude/agents/code-reviewer.md` returning zero matches.
```

- [ ] **Step 2: Verify the agent file exists and is generic**

```bash
cd /Users/ignaciocastro/ia/LastBreath \
  && test -f .claude/agents/code-reviewer.md \
  && ! grep -i "oxygen\|agitation\|presence\|flashlight" .claude/agents/code-reviewer.md
```
Expected: file exists; the negated grep returns success.

- [ ] **Step 3: Commit**

```bash
cd /Users/ignaciocastro/ia/LastBreath && git add .claude/agents/code-reviewer.md && git commit -m "$(cat <<'EOF'
agents: add code-reviewer subagent (read-only)

Adds .claude/agents/code-reviewer.md, a read-only review agent that
audits gameplay diffs against rules (gameplay-code, test-standards,
design-docs, prototype-code), the architecture registry, the active
plan, and the Unity patterns reference. Outputs a structured
violations / registry_drift / plan_adherence response.

Tools: Read, Grep, read-only Bash. No Edit, no Write, no working-tree
mutations. Cannot self-invoke.

Spec: docs/superpowers/specs/2026-05-05-ai-augmented-workflow-design.md §5.1.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 8: Write `/review-gameplay` slash command

**AC-6.** Thin wrapper that dispatches `code-reviewer` in advisory mode. One source of truth (the agent definition); two entry points (this skill + auto-dispatch).

**Files:**
- Create: `.claude/skills/review-gameplay/SKILL.md`

- [ ] **Step 1: Write the skill**

```bash
mkdir -p /Users/ignaciocastro/ia/LastBreath/.claude/skills/review-gameplay
```

Write `.claude/skills/review-gameplay/SKILL.md`:

```markdown
---
name: review-gameplay
user-invocable: true
description: Run the code-reviewer subagent in advisory mode against the current diff. Use to audit a change against rules, registry, active plan, and Unity patterns. Pass --strict to escalate to strict mode (used pre-merge).
---

# review-gameplay skill

## Purpose

User-facing entry point for the same review the gameplay-programmer agent dispatches automatically at the end of every gameplay change. One canonical review prompt, two entry points (this skill + auto-dispatch from the role).

## Args

- `--plan NNN` (optional) — scope the plan-adherence check to a specific plan. Default: auto (reviewer picks the active plan whose scope matches the diff).
- `--strict` (optional) — escalate to strict mode. Use before merging.
- `--range <git_range>` (optional) — review a specific git range. Default: working tree vs HEAD.

## Behaviour

1. Resolve `mode`: `advisory` by default; `strict` if `--strict` is passed.
2. Resolve `plan`: from `--plan`, or `auto`.
3. Dispatch the `code-reviewer` subagent with `mode`, `plan`, and `diff_range`.
4. Print the structured output.
5. Never edit any file.

## See also

- `.claude/agents/code-reviewer.md` — the agent this skill dispatches.
- `docs/process/unity-patterns.md` — one of the rule sources the reviewer consults.
```

- [ ] **Step 2: Verify**

```bash
cd /Users/ignaciocastro/ia/LastBreath && test -f .claude/skills/review-gameplay/SKILL.md && head -5 .claude/skills/review-gameplay/SKILL.md
```
Expected: file exists; frontmatter shows `name: review-gameplay`.

- [ ] **Step 3: Commit**

```bash
cd /Users/ignaciocastro/ia/LastBreath && git add .claude/skills/review-gameplay/ && git commit -m "$(cat <<'EOF'
skills: add review-gameplay slash command

Thin wrapper around the code-reviewer subagent. Dispatches in advisory
mode by default; --strict escalates to the same strict review the
gameplay-programmer auto-dispatches at end-of-change.

Spec: docs/superpowers/specs/2026-05-05-ai-augmented-workflow-design.md §5.2.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 9: Modify `gameplay-programmer.md` (must-rules)

**AC-15.** Append two hard rules per spec §5.5 merge instructions.

**Files:**
- Modify: `.claude/agents/gameplay-programmer.md`

- [ ] **Step 1: Read the current file to find the "Hard rules" and "Definition of done" sections**

```bash
cd /Users/ignaciocastro/ia/LastBreath && cat .claude/agents/gameplay-programmer.md
```

- [ ] **Step 2: Append the pre-code rule to the existing "Hard rules" (or equivalent) section**

Add inside the rules list:

```markdown
- **Before writing C#**, invoke the `unity-patterns` skill. Read the sections relevant to the system you are building (e.g., `monobehaviour-split`, `scriptable-object-config`, `update-loop`, `event-symmetry`, `testability`). Do not write code without consulting it.
```

- [ ] **Step 3: Append the post-code rule to the same section**

```markdown
- **After implementing a gameplay change**, dispatch the `code-reviewer` subagent in `strict` mode before declaring done. Provide `plan: <NNN>` if a plan is active. If the reviewer returns `issues_found`, fix and re-dispatch. Loop maximum 3 rounds; after that, surface to user with the latest violations list and stop. Failure to dispatch the reviewer = failure to ship.
```

- [ ] **Step 4: Append the new bullet to "Definition of done" (if such a section exists; otherwise add one)**

```markdown
- `code-reviewer` returned `approved` in `strict` mode for the change.
```

- [ ] **Step 5: Verify both rules present**

```bash
cd /Users/ignaciocastro/ia/LastBreath \
  && grep -q "Before writing C#" .claude/agents/gameplay-programmer.md \
  && grep -q "dispatch the .code-reviewer." .claude/agents/gameplay-programmer.md \
  && grep -q "unity-patterns" .claude/agents/gameplay-programmer.md
```
Expected: success (both the pre-code rule and the post-code reviewer-dispatch rule are present, and the unity-patterns reference appears).

- [ ] **Step 6: Commit**

```bash
cd /Users/ignaciocastro/ia/LastBreath && git commit -am "$(cat <<'EOF'
agents: gameplay-programmer must consult unity-patterns and dispatch reviewer

Appends two hard rules to .claude/agents/gameplay-programmer.md:
- Before writing C#, invoke the unity-patterns skill for relevant sections.
- After implementing a change, dispatch code-reviewer in strict mode and
  loop max 3 rounds before surfacing to user.

Adds one bullet to Definition of done: code-reviewer must have returned
approved in strict mode.

Spec: docs/superpowers/specs/2026-05-05-ai-augmented-workflow-design.md §5.5.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 10: Write `docs/process/adding-a-mechanic.md` (the recipe)

**AC-8.** Mechanic-agnostic recipe with the eight sections from spec §5.4.

**Files:**
- Create: `docs/process/adding-a-mechanic.md`

- [ ] **Step 1: Write the recipe**

Frontmatter:

```yaml
---
id: PROCESS-ADD-MECHANIC
type: reference
layer: process
status: active
related: [PROCESS-UNITY-PATTERNS, GAMEPLAY-CODE, TEST-STANDARDS]
---
```

Then the eight sections in order, each consumable on its own:

1. **When to add a mechanic vs. fold into an existing one** — the decision tree from spec §5.4 (player verb? rules-bearing state? maps 1:1 to a single pillar?).
2. **ID convention** — mirrors `architecture.yaml`: `MECH-<NAME>` PascalCase, English only, immutable.
3. **GDD section template** — the frontmatter + Function / Suggested rules / Visualisation / Design note skeleton.
4. **SDD system template** — Responsibility / Inputs / Outputs / Invariants / Acceptance / Notes.
5. **TDD class template** — Class signature / Public API / Dependencies / Test plan.
6. **Registry block template** — full YAML block with `mechanic` + `system` + `classes` + `config` + `events`.
7. **Plan template** — matches `docs/plans/001-pilot-split-oxygen.md`'s structure.
8. **EditMode test template** — one failing test for the formula, naming convention `MethodName_Scenario_ExpectedResult`.
9. **Acceptance checklist** — what `code-reviewer` will look for (mirrors §11 acceptance items).

Examples must use `FooSystem`, `BarConfig`, `BazEvent` — never game-specific names.

- [ ] **Step 2: Verify section count and genericity**

```bash
cd /Users/ignaciocastro/ia/LastBreath \
  && test $(grep -c "^## " docs/process/adding-a-mechanic.md) -ge 9 \
  && ! grep -i "oxygen\|agitation\|presence\|flashlight" docs/process/adding-a-mechanic.md
```
Expected: at least 9 sections; zero game-specific terms.

- [ ] **Step 3: Commit**

```bash
cd /Users/ignaciocastro/ia/LastBreath && git add docs/process/adding-a-mechanic.md && git commit -m "$(cat <<'EOF'
docs: add generic add-a-mechanic recipe

Adds docs/process/adding-a-mechanic.md, a mechanic-agnostic recipe
covering the decision tree (when is it a mechanic vs sub-rule),
templates for GDD section, SDD system, TDD class, registry block,
plan, EditMode test, and the acceptance checklist the code-reviewer
will use.

Examples use FooSystem / BarConfig / BazEvent — game-specific names
do not appear. Recipe is the contract; scaffold-mechanic skill
materialises it in Task 11.

Spec: docs/superpowers/specs/2026-05-05-ai-augmented-workflow-design.md §5.4.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 11: Write `scaffold-mechanic` skill + templates

**AC-7.** Refuses overwrites, never auto-edits the registry, prints YAML block to chat.

**Files:**
- Create: `.claude/skills/scaffold-mechanic/SKILL.md`
- Create: `.claude/skills/scaffold-mechanic/templates/gdd-mechanic.md`
- Create: `.claude/skills/scaffold-mechanic/templates/sdd-system.md`
- Create: `.claude/skills/scaffold-mechanic/templates/tdd-class.md`
- Create: `.claude/skills/scaffold-mechanic/templates/plan.md`
- Create: `.claude/skills/scaffold-mechanic/templates/edit-mode-test.cs`
- Create: `.claude/skills/scaffold-mechanic/templates/registry-block.yaml`

- [ ] **Step 1: Create directory and SKILL.md**

```bash
mkdir -p /Users/ignaciocastro/ia/LastBreath/.claude/skills/scaffold-mechanic/templates
```

Write `.claude/skills/scaffold-mechanic/SKILL.md`:

```markdown
---
name: scaffold-mechanic
user-invocable: true
description: Scaffold a new mechanic — writes GDD/SDD/TDD/test/plan stubs and prints a YAML block for architecture.yaml. Refuses to overwrite. Never auto-edits the registry.
---

# scaffold-mechanic skill

## Purpose

Materialise the recipe in `docs/process/adding-a-mechanic.md` for a new mechanic. Produces all stub files in one shot. The recipe is the contract; this skill is the faster path through it.

## Args

- `name` (PascalCase, required) — e.g., `Vision`. Becomes `MECH-VISION`, `SYS-VISION`, `VisionSystem`, etc.
- `pillars` (list of existing PILLAR-NN IDs, required) — must already exist as `status: active` in `docs/registry/architecture.yaml`.
- `kind` (`experience` | `production`, default `experience`).

## Behaviour

1. Read `docs/process/adding-a-mechanic.md` (the contract).
2. Validate: `name` matches `^[A-Z][a-zA-Z0-9]+$`; every pillar in `pillars` is present and active in `architecture.yaml`; no mechanic with this `name` exists (active or deprecated) in `architecture.yaml`.
3. Determine the next plan number `NNN` (max existing + 1 in `docs/plans/`).
4. Write these files (refuse to overwrite if any exist; abort with the conflicting paths listed):
   - `docs/gdd/mechanics/<name-kebab>.md` (from `templates/gdd-mechanic.md`)
   - `docs/sdd/systems/<name-kebab>.md` (from `templates/sdd-system.md`)
   - `docs/tdd/classes/<Name>System.md` (from `templates/tdd-class.md`)
   - `docs/plans/NNN-add-<name-kebab>.md` (from `templates/plan.md`)
   - `tests/EditMode/<Name>SystemTests.cs` (from `templates/edit-mode-test.cs`)
5. Print the registry YAML block to chat (rendered from `templates/registry-block.yaml`); the user pastes it into `architecture.yaml`. **The skill does not edit `architecture.yaml`.**

## Failure modes

- Conflict (target exists): abort, no partial writes.
- Unknown / inactive pillar: abort.
- Duplicate mechanic name (active or deprecated): abort.

## Constraints

- Never auto-edits `docs/registry/architecture.yaml`.
- Never overwrites existing files.
- Never references game-specific terms in the templates.
```

- [ ] **Step 2: Write template files**

Each template uses the placeholder `{{Name}}` (PascalCase), `{{name-kebab}}`, `{{NAME}}` (UPPERCASE), and `{{pillars}}` (comma-separated). Templates contain no game-specific terms.

`templates/gdd-mechanic.md`: frontmatter + the GDD section structure from spec §5.4 step 3.

`templates/sdd-system.md`: frontmatter + Responsibility / Inputs / Outputs / Invariants / Acceptance / Notes (per `.claude/rules/design-docs.md`).

`templates/tdd-class.md`: frontmatter + Class signature / Public API / Dependencies / Test plan.

`templates/plan.md`: matches `docs/plans/001-pilot-split-oxygen.md` structure with placeholder tasks.

`templates/edit-mode-test.cs`: a single failing test. Uses `{{RootNamespace}}` so the project's root namespace can be set later (in `docs/process/unity-patterns.md` Section 1) without re-templating:

```csharp
using NUnit.Framework;
using {{RootNamespace}}.{{Name}};

namespace {{RootNamespace}}.{{Name}}.Tests
{
    public class {{Name}}SystemTests
    {
        [Test]
        public void Tick_BaselineCondition_ProducesExpectedResult()
        {
            Assert.Fail("Implement the first formula assertion for {{Name}}System.");
        }
    }
}
```

`templates/registry-block.yaml`:

```yaml
mechanics:
  - id: MECH-{{NAME}}
    title: {{Name}}
    kind: experience
    pillars: [{{pillars}}]
    doc: docs/gdd/mechanics/{{name-kebab}}.md
    implemented_by: [SYS-{{NAME}}]
    config: [CFG-{{NAME}}]
    status: active

systems:
  - id: SYS-{{NAME}}
    name: {{Name}}System
    doc: docs/sdd/systems/{{name-kebab}}.md
    classes: [CLASS-{{Name}}System]
    config: [CFG-{{NAME}}]
    publishes: []
    subscribes: []

configs:
  - id: CFG-{{NAME}}
    name: {{Name}}Config
    type: ScriptableObject
    doc: docs/tdd/classes/{{Name}}System.md#{{name-kebab}}config
```

- [ ] **Step 3: Verify all template files exist**

```bash
cd /Users/ignaciocastro/ia/LastBreath \
  && for f in SKILL.md templates/gdd-mechanic.md templates/sdd-system.md templates/tdd-class.md templates/plan.md templates/edit-mode-test.cs templates/registry-block.yaml; do test -f .claude/skills/scaffold-mechanic/$f && echo "OK $f" || echo "MISSING $f"; done
```
Expected: seven `OK` lines.

- [ ] **Step 4: Verify genericity**

```bash
cd /Users/ignaciocastro/ia/LastBreath \
  && ! grep -ri "oxygen\|agitation\|presence\|flashlight" .claude/skills/scaffold-mechanic/
```
Expected: success (no matches).

- [ ] **Step 5: Smoke test (manual)**

Per spec §9.2, run the skill on `name: SmokeTest, pillars: [PILLAR-01]` (in a scratch context if available). Verify all five files appear and the YAML block prints. Then `git clean -fd` the scratch artifacts before committing.

- [ ] **Step 6: Commit**

```bash
cd /Users/ignaciocastro/ia/LastBreath && git add .claude/skills/scaffold-mechanic/ && git commit -m "$(cat <<'EOF'
skills: add scaffold-mechanic skill + templates

Adds .claude/skills/scaffold-mechanic/ with SKILL.md and six templates
(GDD mechanic, SDD system, TDD class, plan, EditMode test, registry
YAML block).

The skill materialises docs/process/adding-a-mechanic.md for a new
mechanic. Refuses to overwrite existing files. Never auto-edits the
registry — prints the YAML block to chat for the user to paste.

Templates use FooSystem-style placeholders only; no game-specific
terms.

Spec: docs/superpowers/specs/2026-05-05-ai-augmented-workflow-design.md §5.3.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 12: Synthetic violation fixtures

**AC-11, AC-12, AC-16.** Six fixtures, each named for the rule it triggers. Each must produce the expected `rule_id` from `code-reviewer`.

**Files:**
- Create: `tests/process/reviewer/forbidden-api.diff`
- Create: `tests/process/reviewer/missing-event-unsubscribe.diff`
- Create: `tests/process/reviewer/unregistered-class.diff`
- Create: `tests/process/reviewer/out-of-scope.diff`
- Create: `tests/process/reviewer/formula-without-test.diff`
- Create: `tests/process/reviewer/monobehaviour-formula.diff`
- Create: `tests/process/reviewer/README.md`

- [ ] **Step 1: Create directory**

```bash
mkdir -p /Users/ignaciocastro/ia/LastBreath/tests/process/reviewer
```

- [ ] **Step 2: Write each fixture**

Each `.diff` file is a unified-diff snippet that, if applied to a hypothetical `_Project/` tree, would violate exactly one rule. The fixture file itself is plain text the reviewer can read with `Read` and parse. Each fixture starts with a YAML preamble naming the expected `rule_id`:

Example for `forbidden-api.diff`:

```diff
# expected_rule_id: GAMEPLAY-CODE-NO-FINDOBJECTOFTYPE
# applies_under: src/Assets/_Project/Systems/
--- a/src/Assets/_Project/Systems/FooSystem.cs
+++ b/src/Assets/_Project/Systems/FooSystem.cs
@@ -10,6 +10,9 @@ public class FooSystem : MonoBehaviour
     private void Awake()
     {
+        var bar = FindObjectOfType<BarSystem>();
+        bar.DoThing();
     }
 }
```

Repeat the same structure for the other five fixtures. The `monobehaviour-formula.diff` fixture must show a numeric formula computed inside a `MonoBehaviour.Update()` with no plain-C# logic class extracted — the diff that `UNITY-PATTERN-MONOBEHAVIOUR-SPLIT` should fire on.

- [ ] **Step 3: Write `tests/process/reviewer/README.md`**

```markdown
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
```

- [ ] **Step 4: Verify all six fixtures + README exist**

```bash
cd /Users/ignaciocastro/ia/LastBreath \
  && ls tests/process/reviewer/ \
  && test $(ls tests/process/reviewer/*.diff | wc -l) -eq 6
```
Expected: seven entries (six diffs + README); the count assertion passes.

- [ ] **Step 5: Verify each fixture declares its expected rule_id**

```bash
cd /Users/ignaciocastro/ia/LastBreath \
  && for f in tests/process/reviewer/*.diff; do head -1 "$f" | grep -q "expected_rule_id:" && echo "OK $f" || echo "MISSING preamble in $f"; done
```
Expected: six `OK` lines.

- [ ] **Step 6: Run the fixtures against the reviewer (smoke check)**

For each fixture, dispatch the `code-reviewer` subagent (advisory mode, scoped to the fixture's diff) and confirm the response contains the declared `expected_rule_id`. Manual loop:

```bash
cd /Users/ignaciocastro/ia/LastBreath \
  && for f in tests/process/reviewer/*.diff; do echo "=== $f ==="; head -2 "$f"; done
```

For each, run the reviewer (out of band) and record `PASS`/`FAIL` next to the fixture name. Document failures by tightening either the rule prose or the reviewer prompt; re-run.

- [ ] **Step 7: Commit**

```bash
cd /Users/ignaciocastro/ia/LastBreath && git add tests/process/reviewer/ && git commit -m "$(cat <<'EOF'
tests: add synthetic violation fixtures for code-reviewer

Adds six fixtures under tests/process/reviewer/:
- forbidden-api.diff           → GAMEPLAY-CODE-NO-FINDOBJECTOFTYPE
- missing-event-unsubscribe.diff → GAMEPLAY-CODE-EVENT-SYMMETRY
- unregistered-class.diff      → REGISTRY-DRIFT-UNREGISTERED-CLASS
- out-of-scope.diff            → PLAN-ADHERENCE-OUT-OF-SCOPE
- formula-without-test.diff    → TEST-STANDARDS-FORMULA-NEEDS-EDITMODE
- monobehaviour-formula.diff   → UNITY-PATTERN-MONOBEHAVIOUR-SPLIT

Each fixture starts with a YAML preamble naming the rule it must
trigger. The README documents how to run them and when. No CI yet —
manual loop for now; promote to CI when Unity batchmode lands.

Spec: docs/superpowers/specs/2026-05-05-ai-augmented-workflow-design.md §9.1.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 13: Final verification — all 16 acceptance criteria

**Files:**
- (read-only verification)

- [ ] **Step 1: AC-1 — layer paths resolve**

```bash
cd /Users/ignaciocastro/ia/LastBreath \
  && for p in $(grep -oE "docs/(gdd|sdd|tdd)/[^#[:space:]]+" docs/registry/architecture.yaml | sort -u); do test -f "$p" && echo "OK $p" || echo "MISSING $p"; done | grep -c "MISSING"
```
Expected: `0`.

- [ ] **Step 2: AC-2 — registry mechanic counts**

```bash
cd /Users/ignaciocastro/ia/LastBreath \
  && python3 -c "
import yaml
d = yaml.safe_load(open('docs/registry/architecture.yaml'))
active = [m for m in d['mechanics'] if m.get('status','active') == 'active']
deprecated = [m for m in d['mechanics'] if m.get('status') == 'deprecated']
assert len(active) == 5, f'expected 5 active, got {len(active)}'
assert len(deprecated) == 6, f'expected 6 deprecated, got {len(deprecated)}'
assert any(m['id'] == 'MECH-INTERACTION' for m in active)
assert any(m['id'] == 'MECH-ILUMINACION' and m['status'] == 'deprecated' for m in d['mechanics'])
print('AC-2 OK')
"
```
Expected: `AC-2 OK`.

- [ ] **Step 3: AC-3, AC-4, AC-5, AC-6, AC-7, AC-8, AC-9, AC-10, AC-13, AC-14, AC-15 — file existence and rule references**

```bash
cd /Users/ignaciocastro/ia/LastBreath \
  && for f in \
    docs/registry/glossary.md \
    docs/README.md \
    docs/plans/README.md \
    docs/engine-reference/README.md \
    .claude/agents/README.md \
    .claude/rules/README.md \
    .claude/agents/code-reviewer.md \
    .claude/skills/review-gameplay/SKILL.md \
    .claude/skills/scaffold-mechanic/SKILL.md \
    docs/process/adding-a-mechanic.md \
    docs/process/unity-patterns.md \
    .claude/skills/unity-patterns/SKILL.md ; do
    test -f "$f" && echo "OK $f" || echo "MISSING $f"
  done | tee /tmp/ac-files.log \
  && ! grep -q MISSING /tmp/ac-files.log
```
Expected: 12 `OK` lines; the negated grep returns success.

- [ ] **Step 4: AC-12 — genericity grep**

```bash
cd /Users/ignaciocastro/ia/LastBreath \
  && ! grep -ri "oxygen\|agitation\|presence\|flashlight" .claude/agents/code-reviewer.md .claude/skills/ docs/process/
```
Expected: success (no matches).

- [ ] **Step 5: AC-11, AC-16 — fixtures exist and one is `UNITY-PATTERN-*`**

```bash
cd /Users/ignaciocastro/ia/LastBreath \
  && test $(ls tests/process/reviewer/*.diff | wc -l) -eq 6 \
  && grep -l "UNITY-PATTERN-" tests/process/reviewer/*.diff
```
Expected: count `6`; one filename listed.

- [ ] **Step 6: Print final acceptance summary**

```bash
cd /Users/ignaciocastro/ia/LastBreath \
  && echo "=== Acceptance summary ===" \
  && git log --oneline | head -15
```
Expected: 12 task commits (Tasks 1–12) on top of the initial commit from Task 0 — 13 commits total before this task's plan-done commit lands in Step 7.

- [ ] **Step 7: Mark plan as done**

Add at the top of this plan:

```yaml
status: done
done_date: <YYYY-MM-DD>
```

Commit:

```bash
cd /Users/ignaciocastro/ia/LastBreath && git commit -am "$(cat <<'EOF'
plan: mark plan 002 done

All 16 acceptance criteria verified. Doc structure restructured,
English IDs in registry, Unity patterns reference + skill shipped,
code-reviewer subagent + slash command live, gameplay-programmer
must-rules in place, generic mechanic recipe + scaffold skill ready,
six synthetic fixtures verified.

Spec: docs/superpowers/specs/2026-05-05-ai-augmented-workflow-design.md.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Notes for the executing engineer

- **Each task ends in exactly one commit.** If a task has multiple logical edits, stage them together and commit once — the commit message is the entry on the timeline.
- **If a verify step fails, do NOT skip it.** Either fix the underlying file or amend the plan. Never check a box you cannot defend.
- **The reviewer subagent is read-only by definition.** If anywhere in execution it appears to have edited a file, that's a bug — stop and surface to user.
- **The recipe doc is the contract for the scaffold skill.** If they disagree, the recipe wins.
- **English-only across every file you touch**, including commit messages.
- **Skills referenced by `@` syntax**: `superpowers:test-driven-development` is implicit for any code-bearing task in this codebase, but this plan is doc-only — TDD applies via the synthetic fixtures (they are the tests).

## Completion criteria

Plan is done when:
1. All 16 acceptance criteria from spec §11 verify.
2. All 13 tasks above are checked off.
3. Final commit (Task 13 Step 7) lands on `main`.
4. The six fixtures all return their expected `rule_id` from `code-reviewer`.
