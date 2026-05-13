---
id: PLAN-006
type: plan
layer: process
status: done
done_date: 2026-05-12
related: [ADR-0007, ADR-0008, PROCESS-LEVEL-DESIGN, PROCESS-ASSET-DESIGN, PLAN-011]
followups: [PLAN-011]
---

# Plan 006 — Asset pipeline (Blender → staging → human approval → Unity)

> **Wave A is shipped (methodology, scripts, rules, skills, registry section).** Wave B (the Unity-side `ApprovedAssetImporter` MenuItem, `ArtSyncVerifier`, `blender-mcp` registration in `.mcp.json`, first dogfood asset) was originally listed as out-of-scope here and is **now tracked as `PLAN-011`** so the validation gate in `PLAN-010` can run before any art lands.

Extends the level-design methodology (PLAN-005-equivalent introduced by ADR-0007) with an upstream art pipeline. Adds the `asset-designer` role, the `blender-mcp` authoring surface, the staging-and-approval gate, and the cross-tool sync verifier.

## Context

The PoC needs 3D assets (props, panels, lights, set pieces) to populate the corridor C-7 scene. The `level-designer` composes scenes but does not author meshes. We want an upstream role that drives Blender via `blender-mcp` to produce `.glb` assets, with a hard human-approval gate before anything lands in `src/Assets/_Project/Art/`. The flow must be **agentic**: forgetting to approve, drifting between Blender source and Unity import, or referencing an unapproved asset from a layout — all must be blocked by hooks, scripts, or menu items, not by reminders.

## Decisions taken (recorded in ADR-0008)

1. **Two-role split.** New `asset-designer` owns Blender authoring + staging. `level-designer` gains one import verb (`Import Approved Assets` MenuItem) and read-only `blender-mcp` access for sanity-checking. No role overlap on authoring.
2. **glTF 2.0 (`.glb`) is the canonical export.** Covers meshes + PBR materials + lights (`KHR_lights_punctual`) + skinned rigs in a single binary. Unity has a native glTF importer from 2022.x. FBX is not the default; if a future asset cannot be expressed in glTF, that asset opens an ADR.
3. **Three sourcing options.** `polyhaven` (CC0), `execute_blender_code` (AI-authored Python), `hand_authored_user` (the user models in Blender and asks the MCP to integrate/export). Sketchfab and AI-generative (Hyper3D, Hunyuan) are not yet allowed; a follow-up ADR can add them with the licence and provenance fields they need.
4. **Staging area `art/<asset>/` with a `manifest.yaml`.** Every asset has provenance (source, licence, prompt or recipe), `imported_hash` (sha256 of the `.glb` at approval time), and `approved: pending | true | false`. Nothing reaches `src/Assets/_Project/Art/` without `approved: true`.
5. **SessionStart hook for the approval queue.** `scripts/art-staging-queue.py` runs every session start, scans pending manifests, and injects a system reminder if any are open. The pre-commit hook is not added now; sync is user-invoked via `/verify-art-sync`.
6. **Two-layer sync verifier.** Layer A (Python, `scripts/check-art-sync.py`) does hash-only + cross-reference checks without Unity. Layer B (`[MenuItem("LastBreath/Art/Verify Sync")]`, Wave B) adds importer-setting checks inside Unity. The skill `verify-art-sync` runs Layer A by default.
7. **New ID prefix `ART-*`.** New section `art_assets:` in `docs/registry/architecture.yaml`. Identity-only entries; runtime data stays in the manifest.

## Authoring flow (canon)

