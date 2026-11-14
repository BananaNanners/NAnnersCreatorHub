# NAnners Creator Hub 0.2.0-dev4-fix2 — Persistent save status

## User feedback

After batch narration assigned two new references, the bottom message said to save the project but did not explicitly show an unsaved state. After saving, the status changed to “Saved” and was clearer.

## Changes

- New persistent right-aligned state indicator beside the usual bottom activity message:
  - **NO PROJECT OPEN** before loading or creating a project
  - **UNSAVED CHANGES — Save Project** after changes, including batch narration assignments
  - **SAVED** when an existing project is open and no changes remain
  - **NOT SAVED — Save Project** if a new project has no saved path
- The window title also adds **— UNSAVED** for modified projects.
- Batch assignments now explicitly say **UNSAVED CHANGES** in their immediate activity message.
- Reporting, marker export, and other activity messages cannot hide the persistent save state.
- The indicator changes to **SAVED** only after `save_project` finishes successfully.
- No existing projects, recordings, or output files are automatically changed.

## Desktop verification

1. Open NAnners Creator Hub; confirm version **0.2.0-dev4-fix2**.
2. Open a saved tutorial project. The bottom-right state should say **SAVED**.
3. Modify a section or assign generated narration. The state should change to **UNSAVED CHANGES — Save Project**, while the activity text remains readable.
4. Click **Save Project**. Verify the state changes back to **SAVED**, the activity says `Saved: ...`, and the title no longer says UNSAVED.
5. Open the Kokoro tab and back; the saved/unsaved state should remain accurate.

## Preservation

All previous releases including `0.2.0-dev4-fix1` are retained for rollback. This is a local checkpoint only, not a GitHub release.
