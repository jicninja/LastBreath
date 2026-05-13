# scripts/git-hooks

Project-shipped git hooks. Opt-in per clone with one command:

```
git config core.hooksPath scripts/git-hooks
```

Once enabled, hooks fire on the relevant git events. To disable, run:

```
git config --unset core.hooksPath
```

## Active hooks

### `pre-commit`

Runs the pipeline validators when a commit stages paths under any of:

- `art/**`
- `src/Assets/_Project/Art/**`
- `src/Assets/_Project/Prefabs/**`
- `src/Assets/Scenes/**`
- `docs/levels/**/*.layout.yaml`
- `src/ProjectSettings/TagManager.asset`
- `docs/registry/architecture.yaml`
- `src/Assets/_Project/Scripts/**`

The hook chains three scripts:

1. `scripts/check-manifest-schema.py --quiet` — mechanical enforcement of `ASSET-DESIGN-MANIFEST-REQUIRED`, `ASSET-DESIGN-LICENSE-DOCUMENTED`, `ASSET-DESIGN-PROVENANCE-DOCUMENTED`.
2. `scripts/check-art-sync.py --quiet` — mechanical enforcement of `ASSET-DESIGN-SYNC-PARITY` (Layer A).
3. `scripts/check-prefab-discipline.py --quiet` — mechanical enforcement of `LEVEL-DESIGN-GPU-INSTANCING-ENABLED`, `LEVEL-DESIGN-TAGS-REGISTERED`, `GAMEPLAY-CODE-NO-TAG-STRING-LITERALS`.

A non-zero exit from any of the three blocks the commit with a readable summary and the diagnostic commands to run without `--quiet`.

If the staged diff does not touch any of the watched paths, the hook is a no-op.

### Material opt-out for GPU instancing

If a material legitimately should not have GPU instancing (transparent particle, sprite, third-party shader without instancing pragmas), document it next to the material:

```
src/Assets/_Project/Art/<Category>/Foo.mat
src/Assets/_Project/Art/<Category>/Foo.mat.instancing-opt-out   # one-line reason
```

The verifier reads the sidecar and accepts the opt-out.

### Emergency bypass

```
LASTBREATH_SKIP_ART_HOOK=1 git commit ...
```

Use only when the commit cannot wait (e.g., reverting a bad merge). The reviewer should still flag the underlying violation in the PR.

## Related

- `.claude/settings.json` — wires the live (non-commit) hooks: `SessionStart` (pending-approvals nudge) and `PostToolUse` (advisory drift check after `blender-mcp` write verbs).
- `docs/plans/006-asset-pipeline-blender.md` — the plan that introduced these surfaces.
- `.claude/rules/asset-design.md` — the rules these scripts enforce.
