---
id: ADR-0008-asset-pipeline
type: decision
status: accepted
date: 2026-05-12
related: [ADR-0007, PLAN-006, SCENE-CORREDOR-C7]
---

# ADR 0008: Asset pipeline — Blender → staging → human approval → Unity

## Context

ADR-0007 introduced the `level-designer` role and the `unity-mcp`-driven scene-composition loop. That loop assumes art assets exist; the PoC has none. Authoring 3D assets is a different discipline with different tools (`blender-mcp`, glTF export) and different invariants (licence provenance, source-vs-import sync). Wiring it into the methodology has three load-bearing constraints:

1. **Single human approver.** The user vets every asset before it touches the Unity project. No agent and no script approves on his behalf.
2. **No forgetting.** When an asset sits pending in staging, the next session must surface it. When a `.glb` in staging drifts from the imported copy, the next commit must fail loudly. This is the **agentic forcing** principle the user explicitly asked for: process bugs are caught by hooks and scripts, not by remembering.
3. **Auditable provenance.** Every asset must declare where it came from (Polyhaven id, generative prompt, Python recipe, or hand-authoring), and the licence under which it ships. Reviewers can grep the manifest; `code-reviewer` can enforce the constraint.

Four authoring patterns were considered:

- **Blender-MCP direct, no staging.** AI drives Blender, exports straight into `src/Assets/_Project/Art/`. Rejected — no human gate, no provenance, no audit. The whole point of the pipeline is the gate.
- **Staging + manual approve via PR.** Every batch of assets is its own GitHub PR. Rejected for a solo dev — too much ceremony per asset, and the audit happens twice (once on PR, once on commit).
- **Staging + `Quarantine/` inside `src/Assets/`.** Assets land in `src/Assets/Quarantine/` and get moved manually. Rejected — Unity auto-generates `.meta` files inside `src/Assets/`, so the staging area would commit metadata noise into history.
- **Staging outside `src/Assets/` + manifest + `[MenuItem]` import (chosen).** Assets sit in `art/<asset>/` with a sidecar `manifest.yaml`. A human-approval step flips `approved: true`. The Unity `[MenuItem("LastBreath/Art/Import Approved Assets")]` is the only path into `src/Assets/_Project/Art/`. Drift between source and import is detected by a hash comparison.

## Decision

Adopt **staging + manifest + human-approval gate + hash-checked sync**, with a strict two-role split.

### Roles

- **`asset-designer` (new).** Owns `art/**`. Drives `blender-mcp` with full authoring capabilities (`download_polyhaven_asset`, `execute_blender_code`, `set_texture`, file open/save/export, screenshot). Produces `.glb` files + screenshots + a `manifest.yaml` per asset. Does **not** touch `.unity`, `.layout.yaml`, or `src/Assets/_Project/Art/`.
- **`level-designer` (extended).** Gains one Unity verb: `[MenuItem("LastBreath/Art/Import Approved Assets")]`. Gains a *read-only* subset of `blender-mcp` for cross-tool verification (`get_scene_info`, `get_object_info`, `get_viewport_screenshot`, read-only `execute_blender_code`). Still cannot author in Blender.

### Authoring artefact

`art/<asset>/` contains:

- `manifest.yaml` — provenance + status + import metadata (schema in `docs/process/asset-design.md` `§5`).
- `<asset>.glb` — the canonical binary export.
- `<asset>.blend` (optional) — Blender source, if the asset is `hand_authored_user` or non-trivial `execute_blender_code`. Committed under `git-lfs` if size warrants.
- `screenshots/preview-front.png` and `screenshots/preview-3q.png` — two viewport captures.

### Sourcing

Allowed sources, declared in `manifest.source`:

- `polyhaven` — CC0 library via `download_polyhaven_asset`. No licence risk.
- `execute_blender_code` — AI-authored Python that builds the mesh inside Blender. The script is committed alongside the `.glb`.
- `hand_authored_user` — the user modelled it; the MCP exports and writes the manifest.

Sketchfab and AI-generative (Hyper3D, Hunyuan3D) are explicitly **not** in scope for this ADR. A follow-up ADR may add them once the licence-tracking fields they need are designed.

### Export format

Canonical: **glTF 2.0 binary (`.glb`)**. Covers PBR materials, lights (`KHR_lights_punctual`), and skinned animations in a single file. Unity's glTF importer is native from 2022.x. FBX is **not** the default; if a future asset cannot be expressed in glTF, that asset is preceded by a new ADR that justifies the second format.

### Approval gate

Two complementary mechanisms:

- **SessionStart hook.** `.claude/settings.json` wires `scripts/art-staging-queue.py` to fire at every session start. The script scans `art/*/manifest.yaml`, counts entries with `approved: pending`, and if `> 0` emits a system reminder ("PENDING ART APPROVALS: N. Run /art-approval-queue."). The user cannot start a session without seeing this.
- **Skill `/art-approval-queue`.** User-invocable. Lists pending manifests with provenance + screenshot filenames, offers `approve | reject | request-iteration` per asset, and writes the decision back into the manifest (sets `approved` + `approved_at` + `imported_hash` on approve).

No pre-commit hook in this ADR. The sync verifier is user-invoked via `/verify-art-sync`; pre-commit enforcement can be added by a later plan if drift becomes a recurring problem.

### Import gate

