# MCP Servers — Versions & Install

> This file is the contract for every MCP server wired into the Claude Code session. Every pin is exact, not a range. Bumps are plan-gated (see ADR-0009 §MCP servers and the global `no-stale-APIs` rule in `AGENTS.md`).

The committed `.mcp.json` mirrors these pins. `architecture.yaml::tooling.mcp_servers` mirrors the same. `scripts/check-runtime-versions.py` cross-checks the three sources at every SessionStart.

## Targets (pinned)

| Server | Source | Pin | Pin type |
|---|---|---|---|
| `context7` | `@upstash/context7-mcp` (npm) | `1.0.14` | npm tag |
| `unity-mcp` | `justinpbarnett/unity-mcp` (GitHub) | `<commit-sha>` (set at first install) | git commit |
| `blender-mcp` | upstream `blender-mcp` (GitHub) | `<commit-sha>` (set at first install) | git commit |

`<commit-sha>` placeholders are filled by the `unity-specialist` (for `unity-mcp`) and the `asset-designer` (for `blender-mcp`) at first install and committed back into this file and `architecture.yaml::tooling.mcp_servers`. Until they are filled, the SessionStart drift script emits an advisory warning (`mcp pin missing for <server>`) but does not block.

Compatibility:

| Server | Compatible with |
|---|---|
| `context7@1.0.14` | Node 20+, Claude Code 1.x |
| `unity-mcp@<sha>` | Unity `6000.0.32f1` (LTS pin), .NET Standard 2.1 |
| `blender-mcp@<sha>` | Blender `5.1.0` (with 4.x LTS fallback) |

## Install — `context7`

`.mcp.json` should pin the npm version explicitly (no `npx -y` latest-fetch):

```json
{
  "mcpServers": {
    "context7": {
      "command": "npx",
      "args": ["-y", "@upstash/context7-mcp@1.0.14"]
    }
  }
}
```

Verify:

```bash
npx -y @upstash/context7-mcp@1.0.14 --version
# Expected: 1.0.14
```

## Install — `unity-mcp`

Follow the upstream README at `justinpbarnett/unity-mcp` **at the pinned commit**:

```bash
git clone https://github.com/justinpbarnett/unity-mcp.git
cd unity-mcp
git checkout <commit-sha>          # from this file
# Follow upstream README from this point — install the Unity package and the bridge.
```

Pinning by commit (not tag) is intentional: upstream tags `0.x` move; commits do not.

Verify (inside the Unity editor, after the bridge connects):

- `Window → MCP → Status` shows `Connected to bridge`.
- Bridge process logs `unity-mcp <commit-sha> ready`.

## Install — `blender-mcp`

Follow the upstream `blender-mcp` README **at the pinned commit**. Two parts:

1. **Python bridge** (the MCP server):
   ```bash
   git clone https://github.com/<upstream>/blender-mcp.git
   cd blender-mcp
   git checkout <commit-sha>
   # Install per upstream README (uv / pip / pipx).
   ```
2. **Blender add-on**:
   - Open Blender 5.1.
   - `Edit → Preferences → Get Extensions → Install from Disk...` → select the `blender-mcp` add-on `.zip` from the cloned repo.
   - Enable the add-on. The N-panel shows a `BlenderMCP` tab.

Verify:

- The N-panel `BlenderMCP` tab shows `Connected` after the bridge starts.
- `scripts/check-runtime-versions.py --quiet` returns clean for the `blender_mcp.pin` field.

## How to confirm the running version matches the pin

```bash
python3 scripts/check-runtime-versions.py --quiet
```

The script reads `.mcp.json` and (when reachable) the running bridge process metadata. It does not start servers — it inspects the committed config and surfaces drift between `architecture.yaml`, this file, and `.mcp.json`.

## Bumping policy

A bump plan for any MCP server lists:

1. **Why** — what feature or fix you need; cite the upstream commit log or issue.
2. **Compatibility check** — does the new pin still match the Unity / Blender row above? If not, the bump becomes a paired bump (Unity LTS + `unity-mcp` together, or Blender + `blender-mcp` together).
3. **Smoke** — run one canonical session per affected role: a level-design session for `unity-mcp`, an asset-design session for `blender-mcp`. Both must finish without an MCP-side error.
4. **Update three places in one diff**: this file, `architecture.yaml::tooling.mcp_servers`, and `.mcp.json`.

Bypass: there is no bypass. An MCP that fails to start should be debugged or rolled back, not skipped — agentic forcing means the next session must see the same versions the diff declared.