```
asset-designer side:                                                            
    goal stated → blender-mcp iterates (Polyhaven / execute_blender_code /       
                  hand_authored_user) → snapshot ritual:                         
                    1. scene.save() in Blender                                   
                    2. export .glb to art/<asset>/                       
                    3. write manifest.yaml with approved: pending + provenance    
                    4. capture two screenshots (front + 3/4)                      
                  → commit bundle in art/                               
                                                                                  
human approval gate:                                                              
    SessionStart hook surfaces pending. User runs /art-approval-queue, sees      
    manifest + screenshots, decides approve | reject | request-iteration.        
    Approve writes approved: true + approved_at + imported_hash (sha256 of .glb). 
                                                                                  
level-designer side:                                                              
    Runs [MenuItem("LastBreath/Art/Import Approved Assets")]. Editor utility:    
      - scans art/                                                       
      - for each manifest where approved: true and imported_at is null:          
        - copies the .glb to manifest.target_unity_path                          
        - configures the ModelImporter from manifest.importer_settings           
        - writes imported_at + target_unity_guid back to manifest                
    Then composes scene normally via unity-mcp, referencing the imported asset.   
                                                                                  
sync verification (anytime):                                                      
    /verify-art-sync runs scripts/check-art-sync.py — sha256(.glb) matches       
    manifest.imported_hash, every layout reference resolves, every imported      
    asset has a manifest. --deep additionally invokes the Unity MenuItem.        
```

## Deliverables (Wave A — methodology only, no Unity yet)

| Path | Action |
|---|---|
| `docs/decisions/0008-asset-pipeline.md` | create |
| `docs/process/asset-design.md` | create |
| `docs/process/blender-mcp.md` | create |
| `.claude/agents/asset-designer.md` | create |
| `.claude/agents/level-designer.md` | update — add `Import Approved Assets` verb + read-only `blender-mcp` access |
| `.claude/rules/asset-design.md` | create |
| `.claude/rules/level-design.md` | update — add `LEVEL-DESIGN-USES-APPROVED-ART-ONLY` and `LEVEL-DESIGN-BLENDER-READ-ONLY` |
| `.claude/skills/scaffold-asset/SKILL.md` + `templates/` | create |
| `.claude/skills/asset-design-session/SKILL.md` | create |
| `.claude/skills/art-approval-queue/SKILL.md` | create |
| `.claude/skills/review-asset/SKILL.md` | create |
| `.claude/skills/verify-art-sync/SKILL.md` | create |
| `scripts/art-staging-queue.py` | create (SessionStart hook target) |
| `scripts/check-art-sync.py` | create (Layer A sync verifier) |
| `.claude/settings.json` | create — wire SessionStart hook to `art-staging-queue.py` |
| `art/.gitkeep` | create |
| `docs/registry/glossary.md` | update — `asset-designer`, `asset manifest`, `staging area`, `approval gate`, `art asset`, `glTF`, `provenance` |
| `docs/registry/architecture.yaml` | update — `ART-*` in the ID convention header, new `art_assets: []` section |
| `AGENTS.md` | update — `asset-designer` role row, required reading for art work, `blender-mcp` in the MCP table |
| `.claude/agents/code-reviewer.md` | update — `ASSET-DESIGN-*` rule prefix + recent additions table |
| `.claude/agents/README.md` | update — `asset-designer.md` row |
| `docs/plans/README.md` | update — add the row for plan 006 |

## Deliverables (Wave A follow-ups — added 2026-05-12 to close agentic-forcing gaps)

These items were not in the original Wave A list but were added before opening Wave B, after the first methodology audit found four rules that were prose-only. They are now mechanically enforced.

