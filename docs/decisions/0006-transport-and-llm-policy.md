---
id: ADR-0006-transport-and-llm-policy
type: decision
status: accepted
date: 2026-05-12
related: [PLAN-005, SYS-DIALOGUE, SYS-TERMINAL]
---

# ADR 0006: Transport and LLM policy

## Context

The ship-AI dialogue mechanic introduced in PLAN-005 requires the game to call an LLM at runtime: free-text turns from the player are sent to a language model, and the model returns a structured response that drives `SYS-DIALOGUE`. Until this ADR, the project had no precedent for **network calls, external services, secrets handling, JSON parsing of non-flat shapes, or streaming**. Every later doc (SDD, TDD, reviewer rules) must cite a single source of truth for the transport policy; without one, the same questions resurface at every layer.

The decision is shaped by three constraints from existing ADRs:

- ADR-0002: formula-bearing logic lives in plain C#, MonoBehaviour is an adapter. The transport must live behind an interface that plain-C# logic can drive.
- ADR-0004: no SO event channels, no runtime-mutable ScriptableObjects. Endpoint *configuration* can live in a SO; endpoint *state* cannot.
- ADR-0005: only `SaveSystem` touches disk. The transport never reads/writes save files; endpoint configuration is not save state.

And by one constraint from the user's design intent: the team will host **Ollama on a separate machine** during dev (so the GPU running the LLM is not the GPU running the game) and **Ollama in the cloud** eventually for production. No commitment to a paid hosted API for the PoC.

## Decision

**A single transport seam, HTTP-only, asynchronous, mockable, configured by environment-then-asset, with no secrets-store this round.**

Concretely:

1. **Seam.** `IDialogueTransport` is the only interface through which dialogue logic touches the outside world.

   ```csharp
   public interface IDialogueTransport
   {
       Awaitable<TransportResponse> SendAsync(string prompt, CancellationToken ct);
   }

   public readonly struct TransportResponse
   {
       public readonly string Body;        // raw response body (JSON string)
       public readonly TransportStatus Status; // ok | timeout | network_error | malformed
   }
   ```

   One method, one return type, no streaming, no per-turn options. Parameters that need to flow into the model (temperature, model name, system prompt) are baked into the implementation's constructor or its `CFG-LLM-TRANSPORT` config.

2. **Default implementation.** `OllamaHttpTransport` issues an HTTP POST against an Ollama-compatible chat endpoint. Endpoint resolution order:
   - **(a)** Environment variable `LASTBREATH_LLM_ENDPOINT` (developer override; takes precedence everywhere it is set).
   - **(b)** `CFG-LLM-TRANSPORT` ScriptableObject field `defaultEndpoint` (committed in-repo default).
   - **(c)** Hard-coded fallback `http://localhost:11434` when neither is set, so misconfiguration surfaces as a visible "connection refused" rather than silent mocking.

3. **Mock implementation.** `MockTransport` returns canned `TransportResponse`s keyed by simple input matching. Used in EditMode tests and as the editor-time offline fallback. EditMode tests **never** instantiate `OllamaHttpTransport`.

4. **No secrets-store this round.** Ollama endpoints are URLs, not API keys. If a future transport that requires authentication is added (Anthropic, OpenAI, a token-bearing proxy), it requires a follow-up ADR addressing key storage, build-time vs runtime resolution, and reviewer rules — not this one.

5. **JSON parsing via `JsonUtility`.** The structured response shape (`{ speech, mandateDelta, tags }`) is flat by design so `JsonUtility.FromJson` handles it. **Newtonsoft.Json is not added to the project.** If a future feature genuinely needs dictionaries or polymorphic deserialization, a separate plan adds the package; ADR-0005's "Newtonsoft if needed" hedge does not retroactively authorize it here.

6. **Async pattern.** `async Awaitable<...>` with `destroyCancellationToken`, per `docs/process/unity-patterns.md §6`. No coroutines, no `Task<T>` exposed at the seam (Awaitable is Unity-native and cleaner about the main thread).