Approved assets are moved into `src/Assets/_Project/Art/` **exclusively** through `[MenuItem("LastBreath/Art/Import Approved Assets")]`. The MenuItem (implemented in `src/Assets/_Editor/Art/ApprovedAssetImporter.cs`, Wave B) is idempotent: it skips manifests whose `imported_at` is already set, copies the `.glb` to `manifest.target_unity_path`, configures the `ModelImporter` from `manifest.importer_settings`, and writes `imported_at` + `target_unity_guid` back to the manifest.

### Sync verification

Two layers:

- **Layer A — Python** (`scripts/check-art-sync.py`). Hash-only: for every manifest with `approved: true` and `imported_at != null`, compares `sha256(art/<asset>/<file>.glb)` against `manifest.imported_hash`. Also cross-checks: every reference in `docs/levels/**/*.layout.yaml` resolves to a path under `src/Assets/_Project/Art/` that has a manifest, and every file under `src/Assets/_Project/Art/` has a corresponding manifest. Exit code != 0 on drift.
- **Layer B — Unity** (`src/Assets/_Editor/Art/ArtSyncVerifier.cs`, Wave B). Adds `ModelImporter` setting verification against `manifest.importer_settings`.

The skill `/verify-art-sync` runs Layer A by default; `--deep` calls Layer B via `unity-mcp.menu.invoke`.

### Reviewer rules

`.claude/rules/asset-design.md` declares:

- `ASSET-DESIGN-NO-UNAPPROVED-IN-ASSETS` — a file under `src/Assets/_Project/Art/` exists only if its manifest is `approved: true` and `imported_at` is set.
- `ASSET-DESIGN-MANIFEST-REQUIRED` — every folder in `art/` has a `manifest.yaml` with the mandatory fields.
- `ASSET-DESIGN-LICENSE-DOCUMENTED` — `manifest.license` is non-empty and references a known licence (`CC0`, `CC-BY-*`, `custom`, etc.).
- `ASSET-DESIGN-PROVENANCE-DOCUMENTED` — `manifest.provenance` carries source-specific fields (Polyhaven id, recipe path, etc.).
- `ASSET-DESIGN-STAGING-DOESNT-LEAK` — paths under `art/` are not referenced from `.unity`, `.prefab`, or `.layout.yaml`.
- `ASSET-DESIGN-NO-UNITY-EDITS` — an asset-design diff does not touch `src/Assets/Scenes/**.unity` or `docs/levels/**`.
- `ASSET-DESIGN-SYNC-PARITY` — `scripts/check-art-sync.py` returns exit 0 for any commit that touches `art/**`, `src/Assets/_Project/Art/**`, or `docs/levels/**/*.layout.yaml`.

`.claude/rules/level-design.md` gains:

- `LEVEL-DESIGN-USES-APPROVED-ART-ONLY` — every mesh / prefab path a `.layout.yaml` references resolves to an asset whose manifest is `approved: true` and `imported_at != null`.
- `LEVEL-DESIGN-BLENDER-READ-ONLY` — the `level-designer` may call only the read-only subset of `blender-mcp` (listed in `docs/process/blender-mcp.md` `§4`). Authoring verbs are forbidden.

## Alternatives considered

- **No staging, MCP exports straight to `src/Assets/`.** Rejected because there is no human gate, and Unity auto-imports any file dropped into `src/Assets/` without provenance tracking.
- **Staging in `src/Assets/Quarantine/`.** Rejected because Unity generates `.meta` files inside `src/Assets/`, polluting the history.
- **PR-per-asset.** Rejected for a solo dev — overhead per asset is high and the audit happens twice.
- **No sync verifier.** Rejected; the source-vs-import drift is the single most likely failure mode of a two-tool pipeline, and the user explicitly asked for the check.
- **Reminder-based approval flow (the agent reminds the user to approve).** Rejected per the user's "agentic forcing" preference: forgetting is a methodology bug. The SessionStart hook is the correct mitigation, not an agent reminder.

## Consequences

- **Easy.** Staging is outside `src/Assets/`, so Unity ignores it. Provenance is one YAML per asset. The hook makes pending approvals impossible to miss. Hash-based sync is one short Python script. The role split means `code-reviewer` can audit asset work and level work as separate diffs.
- **Hard.** The user must run the `Import Approved Assets` menu every time something is approved (Wave B); until that menu exists, approved assets sit in staging without being usable. The `manifest.yaml` schema must evolve carefully — every new field is a change every existing manifest may need.
- **Accepted loss.** Manifests are hand-touched (by `/art-approval-queue`, by the importer), so a malformed manifest can poison the queue. `scaffold-asset` generates schema-correct stubs; `code-reviewer` validates them; both layers are necessary.
- **Mandatory tests** (added in Wave B):
  - `ApprovedAssetImporter_IsIdempotent` — EditMode, running the menu twice has no second-pass effect.
  - `ArtSyncVerifier_DetectsHashDrift` — EditMode, fabricates a drift and asserts the verifier reports it.

## Notes

The `manifest.yaml` schema in `docs/process/asset-design.md` `§5` is the binding contract. Wave B may extend it with per-prim overrides, animation clip imports, or LOD configuration; those extensions go through new fields, never renamed fields, per the project's stable-ID rule (`AGENTS.md` `§Global rules`).

If `blender-mcp` becomes unstable or is replaced, the `manifest.yaml` schema and the approval/import flow stay stable — only `docs/process/blender-mcp.md` and the relevant skill verbs change.
