# NAnners Creator Hub — 0.2.0-dev1 Kokoro foundation

## Goal

Add a Kokoro Narration Studio tab alongside the v0.1.0 Assisted Editing workflow, without generating or modifying audio yet.

## What's included

- Read-only discovery of Kokoro CLI using `PATH`
- Model and voices file selection (browse or type a path)
- Voice discovery from the voice library's NumPy ZIP member names, without running model code
- Voice, language and speed defaults, with `em_alex` selected initially when available
- Model/voices/CLI readiness checks with actionable error messages
- Explicit settings saving to `~/.config/nanners-creator-hub/kokoro.json` using an atomic write
- Disabled `Generate WAV` control until synthesis is implemented in dev2
- Original v0.1.0 project schema and editing workflows unchanged

## Detected on the development CachyOS workstation

- `kokoro-tts` executable from the user's uv tool installation
- `~/Applications/kokoro-tts/kokoro-v1.0.onnx`
- `~/Applications/kokoro-tts/voices-v1.0.bin`
- 50 voices, including `em_alex`

The default narration voice uses English GB (`en-gb`) to match the `em_alex` voice. No model files, existing WAV recordings, user script files, or tutorial JSON files are modified.

## GUI test

1. Open the hub from KDE and confirm title `0.2.0-dev1`.
2. Switch between **Assisted Editing** and **Kokoro Narration Studio**.
3. Confirm Kokoro setup reads **ready**, detects 50 voices and defaults to `em_alex`.
4. Change to another voice, then return to `em_alex`; click **Save Voice & Model Preferences**.
5. Close and reopen the hub, verify the selected voice persists.
6. Confirm **Generate WAV — coming in dev2** is disabled.
7. Verify the original tutorial project and existing editing actions still work.

## Known limitations

The installed CLI is checked for existence but not yet exercised to synthesize speech.
Voice detection uses file listing only; exact model and archive compatibility will be exercised in dev2 with non-destructive output handling. Audio preview and generation, pronunciation presets, narration takes and batch creation are future checkpoints.

The v0.1.0 release remains untouched; dev1 is a separate retained install and is not a public GitHub release.
