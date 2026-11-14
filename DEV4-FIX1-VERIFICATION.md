# NAnners Creator Hub 0.2.0-dev4-fix1 — Media reference removal

## What changed
- Added **Remove Selected Media…** directly above the imported media table. Select one or more rows before clicking it.
- A confirmation dialog lists the selected references and the section assignments that would be cleared. Choosing **No** leaves everything unchanged.
- Confirming removes only the entries in the project's media list and clears references from any affected tutorial sections; removed footage also resets source in/out points.
- Previously confirmed sections affected by removals become **Needs Review**.
- The change stays **unsaved** until the user explicitly selects **Save Project**.
- No actual video, audio, narration, or exported files are deleted or overwritten by the removal action.
- The batch Kokoro dialog now explains that each row corresponds to a **tutorial section**, not a media file. Use **Add Section** in Assisted Editing for additional batch rows. Sections already assigned narration begin unchecked to protect the existing assignment.
- User-created root-level project JSON manifests are excluded from Git via the project's .gitignore.

## Desktop verification
1. Open NAnners Creator Hub and confirm version **0.2.0-dev4-fix1**.
2. Open your new tutorial project; select the incorrectly imported video row, then **Remove Selected Media…**.
3. Review the confirmation. Confirm the affected footage assignment and its in/out points will be cleared. Choose **Yes**.
4. Verify the media table no longer lists the wrong video, but it still exists in its original folder. Confirm the project indicates unsaved changes and that **Save Project** persists the removal.
5. Import the correct footage and assign it to the section.
6. In Batch Kokoro Narration, confirm there is one row for each tutorial section. Use **Add Section** to create a second row. A section that already has narration starts unchecked.

## Automated verification
84 tests pass, including media removal confirmation, non-destructive file preservation, and section-link cleanup.

Existing stable and dev versions, including 0.2.0-dev4, are retained for rollback. No GitHub release is updated.
