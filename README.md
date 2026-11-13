# NAnners Creator Hub

A local-first YouTube production assistant for Linux, Kdenlive, OBS and Kokoro.

## Current checkpoint: 0.1.0-dev3

- **Assisted Editing**: create, rename, reorder, and remove tutorial sections
- Assign imported audio and video by file reference, with manual footage in/out points
- Script editor, review notes, statuses: Draft, Needs Review, Confirmed
- Optional filename-only footage suggestion, always subject to confirmation
- Warnings for missing assignments, unscanned references, out-of-range footage, and duration differences
- Open assigned files in the desktop's default media player
- Warn before discarding unsaved project changes
- Read-only FFprobe metadata import/rescan from dev2
- Versioned JSON manifests and atomic saves; dev1/dev2 project files supported
- Preserve source media; section markers still planned for later export
- Automatic Timeline Mode deferred to a future release; transition suggestions disabled

## Run

From the project directory:

```fish
env PYTHONPATH=src python -m nanners_creator_hub
```

## Test

```fish
env PYTHONPATH=src python -m unittest discover -s tests -v
```

## Desktop verification for dev3

1. Launch and open your existing `tutorial.json`; verify both imported media entries remain.
2. Click **Add Section**, rename it, and paste a short narration script.
3. Select the imported WAV under **Narration** and the imported MKV under **Footage**.
4. Set **In point** to 2 seconds and **Out point** to 10 seconds, if that falls within the recording duration.
5. Set **Needs Review**, add a note, click **Save Project**, close and reopen.
6. Verify the section text, media assignments, time range and status are restored.
7. Try **Open Audio** and **Open Footage** if you want to preview them using the default desktop player.

## Boundaries

There is no automatic visual matching, media trimming, preview inside the app, marker export, Kdenlive project generation, or full timeline synchronization in dev3. Timing checks are informational and do not assert that footage actually matches narration. Assigned sources are not changed by the app. Project JSON files are not committed to Git.
