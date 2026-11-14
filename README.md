# NAnners Creator Hub

**v0.2.0** — A local-first, Linux-native YouTube tutorial production assistant with Kokoro narration and Kdenlive starter-timeline export.

Developed and tested on CachyOS / KDE Plasma. Licensed under [MIT](LICENSE).

## Features

### Assisted Editing
- Organize tutorial sections, scripts, media references, footage IN/OUT points, review status, and notes.
- Inspect imported footage and narration with read-only FFprobe; rescan missing files and safely remove media *references* without deleting source files.
- Preview and scrub video, browse 12 timestamped thumbnails from each imported video, then explicitly apply source ranges.
- View narration waveforms, compare footage/narration lengths, and propose synchronization changes.
- Generate editing-readiness Markdown reports and frame-accurate Kdenlive section-marker JSON.
- Persistent **SAVED / UNSAVED CHANGES** indicator; project changes only persist when you save.

### Kokoro Narration Studio
- Detect installed local Kokoro models, voice archives, and available voices, including `em_alex`.
- Enter a script, choose voice/language/speed, and generate WAV narration without terminal commands.
- Play generated audio, cancel generation, and produce uniquely named WAV + original-script TXT pairs.
- Save editable pronunciation rules (e.g. `NAnners => Nanners`, `Wineland => Wine land`) while keeping original scripts unchanged.
- Generate narration in batches for selected tutorial sections, review results, and explicitly assign WAVs. Existing assignments are not replaced by default.

### Kdenlive Integration
- Export section-start marker JSON using the actual timeline FPS.
- Export a **new Kdenlive starter project** with confirmed footage ranges on V1, narration on A1, and section guides.
- Preview the export plan and its exclusions before creating a project. Existing `.kdenlive` files are never overwritten.

## Run

Requires Python 3.11+, PySide6 (Qt Multimedia and MultimediaWidgets), FFmpeg, and FFprobe. Kdenlive is required to open the starter project, but is not needed for the other features. Kokoro generation additionally needs the `kokoro-tts` command and local model/voice files.

From a source checkout:

```sh
PYTHONPATH=src python3 -m nanners_creator_hub
```

Install user-locally from a checkout:

```sh
python3 tools/manage_install.py install
```

Then use the **NAnners Creator Hub** KDE app launcher.

See [INSTALL.md](INSTALL.md) for installation, version listing and rollback.

## Test

```sh
python3 tools/run_tests.py
```

The Qt-aware test runner cleans up UI widgets before interpreter shutdown and isolates the waveform GUI rehearsal. Tests create synthetic content in temporary directories.

## Safety and limitations

- Media inspection, previews, thumbnail sampling and waveform extraction are read-only; existing source audio/video is never altered.
- New narration takes and Kdenlive exports use unique/new filenames and do not replace existing files.
- Saving an explicitly selected project JSON replaces that manifest atomically. Back up important project files independently.
- The starter timeline is **experimental**: it assumes sequential sections without transitions or B-roll, mutes original footage audio, leaves silence after shorter narration, and truncates narration longer than the footage section. Review every result in Kdenlive.
- Exporting a starter project does not modify or read back an existing Kdenlive edit.
- Confirm source ranges, source availability, frame rate, and review status before using the generated timeline for production.
- Local model inference and video extraction use installed system utilities; no cloud service is required.

## License

MIT — see [LICENSE](LICENSE).