7. **No streaming.** Single blocking call per turn. Latency budget: 4-second p95. On timeout, the transport returns `TransportResponse { Status = timeout }`; `DialogueLogic` substitutes a configured offline reply and ticks `integrity` down. **Failure looks like AI degradation** — on-genre, not a separate error state.

8. **Restore invariant.** `IDialogueTransport.SendAsync` is **never** called during `GameState.Loading`. Saved exchanges are the canonical truth; restoring a save never re-queries the model.

## Alternatives considered

- **Anthropic API (Claude) direct from the client.** *Rejected because* (a) it requires API-key storage, which the project has no policy for and which would need a separate ADR anyway; (b) cost per turn is non-zero even for a PoC; (c) the user explicitly named Ollama as the target stack. The seam is interface-shaped, so adding `AnthropicTransport` later is one new class plus one new ADR for key handling, no other doc churn.
- **Embedded local model via Unity Sentis or `llama.cpp` plugin.** *Rejected because* (a) it consumes GPU/CPU on the player's machine that the game already wants; (b) ships large model weights with the build (~4–7 GB); (c) the user explicitly wants the LLM on a separate machine. Sentis remains a future option for non-dialogue ML (e.g., audio classification) but is not in scope for `SYS-DIALOGUE`.
- **Newtonsoft.Json dependency.** *Rejected because* (a) the structured response is flat, (b) ADR-0005 already chose `JsonUtility` for save data, and (c) adding a third-party package needs its own plan per the project's package discipline. If a future response shape needs Newtonsoft, a follow-up ADR addresses it explicitly.
- **Streaming responses (SSE or chunked).** *Rejected for PoC because* (a) blocking calls keep `SYS-DIALOGUE` simple, (b) the "typing indicator" UX can be faked from a single response, (c) timeout-as-degradation is on-genre and cleaner than partial-response state, (d) `Awaitable` does not natively model async iterators without ceremony. Re-open if playtests show the wait feels broken.
- **Static `LlmClient` singleton.** *Rejected because* it violates `gameplay-code.md` "no global singletons" and makes mocking in tests fragile. The interface is owned by `SYS-DIALOGUE`, injected via `[SerializeField]` reference to a `CFG-LLM-TRANSPORT`-bound MonoBehaviour wrapper.

## Consequences

