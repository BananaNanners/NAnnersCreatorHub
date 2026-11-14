# NAnners Creator Hub v0.2.0 — Release Notes

## Highlights

The second stable release expands the local-first tutorial planner into a production-assistance workflow with direct Kokoro narration and Kdenlive editing integration.

### Kokoro Narration Studio
- Detect local ONNX model and voice archive; select from available voices, including `em_alex`.
- Write or paste narration and generate WAV files in one click.
- Preview a generated take, regenerate without overwriting earlier takes, and save one original-script TXT per new WAV.
- Keep the original script separate from editable pronunciation substitutions, including `NAnners => Nanners` and `Wineland => Wine land`.
- Generate multiple narration takes from scripted tutorial sections; review and explicitly approve section assignments.

### Assisted Editing improvements
- Built-in recording preview and scrubber with source IN/OUT controls.
- Timestamped thumbnail browser sampling 12 frames per imported video.
- Narration waveform playback, length comparison, and optional footage-length matching.
- Safe removal of imported media references without deleting underlying files.
- Persistent saved/unsaved project indicator.
- Existing readiness reports, guide exports, and non-destructive project data retained.

### Kdenlive Starter Timeline (experimental)
- Export a NEW `.kdenlive` project from Confirmed sections.
- V1: selected footage source ranges in sequential order.
- A1: selected narration aligned to each section's start.
- Section guides for every included section, with project FPS selection.
- Tested with Kdenlive 26.08.3 on CachyOS; the user visually verified both timeline tracks, guides and editable clips.

## Validation

- Automated regression suite: 114 tests during dev8, with additional release regression checks.
- Real FFmpeg tests validated extracted thumbnails and narration waveforms without modifying recordings.
- MLT renderer accepted and rendered the generated project with video and audio.
- Dev1–dev8 milestones underwent user desktop checks on KDE Plasma; all eight final dev8 checks passed.
- Installer retains earlier versions and supports rollback.

## Important limitations

The starter timeline is **not a finished edit**. It is gapless, does not create transitions, overlays, subtitles, or B-roll, and mutes the original recording audio. If narration is shorter than its footage, the remainder is silent; longer narration is truncated at the section boundary. The section editor shows timing warnings but does not automatically correct script/footage mismatches.

Only Confirmed sections are included in automatic starter exports. Existing Kdenlive projects are never edited by export. Confirm paths, video ranges, FPS, and narration alignment before publishing a video. Generated projects reference original source files by absolute path; moving those sources afterward may break links.

Local Kokoro inference requires `kokoro-tts`, a model, and voice data. Preview, waveform and thumbnail features require installed FFmpeg and Qt Multimedia.

## Install and rollback

See [INSTALL.md](INSTALL.md); versioned installation retains v0.1.0 and all available development checkpoints. Use `python3 tools/manage_install.py list` to inspect active releases.

## License

MIT — [LICENSE](LICENSE).
