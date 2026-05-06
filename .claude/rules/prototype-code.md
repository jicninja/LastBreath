# Rules — Prototype Code

Applies to code under `src/Assets/_Sandbox/**` or any folder marked as prototype.

## Relaxed rules

- You may use `FindObjectOfType` and `GameObject.Find`.
- You may skip tests.
- You may mix UI and logic in a single class.
- You may hardcode constants.

## Still-firm rules

- **Isolation**: nothing under `_Sandbox` is referenced from `_Project`. If a prototype proves good, it is *promoted* into `_Project` with the rigor of `gameplay-code.md`, not imported as-is.
- **Date and purpose in the header**:
  ```csharp
  // Sandbox: agitation-spike — 2026-05-04
  // Test agitation curve when changing zones. Delete on promotion.
  ```
- **Short lifespan**: if a script lives in `_Sandbox` for more than two weeks without being promoted or deleted, delete or promote it.
- **No commits to `main` from sandbox** without going through the promotion plan.
