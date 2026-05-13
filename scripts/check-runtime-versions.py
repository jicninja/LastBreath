#!/usr/bin/env python3
"""Runtime version drift verifier — declared vs on-disk parity.

Cross-checks the pinned versions declared in:
  - docs/registry/architecture.yaml::tooling
  - docs/engine-reference/unity/VERSION.md
  - docs/engine-reference/blender/VERSION.md
  - docs/engine-reference/mcp/VERSIONS.md
  - .mcp.json

…against the on-disk truth (when the project is bootstrapped):
  - src/ProjectSettings/ProjectVersion.txt
  - src/Packages/manifest.json

Handles "not yet bootstrapped" gracefully — missing files are a `skip`, not an
error. The SessionStart hook runs this advisory; it never blocks tool calls.

Schema: docs/registry/architecture.yaml::tooling.
Rules: ADR-0009 §Decision (Drift verification).
Rationale: ADR-0009 §Context, ADR-0003 (soft enforcement).

Exit 0 if clean (or skipped), 1 if any drift, 2 on infrastructure error.

Usage:
  python3 scripts/check-runtime-versions.py
  python3 scripts/check-runtime-versions.py --quiet
  python3 scripts/check-runtime-versions.py --json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.stderr.write(
        "check-runtime-versions: pyyaml not installed. Run: pip install pyyaml\n"
    )
    sys.exit(2)

REPO_ROOT = Path(__file__).resolve().parent.parent
ARCHITECTURE = REPO_ROOT / "docs" / "registry" / "architecture.yaml"
UNITY_VERSION_MD = REPO_ROOT / "docs" / "engine-reference" / "unity" / "VERSION.md"
BLENDER_VERSION_MD = REPO_ROOT / "docs" / "engine-reference" / "blender" / "VERSION.md"
MCP_VERSIONS_MD = REPO_ROOT / "docs" / "engine-reference" / "mcp" / "VERSIONS.md"
MCP_JSON = REPO_ROOT / ".mcp.json"
PROJECT_VERSION = REPO_ROOT / "src" / "ProjectSettings" / "ProjectVersion.txt"
PACKAGES_MANIFEST = REPO_ROOT / "src" / "Packages" / "manifest.json"


def load_architecture_tooling() -> dict | None:
    if not ARCHITECTURE.exists():
        return None
    try:
        data = yaml.safe_load(ARCHITECTURE.read_text(encoding="utf-8")) or {}
    except Exception as e:
        raise RuntimeError(f"failed to parse {ARCHITECTURE}: {e}") from e
    return data.get("tooling")


UNITY_VERSION_RE = re.compile(r"`Unity LTS`\s*\|\s*`([^`]+)`")
UNITY_PKG_RE = re.compile(r"\|\s*`(com\.[a-z0-9._-]+|jp\.[a-z0-9._-]+)`\s*\|\s*`([^`]+)`")
BLENDER_VERSION_RE = re.compile(r"\*\*Blender\*\*\s*\|\s*`([^`]+)`")
MCP_PIN_ROW_RE = re.compile(
    r"\|\s*`([a-z0-9_-]+)`\s*\|[^|]+\|\s*`([^`]+)`\s*\|"
)


def parse_unity_version_md() -> dict:
    if not UNITY_VERSION_MD.exists():
        return {}
    text = UNITY_VERSION_MD.read_text(encoding="utf-8")
    out: dict = {}
    m = UNITY_VERSION_RE.search(text)
    if m:
        out["unity_version"] = m.group(1).split(" ")[0]
    packages: dict[str, str] = {}
    for m in UNITY_PKG_RE.finditer(text):
        packages[m.group(1)] = m.group(2)
    out["packages"] = packages
    return out


def parse_blender_version_md() -> dict:
    if not BLENDER_VERSION_MD.exists():
        return {}
    text = BLENDER_VERSION_MD.read_text(encoding="utf-8")
    m = BLENDER_VERSION_RE.search(text)
    return {"blender_version": m.group(1)} if m else {}


def parse_mcp_versions_md() -> dict[str, str]:
    if not MCP_VERSIONS_MD.exists():
        return {}
    text = MCP_VERSIONS_MD.read_text(encoding="utf-8")
    pins: dict[str, str] = {}
    in_targets = False
    for line in text.splitlines():
        if line.startswith("## Targets"):
            in_targets = True
            continue
        if in_targets and line.startswith("## "):
            break
        m = MCP_PIN_ROW_RE.match(line)
        if m:
            server = m.group(1).replace("-", "_")
            pin = m.group(2)
            if pin.startswith("<"):
                pin = ""  # placeholder, treat as "not yet pinned"
            pins[server] = pin
    return pins


def parse_mcp_json() -> dict[str, str]:
    if not MCP_JSON.exists():
        return {}
    try:
        data = json.loads(MCP_JSON.read_text(encoding="utf-8"))
    except Exception as e:
        raise RuntimeError(f"failed to parse {MCP_JSON}: {e}") from e
    servers = data.get("mcpServers", {})
    out: dict[str, str] = {}
    for name, spec in servers.items():
        args = spec.get("args") or []
        for arg in args:
            if "@" in arg and arg.count("@") >= 2 and not arg.startswith("-"):
                out[name.replace("-", "_")] = arg.split("@")[-1]
                break
            if "@" in arg and arg.startswith("@") and arg.count("@") >= 2:
                out[name.replace("-", "_")] = arg.split("@")[-1]
                break
        else:
            out[name.replace("-", "_")] = ""
    return out


def parse_project_version() -> str | None:
    if not PROJECT_VERSION.exists():
        return None
    for line in PROJECT_VERSION.read_text(encoding="utf-8").splitlines():
        if line.startswith("m_EditorVersion:"):
            return line.split(":", 1)[1].strip()
    return None


def parse_packages_manifest() -> dict[str, str]:
    if not PACKAGES_MANIFEST.exists():
        return {}
    try:
        data = json.loads(PACKAGES_MANIFEST.read_text(encoding="utf-8"))
    except Exception as e:
        raise RuntimeError(f"failed to parse {PACKAGES_MANIFEST}: {e}") from e
    return dict(data.get("dependencies") or {})


def check(tooling: dict) -> tuple[list[dict], list[dict]]:
    """Return (drift, skipped). drift items are violations; skipped are info."""
    drift: list[dict] = []
    skipped: list[dict] = []

    unity = tooling.get("unity") or {}
    declared_unity = unity.get("version")
    declared_pkgs = unity.get("packages") or {}

    unity_md = parse_unity_version_md()
    if declared_unity and unity_md.get("unity_version"):
        if declared_unity != unity_md["unity_version"]:
            drift.append({
                "kind": "mirror_drift",
                "source": "unity/VERSION.md",
                "field": "unity_version",
                "declared": declared_unity,
                "found": unity_md["unity_version"],
            })

    bl_md = parse_blender_version_md()
    blender = tooling.get("blender") or {}
    declared_blender = blender.get("version")
    if declared_blender and bl_md.get("blender_version"):
        if declared_blender != bl_md["blender_version"]:
            drift.append({
                "kind": "mirror_drift",
                "source": "blender/VERSION.md",
                "field": "blender_version",
                "declared": declared_blender,
                "found": bl_md["blender_version"],
            })

    mcp_md = parse_mcp_versions_md()
    mcp_json = parse_mcp_json()
    declared_mcp = tooling.get("mcp_servers") or {}
    for server, entry in declared_mcp.items():
        pin = (entry or {}).get("pin")
        if not pin:
            skipped.append({
                "kind": "mcp_pin_pending",
                "source": "architecture.yaml",
                "field": f"mcp_servers.{server}.pin",
                "detail": "pin not yet set (placeholder); will be filled at first install.",
            })
            continue
        md_pin = mcp_md.get(server)
        if md_pin and md_pin != pin:
            drift.append({
                "kind": "mirror_drift",
                "source": "mcp/VERSIONS.md",
                "field": f"mcp_servers.{server}",
                "declared": pin,
                "found": md_pin,
            })
        json_pin = mcp_json.get(server)
        if json_pin and json_pin != pin:
            drift.append({
                "kind": "mirror_drift",
                "source": ".mcp.json",
                "field": f"mcp_servers.{server}",
                "declared": pin,
                "found": json_pin,
            })

    pv = parse_project_version()
    if pv is None:
        skipped.append({
            "kind": "not_bootstrapped",
            "source": "src/ProjectSettings/ProjectVersion.txt",
            "detail": "Unity project not yet bootstrapped — skipping editor pin check.",
        })
    elif declared_unity and pv != declared_unity:
        drift.append({
            "kind": "editor_drift",
            "source": "ProjectVersion.txt",
            "field": "m_EditorVersion",
            "declared": declared_unity,
            "found": pv,
        })

    pm = parse_packages_manifest()
    if not pm:
        skipped.append({
            "kind": "not_bootstrapped",
            "source": "src/Packages/manifest.json",
            "detail": "Unity manifest not yet present — skipping package pin checks.",
        })
    else:
        pkg_name_map = {
            "render_pipelines_universal": "com.unity.render-pipelines.universal",
            "inputsystem": "com.unity.inputsystem",
            "cinemachine": "com.unity.cinemachine",
            "test_framework": "com.unity.test-framework",
            "ide_rider": "com.unity.ide.rider",
            "addressables": "com.unity.addressables",
            "vcontainer": "jp.hadashikick.vcontainer",
            "unitask": "com.cysharp.unitask",
        }
        for key, declared_version in declared_pkgs.items():
            pkg_id = pkg_name_map.get(key)
            if not pkg_id or pkg_id not in pm:
                continue
            actual = pm[pkg_id]
            if actual and declared_version and declared_version not in actual:
                drift.append({
                    "kind": "package_drift",
                    "source": "manifest.json",
                    "field": pkg_id,
                    "declared": declared_version,
                    "found": actual,
                })

    return drift, skipped


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    try:
        tooling = load_architecture_tooling()
    except RuntimeError as e:
        sys.stderr.write(f"check-runtime-versions: {e}\n")
        return 2

    if tooling is None:
        if args.json:
            print(json.dumps({"status": "skipped", "reason": "no architecture.yaml"}))
        elif not args.quiet:
            print("runtime versions: no architecture.yaml (skip)")
        return 0

    try:
        drift, skipped = check(tooling)
    except RuntimeError as e:
        sys.stderr.write(f"check-runtime-versions: {e}\n")
        return 2

    if args.json:
        print(json.dumps({
            "status": "ok" if not drift else "drift",
            "drift": drift,
            "skipped": skipped,
        }, indent=2))
        return 0 if not drift else 1

    if not drift and not skipped:
        if not args.quiet:
            print("runtime versions: all green")
        return 0

    if not drift:
        if not args.quiet:
            print(f"runtime versions: clean ({len(skipped)} skipped — see --json)")
        return 0

    print(f"runtime versions: {len(drift)} drift(s)")
    for d in drift:
        print(
            f"  [{d['kind']}] {d['source']} {d['field']}: "
            f"declared={d.get('declared')!r} found={d.get('found')!r}"
        )
    if not args.quiet and skipped:
        print(f"  ({len(skipped)} skipped — see --json)")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
