---
id: PLAN-005-ship-ai-dialogue
type: plan
status: done
done_date: 2026-05-12
related: [ADR-0006]
---

# Plan 005: Ship AI dialogue mechanic — documentation only

> **This plan documents a design. It does not implement it. Zero code under `src/`.** All work is editing markdown / YAML in `docs/`, `.claude/rules/`, and `.claude/agents/`.
>
> The design lands as paper, available for a future decision. There is no implementation plan scheduled and none is implied.

## Context

The PoC needs a chatbot mechanic: the player accesses **PC terminals** in-world and chats with the **ship's operations AI**. The AI knows player/world state (oxygen, agitation, zone, flags, objective) and can help OR work against the player. The AI is a **separate character** from the presence — the presence remains non-conversational (PILLAR-02 intact). The AI exists to give information ("what to do now") AND to be talked to as a free-text mechanic.

This shifts the genre register: from pure environmental horror to environmental horror **plus** unreliable conversational ally. It does not weaken PILLAR-02 — the AI is not the threat, and the threat does not speak through the AI either. The threat stays silent, environmental, never visually confirmed.

### Why this plan exists

- No "ship AI" character exists in the GDD today; the only voice events are radio echoes and one terminal text. Introducing a chat-driven character is a real GDD change, not a code add-on.
- The repo has zero precedent for network calls, JSON streaming, external service configuration, or secrets — a new ADR has to set the rules before any class signature lands.
- The existing `NarrativeDirector` is shape-incompatible with request-response chat (it is flag→cue, fire-once). A parallel system is needed, sized to coexist without overlap.
- Locking the design now prevents any future implementation work from re-litigating lore, alignment model, and transport choices.

### Intended outcome

After this plan is executed:

- The GDD names the ship AI as a character, explains the terminals mechanic, and frames the three-axis "AI works against you" model.
- The registry has `SYS-TERMINAL`, `SYS-DIALOGUE`, related configs and events.
- The SDD declares the system contracts (Responsibility / Inputs / Outputs / Invariants / Acceptance) for both systems.
- The TDD declares classes, the `IDialogueTransport` interface, the `DialogueLogic` plain-C# class (per ADR-0002), DTOs.
- A new ADR-0006 fixes the network/transport/endpoint-config policy for the project.
- Reviewer rules block the kinds of mistakes this domain invites (talking to disk for keys, bypassing the transport interface, leaking AI internals into save state).
- The design is self-contained: a programmer in 6 months can read it and start, or shelve it forever, without anything else breaking.

## Design — locked decisions

These are not options; they are the spine of the plan.

### Lore framing — the AI character

