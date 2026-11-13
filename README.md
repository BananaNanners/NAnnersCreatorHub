# NAnners Creator Hub

Local-first YouTube production assistant for Linux, Kdenlive, OBS and Kokoro.

## Current milestone: 0.1.0-dev4

- Assisted editing with numbered sections, scripts, narration and footage references
- Manual footage in/out ranges and review statuses
- Read-only FFprobe media inspection
- **Readiness Report**: section-by-section readiness and timing analysis
- **Export Report**: new, non-overwriting Markdown report containing review checklists
- Timing differences are advisory, not proof that the footage is incorrect
- Original recordings are never modified by the application
- Existing project files from dev1–dev3 remain compatible

Not yet implemented: semantic footage matching, thumbnails, in-app playback, Kdenlive marker export, automatic timeline generation, or suggested transitions.

## Launch

```fish
cd ~/Projects/NAnnersCreatorHub
env PYTHONPATH=src python -m nanners_creator_hub
```

## Tests

```fish
env PYTHONPATH=src python -m unittest discover -s tests -v
```

## Manual dev4 test

1. Launch dev4 and open `tutorial.json` (your existing file).
2. Check that the imported media and the section you created in dev3 are still present.
3. Click **Readiness Report**. Your existing section may need review because it is not marked Confirmed or its durations differ.
4. Click **Export Report**, choose a **new** `.md` filename, then open that file in your text editor.
5. Check section name, narration duration, selected footage duration, difference and review checklist.
6. Confirm that your existing recordings and project are still available and unchanged.

Markdown exports are generated from the current in-memory project state. Save the project separately if you want the underlying section edits persisted.

## Git safety

`tutorial.json` is an untracked user project and is intentionally excluded from development commits. All exports must use new filenames; existing files are not overwritten.