| Path | Action | Closes |
|---|---|---|
| `scripts/check-manifest-schema.py` | create — schema validator (mandatory fields, ID-in-registry, license legend, source-specific provenance) | `ASSET-DESIGN-MANIFEST-REQUIRED`, `ASSET-DESIGN-LICENSE-DOCUMENTED`, `ASSET-DESIGN-PROVENANCE-DOCUMENTED` |
| `scripts/git-hooks/pre-commit` | create — runs `check-manifest-schema.py` + `check-art-sync.py` when staged paths touch art/level surfaces; opt-in via `git config core.hooksPath scripts/git-hooks` | `ASSET-DESIGN-SYNC-PARITY` (now blocks commits) |
| `scripts/add-art-asset-to-registry.py` | create — idempotent registry append; called by `/scaffold-asset` instead of asking the user to copy-paste | end of manual paste step |
| `.claude/skills/scaffold-asset/SKILL.md` | update — Step 4 now invokes `add-art-asset-to-registry.py`; constraint flipped from "never auto-edits" to "edits **only** via the helper" | same |
| `.claude/settings.json` | update — add a `PostToolUse` hook that runs `check-art-sync.py --quiet` after `mcp__blender-mcp__` write verbs; advisory, does not block | `ASSET-DESIGN-SYNC-PARITY` (live drift signal during a Blender session) |
| `AGENTS.md` | update — new "Mechanical enforcement (hooks and pre-commit)" section listing every automated surface and the one-line install command | discoverability |

## Deliverables (Wave B — out of scope for this plan; next plan)

- Install `blender-mcp` (project-scope) and register it in `.mcp.json`.
- Author `src/Assets/_Editor/Art/ApprovedAssetImporter.cs` (`[MenuItem("LastBreath/Art/Import Approved Assets")]`).
- Author `src/Assets/_Editor/Art/ArtSyncVerifier.cs` (`[MenuItem("LastBreath/Art/Verify Sync")]`, the Layer B counterpart).
- Author the first real asset (the maintenance-room panel of `SCENE-CORREDOR-C7`) as dogfood.

## Verification (Wave A end-to-end)

1. **SessionStart hook fires.** Open a fresh session in the repo; the hook runs `python3 scripts/art-staging-queue.py` and prints `PENDING ART APPROVALS: 0` (no pending yet). Manually create `art/test/manifest.yaml` with `approved: pending`; reopen session; the hook reports `PENDING ART APPROVALS: 1`. Delete the test folder.
2. **`scaffold-asset` writes a valid bundle.** Run the skill with a fake asset id; expect `art/<name>/manifest.yaml` + `screenshots/.gitkeep` written, registry YAML block printed, no `architecture.yaml` edits.
3. **`art-approval-queue` triages correctly.** With one pending manifest, the skill lists it with provenance + screenshot filenames and offers approve / reject / iterate.
4. **`verify-art-sync` runs clean on an empty repo.** No manifests, no Unity assets, no layout refs — exit 0.
5. **`verify-art-sync` detects drift.** Add a fake approved manifest pointing at a missing target path; expect exit != 0 with a `target_missing` violation.
6. **`code-reviewer` knows the new rules.** Dispatch with a manufactured diff that puts a file under `src/Assets/_Project/Art/` with no manifest; expect `ASSET-DESIGN-NO-UNAPPROVED-IN-ASSETS` to fire.
7. **`AGENTS.md` renders the new role row** and lists `blender-mcp` in the MCP table.
8. **`docs/plans/README.md`** lists plan 006 as `active`.

## Open questions left for execution

- Exact `manifest.yaml` schema — Wave A locks fields the methodology needs (id, name, purpose, source, license, provenance, exports, screenshots, approved, approved_at, imported_hash, imported_at, target_unity_path, importer_settings, notes). Edge fields (e.g., per-prim material overrides, animation clip imports) get added by the first real asset in Wave B.
- Exact importer settings encoding — `manifest.importer_settings` is currently a free-form mapping (e.g., `{ scale_factor: 1.0, generate_lights: true, import_animations: false }`). Wave B's `ApprovedAssetImporter` reads this map and calls the matching `ModelImporter` setters; if a setter is missing, the importer logs a warning and falls back to Unity's default.
- Whether screenshots are stored as PNGs in `art/<asset>/screenshots/` (chosen) vs hashed into a separate gallery folder. Default: PNGs in-tree; the `.gitkeep` keeps the folder live before the first commit.
