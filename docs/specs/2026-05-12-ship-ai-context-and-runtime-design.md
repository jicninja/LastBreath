---
id: SPEC-2026-05-12-ship-ai-context-and-runtime
type: spec
layer: spec
status: proposed
related: [PLAN-005, ADR-0006, ADR-0002, ADR-0004, ADR-0005, SYS-DIALOGUE, SYS-TERMINAL, CFG-DIALOGUE-AI, CFG-LLM-TRANSPORT]
---

# Ship AI — Context, Runtime, and Availability Design Spec

> **Documentation only.** This spec extends Plan 005 / ADR-0006 with concrete decisions on the per-turn context shape, the LLM model pick, the prompt template, the chat UI tech stack, and a new gameplay-driven availability gate. Implementation, if and when scheduled, requires its own plan.

## Context

Plan 005 shipped the system architecture for `SYS-DIALOGUE` and `SYS-TERMINAL`, and ADR-0006 locked the transport policy (`IDialogueTransport`, HTTP-only, no streaming, env-then-SO endpoint resolution, no secrets in save). The TDD declared `DialogueContext` with eight whitelisted fields, the structured response shape, and the system class signatures.

Three things were intentionally left open and now need to be settled before any implementation plan can land:

1. **The model.** `LlmTransportConfig.modelName` was a placeholder (`"llama3"`). A concrete pick anchors the latency budget, the prompt template choices, and the persona authoring effort.
2. **The per-turn context.** `DialogueContext` did not carry any record of *what the player just did* — only current state (zone, oxygen bucket, agitation bucket, objective, axes, recent dialogue exchanges). MOTHER could not react to the run's events beyond the chat itself.
3. **The chat UI substrate.** The TDD said `TerminalSystem` "owns the chat UI lifecycle" without specifying the framework, layout, or response feedback.

A fourth dimension surfaced during this brainstorm:

4. **Availability gating.** MOTHER should be unreachable or corrupted in some zones / under some flag combinations, by gameplay design — not by transport failure. This needs a typed branch in `DialogueSystem.SubmitTurnAsync` *before* the transport is touched.

The intended outcome of this spec: lock 1–4 with enough specificity that a single follow-up implementation plan can execute end-to-end.

---

## Decisions

### 1. `DialogueContext` extension — categorical action log + last focus

`DialogueContext` (TDD `### DialogueContext`) gains **two whitelisted fields**. All existing fields stay unchanged.

```csharp
public enum RecentEventTag {
    ProtocolBreach,
    ZoneTransition,
    PresenceEvent,
    OxygenBucketDrop,
    AgitationSpike,
    ObjectiveAdvanced,
    ObjectiveBlocked,
    InboxIgnored,
    Idle
}

public enum RecentTagAge { JustNow, ThisTurn, EarlierThisRun }

public readonly struct RecentEvent {
    public readonly RecentEventTag Tag;
    public readonly RecentTagAge Age;
    public RecentEvent(RecentEventTag tag, RecentTagAge age) { Tag = tag; Age = age; }
}

public readonly struct DialogueContext {
    // ...existing 8 fields unchanged...
    public readonly IReadOnlyList<RecentEvent> recentEvents;     // bounded 0..10
    public readonly string lastSignificantInteraction;            // nullable; designer-curated label
}
```

**Source of data:**

- `recentEvents`: `DialogueSystem` keeps an in-memory `Queue<RecentEvent>` fed by its existing subscriptions (`EVT-zone-changed`, `EVT-oxygen-changed`, `EVT-agitation-changed`, `EVT-presence-event-fired`, `EVT-flag-changed`) plus one new subscription: `EVT-interaction-completed` (used to derive `ProtocolBreach` directly when the source interactable implements `IFocusLabel` and is tagged as protocol-breaching, instead of inferring from the resulting flag transition). **Eviction policy:** FIFO when the queue exceeds cap. Consecutive duplicates of the same `Tag` collapse into a single entry holding the most recent `Age`. Cap = 10. No per-bucket reservation: `EarlierThisRun` entries can fully fill the queue; this is intentional — it lets the AI sense "nothing relevant has happened in a while."
- `lastSignificantInteraction`: a new dedicated single-method interface `IFocusLabel { string FocusLabel { get; } }` is implemented **only by interactables that want to be addressable by the ship AI** (e.g., `OxygenStationInteractable`, the airlock interactable, `PanelInteractable` for `panel C-7`). `IInteractable` itself stays unchanged — this is the cleaner separation of concerns. `DialogueSystem` listens to `EVT-interaction-completed`, casts the source to `IFocusLabel`, and if the cast succeeds caches the returned label. The label is a `[SerializeField] string _focusLabel` on the implementing MonoBehaviour, designer-set in the inspector, identical in shape to the existing `_terminalId` precedent on `TerminalInteractable`. Registered as `CLASS-IFocusLabel` in `architecture.yaml`. **# NEW**