**Name:** `MOTHER` (Last Breath's ops AI).

**Three-axis "works against you" model.** The AI's antagonism is not a single hidden hostility score. It's the visible interaction of three internal states the player cannot inspect:

1. **Mandate divergence** (`mandate` ∈ [0..1]): how much the player's current action conflicts with the AI's primary directive (preserve the ship). Rises when the player breaks protocol (forces doors, enters quarantined zones, ignores warnings). Drives **selective omission and refusal**: the AI will give you the rule, then refuse to help you bend it.
2. **System integrity** (`integrity` ∈ [0..1], starts at 1.0, monotonically drifts down over the run): how broken the AI itself is. Drives **inconsistency and unintentional lies**: replies contradict prior turns, reference systems offline, claim sensors that aren't reporting. The AI does not know it is lying.
3. **Budget pressure** (`budget` ∈ [0..1]): how much spare resource (oxygen reserves, power, access tokens) the AI has to allocate. Drives **denial framed as policy**: "Energy module access is restricted under current power budget. Request denied."

The player **cannot tell which axis is hitting them in a given reply**. That ambiguity is the mechanic. The AI is not "good or evil" — it is a cold administrator, breaking down, on a budget.

This framing keeps PILLAR-02 intact: nothing about the AI confirms or denies the presence. The AI may refer to "anomalies" or "sensor faults" but never to a *threat*.

### Mechanic shape — terminals

**Terminal = diegetic chat surface.** Wall-mounted PC. Player must walk to it, hold the interact key, and a chat UI opens. While the UI is open the player stands still (oxygen continues to drain — PILLAR-04 risk gate). Closing the UI returns to gameplay.

**Two channels at every terminal:**

- **Inbox channel** (async, one-way, AI → player). When the AI generates a message scripted to wait at a specific terminal (driven by `EVT-flag-changed` subscriptions), that message appears in the terminal's inbox. The player can read pending messages without consuming an LLM call. This is how the AI "tells you what to do next" without breaking exploration.
- **Live channel** (sync, two-way, request-response). Player types free-text; the AI replies in one paragraph. Each turn costs one LLM call against the transport. History is bounded (last N turns) and saved.

**Why two channels:** the design requirement was both "know what to do next" (info channel) AND "talk freely to the AI" (chat channel). One channel cannot do both well. The inbox is deterministic, scripted, cheap. The chat is non-deterministic, free-text, costly per turn.

### System decomposition

```
SYS-TERMINAL (MonoBehaviour)
  └── owns TerminalInteractable (IInteractable, peer of PanelInteractable)
  └── owns Chat UI lifecycle (open/close, focus, input lock)
  └── owns the per-terminal inbox view materialized from SYS-DIALOGUE
  └── publishes: EVT-terminal-opened, EVT-terminal-closed
  └── subscribes: EVT-dialogue-response-ready, EVT-ai-message-delivered

SYS-DIALOGUE (MonoBehaviour)
  └── owns conversation state, AI internal state (mandate/integrity/budget)
  └── owns the scripted-message routing (which inbox messages go where, when)
  └── delegates to DialogueLogic (plain C#, ADR-0002 split)
  └── delegates to IDialogueTransport (interface)
  └── publishes: EVT-dialogue-response-ready, EVT-ai-message-delivered
  └── subscribes: EVT-flag-changed, EVT-oxygen-changed, EVT-agitation-changed,
                  EVT-zone-changed, EVT-presence-event-fired, EVT-terminal-opened

DialogueLogic (plain C# — NOT a registry system)
  └── builds the LLM prompt from DialogueContext (explicit allowlist)
  └── parses structured LLM response { speech, mandateDelta, tags }
  └── updates internal state (mandate/integrity/budget) per turn
  └── pure, deterministic given the same context + transport response — EditMode-testable

IDialogueTransport (interface, NOT a registry system)
  └── OllamaHttpTransport: POSTs to a configurable HTTP endpoint (default impl)
  └── MockTransport: returns canned structured responses (EditMode + offline dev)
  └── one method: async Awaitable<TransportResponse> SendAsync(string prompt, CancellationToken ct)
```

The LLM transport is **not** a registry system. It is an interface + implementations, owned and held by `SYS-DIALOGUE`. This avoids inflating `architecture.yaml` with an entry that has no events, no save state, and no subscribers.

### Structured LLM response

The AI is asked to return JSON, not free prose:

```json
{
  "speech": "Energy module access is restricted under current power budget. Request denied.",
  "mandateDelta": 0.05,
  "tags": ["refusal", "policy"]
}
```

Tags are bounded enum-like strings (`refusal`, `policy`, `evasion`, `compliance`, `nonsequitur`, `warning`, `false-claim`). `DialogueLogic` validates the shape; malformed responses fall back to a configured offline reply and tick integrity down. Tags drive system reactions (a `refusal` may rise agitation; a `warning` may publish a `EVT-narrative-cue-fired` for the audio layer). The speech field is the only part the player sees.

### What the AI knows and what it does not

**Sent to the AI in the prompt context (per turn):**

- Identity block (system prompt with persona, format rules).
- Current zone (string, e.g., `"corridor_c7"`).
- Oxygen bucket (`"high" | "medium" | "low" | "critical"`) — not the exact %.
- Agitation bucket (`"calm" | "tense" | "panic"`).
- Current objective text (string, the same line the HUD shows).
- AI internal state (`mandate`, `integrity`, `budget` — exposed to the model so it can role-play them).
- Last N exchanges (N = config, default 5).

**Withheld from the AI:**

- Exact position, exact oxygen %, exact agitation value.
- The full flag list, the presence cooldowns, the registry of fired narrative cues.
- The contents of the inbox (so the AI cannot reference messages it scripted earlier — those exist only in `SYS-DIALOGUE` routing).
- Prior session history beyond the current run.

The withholding is deliberate: the AI feels less omniscient, the player retains private state, and the structured-response shape prevents the model from inventing inspections it does not actually have.

### Transport policy

**Default transport:** `OllamaHttpTransport` — HTTP POST to a configurable Ollama-compatible endpoint. Endpoint resolution order:

1. Environment variable `LASTBREATH_LLM_ENDPOINT` (developer override).
2. `CFG-LLM-TRANSPORT` ScriptableObject `defaultEndpoint` field (committed default).
3. Hard-coded fallback to `http://localhost:11434` if both above are empty.

**No secrets management this round.** Ollama endpoints are URLs, not API keys.

**No streaming.** Single blocking call per turn with a 4-second p95 latency budget. Timeout falls back to a configured offline reply and ticks `integrity` down — *failure looks like AI degradation*, which is on-genre.

Full rationale in ADR-0006.

### Save shape

`DialogueDto` joins `SaveData`:

```csharp
[Serializable]
public class DialogueDto
{
    public List<DialogueExchange> exchanges;
    public List<InboxEntry> inbox;            // per-terminal pending messages
    public float mandate;
    public float integrity;
    public float budget;
    public int turnCount;
}
[Serializable] public class DialogueExchange { public string playerText; public string aiSpeech; public string[] aiTags; public int turnIndex; }
[Serializable] public class InboxEntry { public string terminalId; public string messageId; public string body; public bool isRead; }
```

Restored silently per `SAVE-NO-EVENTS-DURING-LOADING`. The transport is **never** invoked during restore — the saved exchanges are the truth.

### Reviewer rules added

- `GAMEPLAY-CODE-DIALOGUE-NO-DIRECT-LLM` — only `SYS-DIALOGUE` calls `IDialogueTransport.SendAsync`.
- `GAMEPLAY-CODE-DIALOGUE-NO-SECRETS-IN-SAVE` — `DialogueDto` holds conversational state only.
- `GAMEPLAY-CODE-DIALOGUE-PROMPT-MUST-WITHHOLD` — the prompt is built from an explicit allowlist; no reflection.

## Scope (8 items: A–H)

- **A**. GDD — add `## Ship AI character` section AND `### Terminals` mechanic under `## Main Mechanics`. Frame the three-axis antagonism model.
- **B**. New ADR-0006 — `transport-and-llm-policy.md`. Locks: HTTP-only, async Awaitable, endpoint via env + SO, no secrets in save, no Newtonsoft, `IDialogueTransport` as the single seam.
- **C**. `architecture.yaml` — register `SYS-TERMINAL`, `SYS-DIALOGUE`, configs (`CFG-DIALOGUE-AI`, `CFG-LLM-TRANSPORT`, `CFG-DIALOGUE-CUE`), events (`EVT-terminal-opened`, `EVT-terminal-closed`, `EVT-dialogue-response-ready`, `EVT-ai-message-delivered`).
- **D**. SDD — add `### TerminalSystem`, `### DialogueSystem` sections (Responsibility / Inputs / Outputs / Invariants / Acceptance). Update `§Communication matrix`. Note: terminals are the only `IInteractable` that pauses player input and holds focus for >1s.
- **E**. TDD — add `## Terminals` and `## Dialogue` sections. Declare `TerminalInteractable`, `TerminalSystem`, `DialogueSystem`, `DialogueLogic`, `IDialogueTransport`, `OllamaHttpTransport`, `MockTransport`, `DialogueContext`, `DialogueCueDefinition`, `DialogueDto`, `DialogueExchange`, `InboxEntry`, structured response shape. Per ADR-0002: `DialogueLogic` is plain C#, `DialogueSystem` is its MonoBehaviour adapter. Update `SaveData` to include `dialogue: DialogueDto`.
- **F**. Reviewer rules — add the three `GAMEPLAY-CODE-DIALOGUE-*` rules to `.claude/rules/gameplay-code.md` + index in `.claude/agents/code-reviewer.md`.
- **G**. Glossary — define: terminal, ship AI, mandate, integrity, budget, inbox, live channel, structured response, transport, mock transport. Anti-glossary: forbid "computer" (say `terminal`), "chatbot" in design prose (say `ship AI`), "API key" (say `endpoint config`), "AI trust meter" / "hostility score" / "alignment bar".
- **H**. Plans index — register PLAN-005, link ADR-0006.

## Out of scope

- All C# code under `src/`. This plan is documentation-only.
- The implementation of `OllamaHttpTransport` (the *spec* lands in TDD; the code is not planned).
- Chat UI styling (TextMeshPro layout, sound on type, color palette).
- TTS / voice acting of AI replies.
- Multiple distinct AI personalities per terminal.
- Anthropic / OpenAI transports.
- Cross-run persistence (memory of prior playthroughs).
- AI being able to directly invoke world effects (lock doors, kill lights). The AI in PoC can *talk* about doing so; actual side-effects via flags happen in a follow-up.
- Streaming responses.
- Cloud-Ollama production deployment.

## Critical files

Modified by this plan:

- `docs/gdd/last-breath-poc-gdd.md` — step A.
- `docs/decisions/0006-transport-and-llm-policy.md` — **new file**, step B.
- `docs/registry/architecture.yaml` — step C.
- `docs/sdd/last-breath-poc-sdd.md` — step D.
- `docs/tdd/last-breath-poc-tdd.md` — step E.
- `.claude/rules/gameplay-code.md` — step F.
- `.claude/agents/code-reviewer.md` — step F.
- `docs/registry/glossary.md` — step G.
- `docs/plans/README.md` — step H.
- `docs/plans/005-ship-ai-dialogue.md` — **new file**, this plan filed in step H.

Already-shipped references (consulted but not modified):

- `docs/decisions/0002-monobehaviour-vs-plain-csharp-split.md` — drives the `DialogueLogic` split.
- `docs/decisions/0004-flag-and-narrative-event-model.md` — forbids SO event channels; chat events are C# events on `SYS-DIALOGUE`.
- `docs/decisions/0005-save-system-architecture.md` — drives `DialogueDto` shape, silent restore.
- `docs/plans/004-progression-and-save.md` — the template this plan mirrored.
- `docs/process/unity-patterns.md` §6 — endorses `async Awaitable` + `destroyCancellationToken`.

## Implementation order

1. **A** (GDD framing) — narrative anchor; everything else cites it.
2. **B** (ADR-0006) — locks the transport policy before SDD/TDD name a transport.
3. **C** (registry) — IDs exist before SDD/TDD reference them.
4. **D** (SDD).
5. **E** (TDD).
6. **F** (reviewer rules + agent index).
7. **G** (glossary).
8. **H** (plans index, file PLAN-005).
9. Verify + mark `done`.

Each step = one commit. Subagents used:

- A → `game-designer`.
- B → manual (ADR author is the decision-maker).
- C → manual (registry is sensitive).
- D → `systems-designer`.
- E → `gameplay-programmer` (doc-only mode).
- F → manual.
- G → manual.
- H → manual.

## Acceptance

- [x] GDD `## Ship AI character` section exists with the three-axis model named and persona `MOTHER` recorded.
- [x] GDD `### Terminals` mechanic under `## Main Mechanics` describes inbox + live channel; cross-references `MECH-INTERACTION` and `PILLAR-04`.
- [x] ADR-0006 exists at `docs/decisions/0006-transport-and-llm-policy.md`, `status: accepted`, with `Considered Alternatives` covering: Anthropic API direct, embedded local model, Newtonsoft dependency, streaming responses, static singleton.
- [x] `architecture.yaml` contains `SYS-TERMINAL`, `SYS-DIALOGUE`, `CFG-DIALOGUE-AI`, `CFG-LLM-TRANSPORT`, `CFG-DIALOGUE-CUE`, `EVT-terminal-opened`, `EVT-terminal-closed`, `EVT-dialogue-response-ready`, `EVT-ai-message-delivered`.
- [x] SDD has `### TerminalSystem` and `### DialogueSystem` with the full five-block shape; `§Communication matrix` has four new rows.
- [x] TDD declares `IDialogueTransport`, `OllamaHttpTransport`, `MockTransport`, `DialogueLogic` (plain C# per ADR-0002), `DialogueSystem`, `TerminalSystem`, `DialogueContext`, `DialogueCueDefinition`, `DialogueDto`, `DialogueExchange`, `InboxEntry`, structured response object. `SaveData.dialogue` field added.
- [x] `.claude/rules/gameplay-code.md` contains `GAMEPLAY-CODE-DIALOGUE-NO-DIRECT-LLM`, `GAMEPLAY-CODE-DIALOGUE-NO-SECRETS-IN-SAVE`, `GAMEPLAY-CODE-DIALOGUE-PROMPT-MUST-WITHHOLD`, each cross-referencing ADR-0006.
- [x] `.claude/agents/code-reviewer.md` rule index lists the three new rule IDs.
- [x] Glossary defines all ten new terms plus the long-form axis terms and anti-glossary entries.
- [x] `scripts/audit-md.py` passes; 0 orphans, 0 broken refs.
- [x] No code under `src/Assets/_Project/**` touched.
- [x] `docs/plans/README.md` index lists PLAN-005 with `status: done`.

## What comes after this plan

**Nothing scheduled.** Implementation is *not* planned. This plan ends when the documentation lands. The design exists on paper as a vetted proposal; whether it ever gets built is a separate future decision that would require its own implementation plan opened explicitly. The documentation produced here is self-contained: a programmer in 6 months could read it and start, or shelve it forever, without anything else breaking.