- **Easy:** the seam is mockable, the default transport is free to run (self-hosted Ollama), endpoint configuration travels through env vars (zero-friction local dev) and a committed SO (zero-friction CI/build). No secret-store code paths. Tests target `DialogueLogic + MockTransport`; the real network is exercised only by manual play.
- **Hard:** running the game without a reachable Ollama means every live-channel turn falls back to the offline reply and ticks `integrity` down. Reviewers must remember that "AI sounds broken" is a transport-misconfiguration smell, not always a design bug. The 4-second timeout requires Ollama to be reachable on a fast LAN or fast WAN; remote-cloud-Ollama with 8+ second latency would degrade the experience until either the budget rises or streaming is added.
- **Accepted loss:** no native function-calling / tool-use protocol (the structured response is a contract enforced by the system prompt + `JsonUtility` parsing — the model can lie about it). No multimodal input. No streaming. No retries-with-backoff at the seam (left to `DialogueLogic`'s degradation policy).
- **Reviewer cost:** three new rules added in PLAN-005 step F:
  - `GAMEPLAY-CODE-DIALOGUE-NO-DIRECT-LLM` — no class outside `SYS-DIALOGUE` calls `IDialogueTransport` directly.
  - `GAMEPLAY-CODE-DIALOGUE-NO-SECRETS-IN-SAVE` — `DialogueDto` cannot include endpoint URLs or tokens.
  - `GAMEPLAY-CODE-DIALOGUE-PROMPT-MUST-WITHHOLD` — the prompt builder consults an explicit allowlist; no reflection-based "send everything."

## Notes

This ADR deliberately does not lock the **prompt content**, the **persona shape**, or the **degradation curves** — those live in the GDD (PLAN-005 step A) and in `DialogueLogic` (PLAN-005 step E). It locks only the transport, the seam shape, and the policy boundary. Replacing Ollama with Anthropic or any other provider is a one-class change behind the existing seam; replacing the seam itself requires superseding this ADR.

## Amendment — 2026-05-12 (ratified via SPEC-2026-05-12-ship-ai-context-and-runtime)

This amendment extends the original decision without overturning any of items 1–8. It addresses four concrete gaps surfaced by the SPEC-2026-05-12 brainstorm.

**A. Allowlist extension (extends §Decision item 5).** The exhaustive allowlist of fields visible to the LLM via `DialogueLogic.BuildContext` / `BuildPrompt` is now:

- `zone` (string)
- `oxygen` (`OxygenBucket`)
- `agitation` (`AgitationBucket`)
- `objectiveText` (string)
- `mandate` / `integrity` / `budget` — sent **bucketed** at serialization (`very-low | low | medium | high | very-high`); the underlying floats stay in `DialogueContext` for `DialogueLogic` math but never enter the prompt
- `recentEvents` (`IReadOnlyList<RecentEvent>`; closed `RecentEventTag` enum + `RecentTagAge` enum; cap 10; FIFO eviction)
- `lastSignificantInteraction` (nullable string sourced exclusively through `IFocusLabel.FocusLabel`, never via reflection)
- `recentExchanges` (bounded by `DialogueAIConfig.maxHistoryDepth`, default 5)

The TDD `### DialogueContext` `Withheld by design` block is amended to read: *"exact presence cooldowns or per-firing timestamps are withheld; aggregated `RecentEventTag.PresenceEvent` entries with `RecentTagAge` buckets are part of the allowlist."* Reviewer rule `GAMEPLAY-CODE-DIALOGUE-PROMPT-MUST-WITHHOLD` cites both `BuildContext` and the new `BuildPrompt` as the audit surface.

**B. Availability gating sub-policy.** `IDialogueTransport.SendAsync` is invoked **only when `DialogueLogic.EvaluateAvailability(...)` returns `Online`**. The two non-Online states are entirely transport-bypassing:

- `Garbled` → `DialogueSystem` selects a canned reply from `DialogueAIConfig.garbledReplies[]` deterministically (`turnCount % length`), tags the synthetic response `["nonsequitur","false-claim"]`, ticks `integrity` down per the configured curve, and fires `EVT-dialogue-response-ready`. This is consistent with item 7 ("failure looks like degradation") — the failure mode is now also designer-triggerable, not only transport-triggered.
- `Silent` → `DialogueSystem` synthesizes an empty-speech response with `tags=["silent"]`, fires `EVT-dialogue-response-ready` (so the UI renders the "NO RESPONSE" indicator), and does NOT touch `integrity` (silence is environmental, not internal failure).

This **strengthens** `GAMEPLAY-CODE-DIALOGUE-NO-DIRECT-LLM`: not only is `SendAsync` confined to `SYS-DIALOGUE`, it is also confined to the `Online` branch.

**C. Tag enum extension.** The closed tag set is now `[refusal, policy, evasion, compliance, nonsequitur, warning, false-claim, silent]`. `silent` is reserved for synthesized responses with empty `speech` and never appears on real LLM outputs.

**D. `format: "json"` is non-toggleable.** Item 5 of the original decision selected `JsonUtility` for parsing. This amendment makes it explicit that `OllamaHttpTransport` hard-codes `format: "json"` in the request body; the field is not exposed on `LlmTransportConfig` and designers cannot disable it. Removing the flag would require a follow-up ADR amendment, not a config change.

The amendment introduces no new transport, no new secret-store path, and no new event class; it strictly tightens the existing seam policy and extends the documented allowlist.