**Justification of withholding policy** (extends ADR-0006 §Decision item 5):

- `RecentEventTag` is a closed enum — the reviewer can grep the type to see the entire universe of possible values. No reflection.
- `lastSignificantInteraction` is a free string but its values are sourced exclusively through the explicit `IFocusLabel.FocusLabel` getter, not via reflection over the interactable's internal state. The values are designer-authored on the implementing MonoBehaviour, identical in shape to the existing `TerminalInteractable._terminalId` precedent that the project already accepts.
- `RecentTagAge` is a 3-value enum, not a wall-clock float. Reviewer rule `GAMEPLAY-CODE-DIALOGUE-PROMPT-MUST-WITHHOLD` continues to hold; only its allowlist needs to be extended.

**TDD `Withheld by design` block — required amendment.** The existing block in TDD `### DialogueContext` (lines 1623–1628 at time of writing) reads, in part: "presence cooldowns or fired-event history" must NOT be added. `RecentEventTag.PresenceEvent` is categorical, age-bucketed presence-event awareness — not a cooldown timer or per-firing timestamp log. The TDD block must be amended to read: *"exact presence cooldowns or per-firing timestamps are withheld; aggregated `RecentEventTag.PresenceEvent` entries with `RecentTagAge` buckets are part of the allowlist."* This amendment is part of the doc changes required by this spec; without it, the new field contradicts the existing TDD invariant. Tracked in the "Document changes" table below.

### 2. Save shape — `DialogueDto` persists both new fields

```csharp
[Serializable]
public class DialogueDto {
    public List<DialogueExchange> exchanges;
    public List<InboxEntry> inbox;
    public float mandate;
    public float integrity;
    public float budget;
    public int turnCount;
    public List<RecentEventDto> recentEvents;          // NEW. capped at 10.
    public string lastSignificantInteraction;          // NEW. nullable.
}

[Serializable]
public class RecentEventDto {
    public RecentEventTag tag;
    public RecentTagAge age;
}
```

