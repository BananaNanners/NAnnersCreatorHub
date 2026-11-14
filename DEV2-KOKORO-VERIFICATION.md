# NAnners Creator Hub — 0.2.0-dev2 Kokoro generation

## Implemented

- Type or paste a narration script in the **Kokoro Narration Studio** tab.
- Choose a voice, language, speaking speed, model file, and voices archive.
- Choose a take name and an output directory, then click **Generate WAV**.
- Kokoro runs using an asynchronous Qt process; the UI remains responsive.
- Each successful take gets a unique timestamp/ID WAV name and a matching TXT script snapshot.
- Generation uses an isolated temporary directory within the output folder; completed files are published only after WAV validation. Existing WAV and script files are never overwritten.
- Generation failures and user cancellation clean up temporary staging files.
- Closing the hub during generation prompts before cancelling and closing.
- Existing v0.1.0 project schema and Assisted Editing remain untouched.

## Tested on CachyOS

- Kokoro-tts 2.3.2 with em_alex, en-gb, and the installed ONNX/voice library generated a valid 24 kHz PCM WAV in an isolated temporary directory.
- Automated regression tests cover empty scripts, unsafe filenames, unique take names, WAV validation, generation failure, and mock async GUI generation.
- The real GUI/button workflow requires the user's hands-on verification.

## Desktop verification

1. Open NAnners Creator Hub; confirm title **0.2.0-dev2**.
2. Open the **Kokoro Narration Studio** tab and confirm Kokoro is ready with 50 voices.
3. Choose `em_alex` and English GB, speaking speed 1.0×.
4. Enter a short test script (for example: "Welcome to NAnners Creator Hub.").
5. Set a take name such as `dev2-test`; choose an output folder you want to use.
6. Press **Generate WAV**. The UI should stay responsive; wait for the green success message.
7. Click **Open Output Folder**. Confirm a new `.wav` and matching `.txt` file are present; play the WAV using your desktop audio player.
8. Click **Generate WAV** again. Confirm another pair is added without replacing the first one.
9. Confirm your original tutorial project, existing WAVs, and Kdenlive files are unchanged.

The built-in audio player, pronunciation presets, narration takes browser and automatic project-section assignment are planned for later checkpoints. The output file can currently be imported through the existing **Import Media** button.

## Rollback

The stable v0.1.0 and earlier dev versions remain installed. Use:
```fish
cd ~/Projects/NAnnersCreatorHub
python tools/manage_install.py list
python tools/manage_install.py rollback 0.2.0-dev1
```

Do not publish this dev checkpoint to GitHub as a stable release.
