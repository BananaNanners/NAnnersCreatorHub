# NAnners Creator Hub

**v0.1.0** — A local-first YouTube tutorial production assistant for CachyOS/Linux, Kdenlive, OBS and Kokoro. Licensed under MIT.

## Features

- Assisted editing: tutorial sections, script, media assignments, source in/out points and review notes
- Read-only FFprobe media inspection, duplicate detection and missing-file rescans
- Timing difference warnings and an exportable Markdown editing-readiness report
- Kdenlive timeline-guide JSON export with frame-accurate positions for 23.976, 24, 25, 29.97, 30, 50, 59.94 and 60 FPS
- FPS preference detection, prominent mismatch warnings, and export validation
- A 640 × 500 marker export dialog with full-width FPS guidance
- User-local KDE launcher, retained installed releases, and rollback to any retained version

## Run from source

```fish
cd ~/Projects/NAnnersCreatorHub
env PYTHONPATH=src python -m nanners_creator_hub
```

## Install or upgrade

See [INSTALL.md](INSTALL.md). Requires Python 3.11+, PySide6, and FFprobe. The installer does not require sudo and does not install system packages.

## Tests

```fish
env PYTHONPATH=src python -m unittest discover -s tests -v
```

## Important limitations

This is an **assisted-editing planner**, not an automatic video editor. Marker export proposes sequential section-start positions based on user-selected footage ranges or narration durations; it does **not** inspect an existing Kdenlive timeline. Gaps, transitions, B-roll and multiple tracks can shift actual section starts. Check the current Kdenlive project's FPS under Project Settings; its settings can differ from Kdenlive's saved FPS preference.

Marker export creates a *new* JSON file and never edits Kdenlive projects. Existing recordings, Kokoro WAV files and other source media are only referenced and scanned read-only. Automatic Timeline Mode remains planned for a future version.

## License

[MIT](LICENSE)
