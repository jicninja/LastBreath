---
id: PLAN-016-spike-runtime-probe
type: plan
status: proposed
date: 2026-05-12
related: [ADR-0011, PLAN-013]
owners: [unity-specialist, gameplay-programmer]
---

# PLAN-016-spike — Unity runtime-probe feasibility spike (B)

## Context

ADR-0011 §B adopts `HARNESS-LOOP-RUNTIME-PROBE-BEFORE-COMPLETION` as binding methodology. The artifact shape depends on what the existing `unity-mcp` server can already do versus what would need a new Unity-side companion. A spike is needed before scoping the full implementation plan.

Anthropic's article describes the analogous pattern with Playwright MCP: the evaluator drove the running web application, captured DOM snapshots and runtime events, fed the trace back into the evaluator's prompt. The Unity equivalent must answer: can `unity-mcp` enter Play Mode, capture Console output, capture frame stats, and capture end-of-smoke state on its own, or do we need an Editor-side companion (an `EditorWindow`, a `MenuItem`, a JSON-on-disk handoff)?

## Goal

In 0.5–1 day, produce a written assessment at `docs/specs/016-runtime-probe-spike.md` with:

- An inventory of `unity-mcp` verbs relevant to runtime introspection (Play Mode lifecycle, Console reads, Editor selection state, Scene state).
- A reproducible demo: with a smoke scene (or with `src/Assets/Scenes/Main.unity` from `plan 008` once it lands), enter Play Mode via `unity-mcp`, capture at least: console error count, frame count, end-state of one tracked GameObject.
- A go/no-go on the two implementation shapes:
  - **Shape S1 — Pure MCP**: `/play-and-observe` is a thin skill on top of existing `unity-mcp` verbs. Works if Console reads and Play Mode lifecycle are both first-class.
  - **Shape S2 — Editor companion**: a new `[MenuItem("Tools/Last Breath/Runtime Probe/Run Smoke")]` writes a JSON report; `/play-and-observe` invokes the MenuItem and reads the JSON. Works if Shape S1 is infeasible.
- A scoped follow-up plan (PLAN-017 or whichever is next) with the implementation that the spike outcome justifies.

## Out of scope

- Building the production probe. The spike produces the spec; the follow-up plan builds the probe.
- Tuning what the probe captures (frame budget thresholds, error severity filters). That is part of the follow-up plan.
- Wiring the probe into any session flow. That is part of the follow-up plan.

## Runtime verification

The spike's runtime verification is the demo itself — Play Mode entered via MCP, Console captured, end-state captured. The result lives in `docs/specs/016-runtime-probe-spike.md` with at least one screenshot and one captured JSON fragment.

## Acceptance

- [ ] `docs/specs/016-runtime-probe-spike.md` exists with the four required sections (Inventory, Demo, Go/No-go, Follow-up plan scope).
- [ ] At least one screenshot or captured artifact proves the demo ran.
- [ ] The follow-up plan number is reserved in `docs/plans/README.md` (`PLAN-017` or next available).
- [ ] `docs/process/harness-engineering.md` §3.B is updated to name the chosen shape.

## Dependencies

PLAN-013 (this spike's rationale). PLAN-008 (Unity bootstrap) is **soft** dependency — the spike can run against a one-scene Unity project the spike sets up itself if `plan 008` has not landed yet. Hard prerequisite is `unity-mcp` installed and pinned in `architecture.yaml::tooling.mcp_servers`.
