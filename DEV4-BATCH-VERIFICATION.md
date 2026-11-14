# NAnners Creator Hub — 0.2.0-dev4 batch narration checkpoint

## Overview

This development checkpoint joins Kokoro Narration Studio with Assisted Editing. A new **Batch Kokoro Narration…** action appears below the tutorial section list. It generates separate narration takes for selected sections, then offers an explicit review step before assigning any new WAVs to the in-memory project.

## Workflow

1. Open a tutorial project in **Assisted Editing** and make sure the sections have scripts.
2. Open **Batch Kokoro Narration…**.
3. Choose which scripted sections to narrate. A section with an existing narration begins **unchecked**. A blank-script section cannot be selected.
4. Click **Start Batch** to run Kokoro sequentially with the current Narration Studio voice, speed, model, output folder and pronunciation rules.
5. For each successful section, a new uniquely named WAV and a single TXT of the original script are generated. Existing files are never replaced.
6. Review generated results in the batch dialog. Under **Assign new WAV**, new unassigned sections start checked, and sections with existing narration start unchecked.
7. Click **Assign Checked WAVs to Project**. An explicit extra confirmation is required for any section that already has a narration assignment. The application validates all selected WAVs and the unchanged script/assignment snapshots before applying any in-memory changes.
8. The project becomes **unsaved/modified**. Review the references and click **Save Project** to persist them. If you choose **Keep WAVs Only / Close**, the generated files remain available but the project is unchanged.

## Protections

- The project file format is unchanged (schema version 1).
- No project JSON is silently saved by batch generation; the user must use Save Project.
- A checked replacement changes only the project's narration reference. The previous WAV file is never deleted or overwritten.
- Section scripts and existing assigned narration references are snapshotted at batch start; later changes invalidate assignment.
- Media references are scanned with FFprobe, and project changes are applied to a validated copy.
- Cancellation ends remaining generation; already generated files are retained.
- Existing Kokoro single-take generation remains supported.

## Desktop verification

1. Open the hub through KDE and confirm **0.2.0-dev4**.
2. Open an existing or disposable tutorial project with at least two sections that have scripts. If one has existing narration, verify it starts unchecked for batch generation.
3. Click **Batch Kokoro Narration…**, select two scripted sections and start the batch.
4. Confirm each generates a different WAV and one TXT, with no `.speech.txt`.
5. Confirm output filenames correspond to sections and that the pronunciation rules still apply.
6. Verify the section with previous narration defaults to **not replacing** its assignment.
7. Check **Assign new WAV**, approve any replacement prompt intentionally, then confirm the updated narration references and **unsaved project** state.
8. Use **Save Project** only on a disposable test project until satisfied. Verify original recordings and the previously assigned WAV remain intact.

## Automated checks

Batch unit and offscreen GUI tests exercise multiple-section sequencing, unselected blank scripts, existing narration protection, missing WAV validation, snapshot safety, assignment review, unique take publication, and preservation of original project data.

Earlier installs including stable v0.1.0 and dev3-fix1 are preserved for rollback. This dev4 checkpoint remains local; no GitHub push or public release is performed.
