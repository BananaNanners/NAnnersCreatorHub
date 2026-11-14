# NAnners Creator Hub v0.2.0 — Installation, upgrade and rollback

## Requirements

- Linux desktop; tested on CachyOS/KDE Plasma
- Python 3.11+ with PySide6 QtWidgets, QtMultimedia and QtMultimediaWidgets
- `ffmpeg` and `ffprobe` on `PATH`
- Kdenlive (tested on 26.08.3) to view/edit starter timelines
- For narration generation: installed `kokoro-tts` command, `.onnx` model and voices archive

The local installer requires no sudo and does not install Python/system dependencies.

## Install

In a checked-out release:

```sh
cd ~/Projects/NAnnersCreatorHub
python3 tools/manage_install.py install
```

A versioned copy is retained under:
`~/.local/share/nanners-creator-hub/releases/0.2.0`

The launcher `~/.local/bin/nanners-creator-hub` and KDE menu entry `org.nanners.CreatorHub.desktop` resolve through the managed `current` symlink, which points to the active version.

Run it from the KDE application menu or:

```sh
~/.local/bin/nanners-creator-hub
```

The installer refuses to overwrite an unrelated launcher or an already-installed version with the same version number.

## List and rollback

```sh
cd ~/Projects/NAnnersCreatorHub
python3 tools/manage_install.py list
python3 tools/manage_install.py rollback 0.2.0-dev8
```

To restore v0.2.0 after switching back to a retained development version:

```sh
python3 tools/manage_install.py rollback 0.2.0
```

Only installed versions can be selected. Rollback changes the active application; it doesn't remove installed releases, user projects, or recordings. Preserve separate backups before introducing future project-format changes.

## Project and output locations

- Project JSON: user-chosen path
- Local Kokoro settings: `~/.config/nanners-creator-hub/kokoro.json`
- Pronunciation rules: `~/.config/nanners-creator-hub/pronunciations.json`
- Default narration output: `~/Music/NAnnersCreatorHub/Narration`
- Reports, marker JSON and starter Kdenlive projects: user-chosen destinations

Original media is referenced, not copied into the app. Generated `.kdenlive` files use absolute source paths; moving the recordings can break those references.

## Tests

```sh
python3 tools/run_tests.py
```

The test suite verifies media preservation, pronunciation/voice configuration, non-overwriting WAV takes, batch assignment safety, preview workflows, marker positions and Kdenlive starter export. GUI playback and editability were additionally checked manually on CachyOS.

## Notes

- Kdenlive starter export is a prototype: only **Confirmed** sections are included; clips are gapless and there are no automatic transitions, B-roll, or text overlays.
- If narration is shorter than footage, the remainder is silent. Longer narration is truncated at the section end, after an explicit warning.
- Export uses the selected Kdenlive FPS. Always verify the active editing project profile, not just Kdenlive's saved preference.
- Existing v0.1.0 and dev release installations can be retained alongside this release.