**Restore policy:** in `DialogueSystem.RestoreState(dto)`, all `recentEvents.age` are demoted to `EarlierThisRun` regardless of their stored value. Reasoning: after restore, no recent event is honestly "JustNow" anymore — the file came off disk. The tags survive (so MOTHER's awareness of run history is preserved); only the age is normalized. Implementation is one line.

This satisfies SDD `§SaveSystem.Acceptance`: "Capture, write, read, restore yields a state observationally equal to the moment of capture" — by preserving the events themselves and only adjusting an age field whose meaning is *position relative to now*, not absolute time.

Restore continues to follow `GAMEPLAY-CODE-SAVE-NO-EVENTS-DURING-LOADING`: fields are assigned directly, no events fire.

### 3. Model — Hermes 3 8B primary, Qwen 2.5 14B fallback

```csharp
// CFG-LLM-TRANSPORT defaults
public string modelName = "hermes3:8b-llama3.1-q4_K_M";
```

Rationale (assumes 16–24 GB VRAM target hardware, e.g. RTX 4080/4090):

- **JSON discipline** is decisive. The structured response (`{ speech, mandateDelta, tags }`) is parsed with `JsonUtility`; every malformed reply costs an `integrity` tick. Hermes 3 is fine-tuned by Nous Research specifically for function-calling / structured output and is among the most JSON-disciplined models in its size class.
- **Persona steerability.** Hermes 3 has notably weaker safety-refusal triggers than vanilla Llama 3.1 / Gemma 3, which matters because MOTHER's character (cold administrator, refuses help, withholds intentionally, contradicts itself) trips the "let me help you" reflex of strongly-aligned models.
- **Latency.** ~0.7–1.2s per turn for ~200 tokens of output on RTX 4080/4090. Comfortable under the 4s p95 budget from ADR-0006.
- **Footprint.** ~5 GB Q4 weights. Fits trivially with room to keep the model resident.

**Documented fallback:** `qwen2.5:14b-instruct-q4_K_M`. Used when persona drift or formatting issues require more raw reasoning. Fits in ~9 GB Q4. Latency 1.5–2.0s per turn, still under budget. Switching is one config flip.

**Rejected:** Gemma 3 (safety alignment fights MOTHER's character; weaker `format:json` discipline; multimodal weight we don't use). Vanilla Llama 3.1 8B Instruct (weaker JSON discipline than Hermes 3, weaker steerability for dark personas). Llama 3.3 70B (~40 GB Q4, doesn't fit, latency 8–15s busts budget). Mistral Small 22B (more uncensored and intelligent but ~13 GB Q4 + 2.5–3.5s latency pushes the p95 too close to 4s on 4080).

### 4. Prompt template — Ollama `messages` API, `format:"json"` mandatory

POST body shape (illustrative):

```json
POST /api/chat
{
  "model": "hermes3:8b-llama3.1-q4_K_M",
  "format": "json",
  "stream": false,
  "options": { "temperature": 0.6, "num_predict": 220 },
  "messages": [
    { "role": "system",    "content": "<system prompt MOTHER>" },
    { "role": "user",      "content": "<state block + history block + player line>" }
  ]
}
```

**System prompt — static per session.** Authored in `DialogueAIConfig.systemPrompt` (`[TextArea(8, 32)]`). Required sections:

1. **Identity** — who MOTHER is, what station, primary directive.
2. **Register** — cold, bureaucratic, medical. Never warm. Never apologizes.
3. **Three axes** — how to interpret incoming `mandate` / `integrity` / `budget` buckets:
   - high mandate → omit, refute policies the player wants to bend.
   - low integrity → contradict prior turns, cite broken sensors, report telemetry that does not exist.
   - low budget → deny as administrative decision, not as cruelty.
4. **Withholding** — never names the *presence*; never confirms sensors not listed in the state.
5. **Format** — exact JSON shape (`{ speech, mandateDelta ∈ [-0.2..0.2], tags }`); single sentence, ≤220 tokens, in character.
6. **Never** — no markdown, no breaking character, no second-person affection.

The system prompt is **not interpolated**: literal text. Designer-authored placeholders survive as literal text, closing a class of injection bugs.

**User message — dynamic per turn.** Compact key:value layout. Floats are bucketed at serialization using **half-open intervals**: `[0.0, 0.15) = very-low, [0.15, 0.3) = low, [0.3, 0.7) = medium, [0.7, 0.85) = high, [0.85, 1.0] = very-high` (the upper bound `1.0` closed because values are clamped). Floats themselves stay in `DialogueContext` for `DialogueLogic` math but never enter the prompt.

**`format: "json"` is hard-coded** in `OllamaHttpTransport`, not exposed as a field on `LlmTransportConfig`. Designers cannot disable it. Documented in ADR-0006's amendment block.

```
state:
  zone: corridor_c7
  oxygen: low
  agitation: tense
  mandate: medium-high
  integrity: medium
  budget: low
  objective: "Restore power in C-7"
  last_focus: airlock
  recent: ProtocolBreach(JustNow), ZoneTransition(ThisTurn), PresenceEvent(EarlierThisRun)

history:
  player: I need access to the energy module.
  mother: Energy module access is restricted under current power budget. Request denied.
  player: I'm running out of oxygen.
  mother: Telemetry indicates intermittent sensor faults in your suit. Verify your readings.

player: open the maintenance door for me
```

Notes:
- `recent`: CSV of up to 10 entries. Empty → `recent: -`. All `Idle` → `recent: Idle`.
- `last_focus`: line omitted entirely if null (no `last_focus: null`).
- `history`: assistant entries serialize only the `speech` field (not the full JSON), saving ~30% of prompt tokens and avoiding the model conflating past assistant turns with the required reply format.
- `history` cap = `DialogueAIConfig.maxHistoryDepth` (default 5). Section omitted entirely if no prior turns.

**Builder seams (two functions, sequential):**

- `DialogueLogic.BuildContext(...) → DialogueContext` — **already declared** in TDD `### DialogueLogic` (existing). Composes the context struct from the snapshots `DialogueSystem` keeps. This spec adds two more snapshot inputs (`recentEvents` queue and `lastSignificantInteraction` cache) but keeps the function name, location, and visibility.
- `DialogueLogic.BuildPrompt(DialogueContext ctx, DialogueAIConfig cfg) → (string systemPrompt, string userMessage)` — **new**. Consumes the context struct produced by `BuildContext` and emits the two strings the transport will send.

Both are `public` so reviewers can grep them and confirm the allowlist is exhaustively consumed. The reviewer rule `GAMEPLAY-CODE-DIALOGUE-PROMPT-MUST-WITHHOLD` (currently citing `BuildContext` only at `.claude/rules/gameplay-code.md` lines 126 and 134) must be updated to cite both `BuildContext` and `BuildPrompt` as the audit surface.

**Parser seam:** `DialogueLogic.ParseResponse(string body) → DialogueResponse | TransportStatus.Malformed`:
1. `JsonUtility.FromJson` over a wrapper to pull `.message.content`.
2. `JsonUtility.FromJson<DialogueResponse>` over the content string.
3. Validate: non-empty `speech`; clamp `mandateDelta` to `[-0.2, 0.2]`; filter `tags` to the allowed enum subset.
4. Failure path → `TransportStatus.Malformed` → `DialogueLogic` falls back to `DialogueAIConfig.offlineFallbackReplies` and ticks `integrity` down (per ADR-0006 "failure looks like degradation").

### 5. Chat UI tech stack — uGUI + TextMeshPro, custom

Chosen over UI Toolkit and over any third-party Asset Store package. Rationale:

- The project's existing UI surface (`SDD §HudController`) is uGUI / TMP. Mixing UI Toolkit only for the terminal would split the project's UI mental model for one screen.
- TMP gives the diegetic CRT-monospace aesthetic for free (monospace TMP font + rich-text tags handle glitch/garbled effects natively).
- No package dependency: `AGENTS.md` global rule "never bump a package or engine version as a side effect" — adding a chat package needs its own plan, not justified for ~200 lines of glue.
- Yarn Spinner / Pixel Crushers Dialogue System are tree/graph runtimes for branching pre-authored dialogue. The ship-AI live channel is request/response with an LLM — no graph to execute. The inbox already uses `DialogueCueDefinition` SOs for its small "scripted message gated by flags" job.

Components introduced:

| Component | Type | Role |
|---|---|---|
| `TerminalChatPanel.prefab` | Canvas prefab | The terminal screen. World-space or overlay (Unity-specialist call at implementation time; both viable). |
| `TerminalChatView` | MonoBehaviour | Owns the panel; the view layer for `TerminalSystem`. Subscribes to `EVT-dialogue-response-ready`, filtering by `terminal_id`. |
| `ChatHistoryView` | MonoBehaviour | `ScrollRect` + `VerticalLayoutGroup` of `ChatEntry` instances. Auto-scrolls on new entry. |
| `ChatEntry.prefab` (×3 variants) | Prefab variants | One variant per role: `player`, `ship-ai-online`, `ship-ai-garbled`. Single `TMP_Text` inside. `ship-ai-garbled` applies TMP rich-text glitch tags / random char substitution at render. (Variant keys use the canonical glossary term `ship AI` rather than the persona name `MOTHER`, to match the rest of the design prose.) |
| `ChatInputField` | MonoBehaviour | Wraps `TMP_InputField` + Send button + Enter binding. Disabled while a turn is in flight or when MOTHER is `Silent`. |
| `AvailabilityIndicator` | MonoBehaviour | Small status line: `ONLINE` / `DEGRADED` / `NO SIGNAL`, derived from current `AvailabilityState` (see decision 6). |

`TerminalSystem` (already declared in the TDD) gains one new `[SerializeField] private TerminalChatView _chatView` and forwards open/close calls to it. No change to its public API or to `EVT-terminal-opened` / `EVT-terminal-closed`.

ADR-0002 split applied to the new components: all six are MonoBehaviours; UI lifecycle and rendering have no formula content. EditMode tests target `TerminalChatView` open/close gating and the dispatch filter via observable state, no plain-C# helper required.

### 6. Availability gating — three states, designer-driven rules

MOTHER is no longer always-on. Whether she replies, replies garbled, or stays silent is a function of zone + flag state, designer-tunable.

**Three states:**

| State | Meaning | Transport called? | History entry? | UI render |
|---|---|---|---|---|
| `Online` | Normal request/response | yes | yes | speech entry; optional typewriter effect |
| `Garbled` | MOTHER tries but transmission corrupts | **no** — canned `garbledReplies` pool | yes (canned text + `tags=["nonsequitur","false-claim"]`) | speech entry with TMP rich-text glitch tags, char substitution at render |
| `Silent` | ship AI unreachable | **no** | yes (player text + empty AI speech + `tags=["silent"]`) | brief "NO RESPONSE" indicator (rendered by `AvailabilityIndicator`); no speech entry; player line + silence marker remain in history |

Two distinct non-Online states, not one, because the design intent — the ship AI either says nothing at all, or says something incoherent — names two different fictions and must surface differently in the UI.

**Rule shape — new SO `MotherAvailabilityRule`:**

```csharp
public enum AvailabilityState { Online, Garbled, Silent }

[CreateAssetMenu(menuName = "LastBreath/Dialogue/Availability Rule")]
public class MotherAvailabilityRule : ScriptableObject {
    public string ruleId;                       // stable id for diagnostics
    public string zone;                         // empty = any zone
    public FlagDefinition[] requiredFlags;      // all true ⇒ rule may apply
    public FlagDefinition[] forbiddenFlags;     // all false ⇒ rule may apply
    public AvailabilityState state;
    public int priority;                        // higher wins
}
```

Identity-only SO per ADR-0004: no `_runtimeValue` field, no `OnEnable`-resets-to-default pattern, all values read at `Awake` and never mutated at runtime. **Registered as `CFG-AVAILABILITY-RULE` (# NEW)** in `architecture.yaml`. `DialogueAIConfig` gains a `MotherAvailabilityRule[] availabilityRules` and a `string[] garbledReplies` field.

Separate-asset (one rule per file) chosen over nested-array-on-`DialogueAIConfig` to match the existing `DialogueCueDefinition` authoring pattern (one cue per asset).

**Evaluator:** `DialogueLogic.EvaluateAvailability(DialogueContext ctx, IReadOnlyList<MotherAvailabilityRule> rules, IFlagSystem flags) → AvailabilityState` (plain C# per ADR-0002, EditMode-testable):

1. Iterate `rules` in descending `priority`.
2. Skip a rule if `zone != ""` and `zone != ctx.zone`.
3. Skip a rule if any `requiredFlag` is false.
4. Skip a rule if any `forbiddenFlag` is true.
5. First match wins; return its `state`.
6. No match → return `Online` (default).

**Priority tie-break:** if two rules share the same `priority` and both match, the rule appearing earlier in the input list wins. Designers should treat ties as authoring errors and avoid them; an EditMode test asserts the file-order tie-break and a separate test logs a warning when ties are detected at startup. (Stable, deterministic; no random selection.)

**`DialogueSystem.SubmitTurnAsync(string text)` flow:**

1. Build `DialogueContext`.
2. Evaluate availability.
3. Branch:
   - **`Online`** → existing flow: `BuildContext → BuildPrompt → SendAsync → ParseResponse`.
   - **`Garbled`** → pick a reply from `cfg.garbledReplies[]` deterministically: index `= turnCount % cfg.garbledReplies.Length` (round-robin from `turnCount`, no random; cheap to reason about, plays back identically across save/restore for the same turn). Synthesize `DialogueResponse` with `tags=["nonsequitur","false-claim"]`; tick `integrity` down (consistent with ADR-0006 "failure looks like degradation"); fire `EVT-dialogue-response-ready`.
   - **`Silent`** → synthesize empty-speech `DialogueResponse` with `tags=["silent"]`; do **not** touch `integrity` (silence is environmental, not internal failure); fire `EVT-dialogue-response-ready` so the UI can render the "NO RESPONSE" indicator and append the silent entry to history.
4. Append the turn to `recentExchanges` and persist via the next save. Silent and Garbled turns are real history; the player tried, the ship AI did not help — that is the gameplay.

**Tag enum extension:** `"silent"` joins the existing tag set (`refusal`, `policy`, `evasion`, `compliance`, `nonsequitur`, `warning`, `false-claim`).

**Reviewer rule effect:** strengthens, not weakens, `GAMEPLAY-CODE-DIALOGUE-NO-DIRECT-LLM`. Now formally: `IDialogueTransport.SendAsync` is called only inside `SYS-DIALOGUE` *and only when `DialogueLogic.EvaluateAvailability` returns `Online`*.

---

## Document, registry, and reviewer-rule changes required (when the implementation plan executes)

| File | Change |
|---|---|
| `docs/tdd/last-breath-poc-tdd.md` | (a) Extend `### DialogueContext` with two new fields and amend the `Withheld by design` block to allow categorical `RecentEventTag.PresenceEvent` entries (see Section 1). (b) Add `### IFocusLabel` (# NEW interface). (c) Add `### MotherAvailabilityRule`, `### TerminalChatView`, `### ChatHistoryView`, `### ChatInputField`, `### AvailabilityIndicator`, plus a note about `ChatEntry.prefab` variants and `TerminalChatPanel.prefab`. (d) Extend `### DialogueAIConfig` with `availabilityRules` + `garbledReplies`. (e) Extend `### DialogueSystem` with `EvaluateAvailability` and the gated `SubmitTurnAsync` branches. (f) Extend `### DialogueDto` with `recentEvents` + `lastSignificantInteraction`. (g) Extend `### DialogueLogic` to declare the new `BuildPrompt` signature alongside the existing `BuildContext`. |
| `docs/sdd/last-breath-poc-sdd.md` | `### DialogueSystem.Inputs`: add `EVT-interaction-completed`. `### DialogueSystem` gets a new "Decision — availability gating" subsection. `### TerminalSystem.Notes`: reference `TerminalChatView` MonoBehaviour binding. |
| `docs/decisions/0006-transport-and-llm-policy.md` | Dated amendment block at end: (a) extend §Decision item 5 allowlist to include `recentEvents` and `lastSignificantInteraction`; (b) new sub-policy: "`SendAsync` is never called when `AvailabilityState != Online`" — *strengthens* `GAMEPLAY-CODE-DIALOGUE-NO-DIRECT-LLM`; (c) extend tag set with `"silent"`; (d) note `format: "json"` is non-toggleable, hard-coded in `OllamaHttpTransport`. |
| `docs/registry/architecture.yaml` | (# NEW) Add `CFG-AVAILABILITY-RULE`. (# NEW) Add `CLASS-IFocusLabel` under `SYS-DIALOGUE.classes`. Extend `SYS-DIALOGUE.subscribes` with `EVT-interaction-completed`. Annotate the `SYS-DIALOGUE` block with a comment noting persisted DTO fields. |
| `docs/registry/glossary.md` | Add canonical entries: `availability state`, `availability rule`, `garbled reply`, `silent turn`, `focus label`. Anti-glossary: forbid "AI offline meter", "ship AI status bar" (per the same opacity logic as the three axes). The terms intentionally avoid the noun `response`, which the glossary already binds to `structured response` (the LLM JSON shape). |
| `.claude/rules/gameplay-code.md` | (a) Update `GAMEPLAY-CODE-DIALOGUE-PROMPT-MUST-WITHHOLD` allowlist citation to include `recentEvents` and `lastSignificantInteraction` and to cite both `BuildContext` AND `BuildPrompt` as the audit surface (current rule cites only `BuildContext`). (b) Strengthen `GAMEPLAY-CODE-DIALOGUE-NO-DIRECT-LLM` with the availability-gate clause. |

---

## Verification

When the implementation plan downstream of this spec runs, it must satisfy:

- `grep -n "RecentEventTag\|MotherAvailabilityRule\|AvailabilityState\|IFocusLabel" docs/tdd/last-breath-poc-tdd.md` returns hits for all four.
- `grep -n "availability state\|garbled reply\|silent turn\|availability rule\|focus label" docs/registry/glossary.md` returns five hits.
- `grep -n "CFG-AVAILABILITY-RULE\|CLASS-IFocusLabel" docs/registry/architecture.yaml` returns hits for both.
- `grep -n "EVT-interaction-completed" docs/registry/architecture.yaml` returns at least one hit under `SYS-DIALOGUE`.
- ADR-0006 has a dated amendment block citing: the allowlist extension, the availability-gating sub-policy, the `"silent"` tag, and the `format:"json"` hard-coding.
- `python3 scripts/audit-md.py --quiet` returns 0 new BROKEN_REFS.
- An EditMode test exercises `DialogueLogic.EvaluateAvailability` for each case: zone-only match, required-flags match, forbidden-flags reject, default-Online fallback when no rule matches, and **priority tie-break asserting that two equal-priority matching rules resolve to the one earlier in the input list** (deterministic file order).
- An EditMode test exercises `DialogueSystem.SubmitTurnAsync` per branch: `Online` calls `MockTransport.SendAsync` exactly once; `Garbled` calls `SendAsync` zero times, picks `cfg.garbledReplies[turnCount % length]` (assert exact index), ticks `integrity` down by the configured curve amount; `Silent` calls `SendAsync` zero times, fires `EVT-dialogue-response-ready` with `tags=["silent"]`, and leaves `integrity` unchanged (assert with `Mathf.Approximately`).
- An EditMode test exercises the restore demote: `recentEvents.age` are all `EarlierThisRun` after `DialogueSystem.RestoreState(dto)` regardless of stored value, and no event is published during the restore call (use a recording subscriber to assert event count == 0).

---

## Out of scope (explicitly)

- Any C# under `src/`. This is a documentation spec; implementation is a separate plan.
- Prefab building, Canvas authoring, font import, palette choices — Unity-specialist tasks at implementation time.
- The actual text of MOTHER's `systemPrompt` — `DialogueAIConfig.systemPrompt` is `[TextArea]`, designer-authored. This spec locks the *required sections*, not the wording.
- Retry / backoff at the transport layer (kept by ADR-0006).
- Cross-run memory of past playthroughs (kept out by Plan 005).
- Multiple distinct AI personalities per terminal (kept out by Plan 005).
- Availability gating beyond zone + flags (no oxygen-bucket gating, no agitation-bucket gating, no time-of-run gating). Follow-up edits extend `MotherAvailabilityRule` if needed.
- The mapping from `EVT-flag-changed` transitions to specific `RecentEventTag` values (e.g., which flags trigger `ProtocolBreach`, which trigger `ObjectiveBlocked`, etc.). The implementation plan that consumes this spec must enumerate this mapping as a designer-authored table or as small SO assets; this spec only locks the tag enum and the queue mechanics.
- **Long-term summary compaction (deferred extension).** When `recentExchanges` reaches `maxHistoryDepth` and starts evicting, the current design drops the oldest exchange. A future extension would add a fire-and-forget compact-on-evict path: when an exchange is evicted, `DialogueLogic` issues a separate LLM call asking the model to fold the evicted exchange into a running summary, and accumulates the result into a new `DialogueDto.longTermSummary` field that is fed back into subsequent prompts as long-term memory. **Deferred** because PoC volume (≤10 turns per run) does not exercise it and the savefile is already small. When picked up later, it is purely additive: one new DTO field (`longTermSummary`), one new method on `DialogueLogic` (`SummarizeAndCompactAsync`), one new prompt template on `DialogueAIConfig` (`compactionSystemPrompt`) — no refactor to anything in this spec.
- Streaming responses, function calling, multimodal input (kept out by ADR-0006).
- Cloud-Ollama production deployment.

---

## Provenance

This spec consolidates a brainstorming session held 2026-05-12. Decisions were made interactively against the existing material in:

- `AGENTS.md` (Global rules — English-only, stable IDs, canonical glossary, package discipline)
- `docs/decisions/0002-monobehaviour-vs-plain-csharp-split.md`
- `docs/decisions/0004-flag-and-narrative-event-model.md`
- `docs/decisions/0005-save-system-architecture.md`
- `docs/decisions/0006-transport-and-llm-policy.md`
- `docs/plans/005-ship-ai-dialogue.md`
- `docs/sdd/last-breath-poc-sdd.md` `§DialogueSystem`, `§TerminalSystem`, `§SaveSystem`, `§HudController`
- `docs/tdd/last-breath-poc-tdd.md` `### DialogueContext`, `### DialogueLogic`, `### DialogueSystem`, `### TerminalSystem`, `### TerminalInteractable`, `### DialogueAIConfig`, `### LlmTransportConfig`, `### IDialogueTransport`, `### DialogueResponse`, `### DialogueDto`
- `docs/registry/architecture.yaml`
- `docs/registry/glossary.md`
- `.claude/rules/gameplay-code.md`

No prior decision in those documents is overturned. This spec only extends — adds fields to allowlists, adds a new SO type, adds a new evaluator function, adds UI components, adds a model name, adds a tag value.
