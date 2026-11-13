# NAnners Creator Hub

Local-first YouTube tutorial production assistant for Linux, Kdenlive, OBS and Kokoro.

## Current milestone

**0.1.0-dev2**: Assisted-editing project shell with read-only media import and inspection.

- Single-window PySide6 application, project create/open/save
- Versioned JSON manifests, atomic saving and backwards-compatible optional `media` list
- Read-only FFprobe metadata: duration, codecs, resolution, frame rate, size, type
- Manual multi-file import, duplicate detection, rescan, missing/error status
- Preserve original recordings: always on
- Section markers: enabled by default, export planned
- Transition suggestions: off
- Automatic Timeline Mode: future release, not implemented yet

## Run

From the project directory:

```fish
env PYTHONPATH=src python -m nanners_creator_hub
```

## Tests

```fish
env PYTHONPATH=src python -m unittest discover -s tests -v
```

## Development safety

**No media files or existing Kdenlive projects are modified by the application.** File import stores paths and metadata in the project manifest; scanning invokes FFprobe with no write commands. Save only writes the selected project JSON path. Your `tutorial.json` project remains untracked by Git and is not part of the source checkpoint.

## Manual smoke test for dev2

1. Open your dev1 `tutorial.json` and verify its name.
2. Choose **Import Media** and select a short OBS recording and a Kokoro WAV file.
3. Verify metadata appears; choose **Save Project**, close, reopen and confirm the media list survives.
4. Optionally test a disposable file by importing it, moving it aside manually, then choosing **Rescan Media** to see **missing** status. Return it afterward.

## Next steps

dev3 will focus on script sections, manual media assignment, selected footage ranges, and review states. More advanced visual matching and Kdenlive exports are not implemented in dev2.
