---
name: verify-art-sync
user-invocable: true
description: Run the cross-tool sync verifier between art/ (Blender source) and src/Assets/_Project/Art/ (Unity imports). Layer A (Python, default) checks hashes and cross-references without Unity. Pass --deep to also invoke the Unity-side ArtSyncVerifier MenuItem (Wave B).
---

# verify-art-sync skill

## Purpose

Detects drift between Blender source assets in `art/` and their Unity-side imports in `src/Assets/_Project/Art/`. Drift means: the `.glb` was edited after approval, the imported file is missing, a layout references an unapproved asset, or the importer settings drifted from the manifest.

Two layers, per ADR-0008 `§Sync verification`.

## Args

- `--deep` (optional) — also invoke the Unity-side verifier (`[MenuItem("LastBreath/Art/Verify Sync")]`, Wave B) via `unity-mcp.menu.invoke`. Requires Unity to be running with `unity-mcp` connected. Without `--deep`, only Layer A runs.
- `--asset ART-*` (optional) — focus on a single asset. Default: scan everything.
- `--quiet` (optional) — print only violations and the summary line. Default: print per-asset progress.

## Behaviour

### Layer A (default, Python, no Unity)

Runs `python3 scripts/check-art-sync.py` with the same flags. The script:

1. Walks `art/*/manifest.yaml` and `docs/levels/**/*.layout.yaml`.
2. For each manifest with `approved: true && imported_at != null`:
    - Resolves `manifest.exports[0].path` (`<asset>.glb`).
    - Computes `sha256(<glb>)`.
    - Compares against `manifest.imported_hash`. Reports `hash_drift` on mismatch.
    - Resolves `manifest.target_unity_path`. Reports `target_missing` if the file does not exist.
3. For each `.layout.yaml`:
    - For every `prefab` / `mesh` reference under `src/Assets/_Project/Art/`:
        - Reports `unmanifested_target` if no manifest's `target_unity_path` matches.
        - Reports `unapproved_target` if the matching manifest has `approved != true` or `imported_at == null`.
4. For each file under `src/Assets/_Project/Art/**`:
    - Reports `unmanifested_target` if no manifest's `target_unity_path` matches.
5. Exits 0 if no violations, exit 1 otherwise.

### Layer B (`--deep`, Wave B)

1. Verify `unity-mcp` is connected (call a no-op verb; surface and stop if not).
2. Open the project in Unity (it should already be open if `unity-mcp` works).
3. Invoke `unity-mcp.menu.invoke("LastBreath/Art/Verify Sync")`.
4. Read the verifier's report. Append any `importer_setting_drift` entries to the Layer A output.

## Output

Structured (machine-readable):

```yaml
status: ok | issues_found
layer: A | A+B
violations:
  - kind: hash_drift | target_missing | unmanifested_target | unapproved_target | importer_setting_drift
    asset: ART-<NAME>
    file: <path>
    detail: <one sentence>
summary: <"all green" | "N violations across M assets">
```

## Failure modes

- Missing dependencies (Python yaml package not installed): the Layer A script prints `pip install pyyaml` and exits 2.
- Unity not connected when `--deep` is set: skill stops, does not silently fall back to Layer A — that would hide drift the user expected to be checked.
- Manifest malformed (missing `target_unity_path`): the verifier reports `manifest_malformed` with the offending file and exits 1.

## Constraints

- Read-only. Never edits manifests, never moves files, never touches Unity assets.
- Honest about scope: when running Layer A only, the output's `layer: A` makes clear that importer settings were not verified.

## See also

- `docs/decisions/0008-asset-pipeline.md` `§Sync verification`.
- `docs/process/asset-design.md` `§8`.
- `scripts/check-art-sync.py` — the Python implementation Layer A wraps.
- `.claude/rules/asset-design.md` — `ASSET-DESIGN-SYNC-PARITY` is the rule this verifier enforces.
- `.claude/skills/review-asset/` — the strict-mode reviewer that calls this verifier automatically.
