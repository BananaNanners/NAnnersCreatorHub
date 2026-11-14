# NAnners Creator Hub — 0.2.0-dev3-fix1

## Reported issue

Dev3 created two text files alongside every narration WAV:
- `take.txt` (original script)
- `take.speech.txt` (pronunciation-adjusted text)

## Fix

Each new generation now produces **exactly one WAV and one TXT**:
- `take.wav` — Kokoro narration
- `take.txt` — original, unmodified script

The speech-ready preview still applies the editable pronunciation rules to the text sent to Kokoro. The adjusted text is only staged temporarily for the synthesis process and is not published as a second TXT. Existing takes and extra text files from dev3 are untouched.

## Verify in KDE

1. Open the hub, verify title `0.2.0-dev3-fix1`.
2. In Kokoro Narration Studio, use `em_alex` and paste `Welcome to NAnners Creator Hub.`
3. Confirm the speech-ready preview displays `Welcome to Nanners Creator Hub.`
4. Generate in a disposable or separate output folder.
5. Confirm **one new WAV plus one new TXT**, and no new `.speech.txt` file.
6. Open the TXT and verify it retains `NAnners` as originally typed.
7. Play WAV and verify the pronunciation sounds correct.

69 automated tests passed before the focused output-count check was added. Final test results are recorded in the local development run. No existing narrations or projects are automatically changed.

## Rollback

All previous versions, including stable `0.1.0` and dev3, remain available through `python tools/manage_install.py list` and `rollback VERSION`. No GitHub release was modified.
