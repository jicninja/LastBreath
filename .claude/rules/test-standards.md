# Rules — Test Standards

## What gets tested

- **Formulas**: oxygen, agitation → EditMode unit tests.
- **Critical events**: oxygen-depleted, presence-event-fired → PlayMode smoke.
- **PoC golden path**: full smoke of the scene (see `qa-tester.md`).

## What is NOT tested

- Visuals (lights, glitches, particles).
- Cosmetic UI.
- Audio.
- Coverage for coverage's sake.

## Structure

```
tests/
  EditMode/
    OxygenSystemTests.cs
    AgitationSystemTests.cs
  PlayMode/
    PocSmokeTests.cs
```

- One test = one conceptual assertion. If a test fails, the message says what broke.
- Naming: `MethodName_Scenario_ExpectedResult`. Example: `Tick_InExteriorWithHighAgitation_ConsumesAtAcceleratedRate`.
- No `Thread.Sleep`. For PlayMode use `yield return new WaitForSeconds` or specific frames.

## Test data

- Test ScriptableObjects live in `tests/EditMode/Resources/` with the `_Test` suffix.
- They never depend on production assets (prod assets change).

## Hard rules

- A test cannot depend on another test (execution order is not guaranteed).
- A test does not touch disk, network, or `PlayerPrefs`.
- If a test is flaky three runs in a row, delete it or fix it — do not ignore it.
