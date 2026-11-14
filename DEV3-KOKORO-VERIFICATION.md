# NAnners Creator Hub — 0.2.0-dev3 pronunciation and playback

## What changed

- **Pronunciation rules:** Editable `Original => Spoken` pairs in the Kokoro Narration Studio, initially `NAnners => Nanners` and `Wineland => Wine land`.
- **Speech-ready preview:** Shows exactly the altered text sent to the Kokoro command; the user's original script stays unchanged.
- **Save/Reload Pronunciations:** Rules are stored separately in `~/.config/nanners-creator-hub/pronunciations.json`, atomically.
- **WAV playback:** The most recently generated WAV can be played and stopped inside the app through Qt Multimedia.
- **Regeneration safety:** Every generation remains a distinct WAV take; each take now includes an original `.txt` and a transformed `.speech.txt`. Existing takes are never overwritten.
- Existing Assisted Editing remains unchanged.

## Intended pronunciation test

Open the Narration Studio and paste this original script:

```text
Welcome to NAnners Creator Hub. Next, select Wineland eleven point zero....
```

The speech-ready preview should show:

```text
Welcome to Nanners Creator Hub. Next, select Wine land eleven point zero....
```

Select `em_alex` / `en-gb`, generate a new WAV, then use **Play Last Take**. Listen specifically to whether Alex says the app name as *Nanners* (one word). If not, change the spoken replacement to another phonetic spelling in the rules editor, then regenerate to a new take. This is an initial pronunciation suggestion, **not a guarantee** that Kokoro will pronounce the word correctly.

## Checks

- 69 automated tests: baseline + pronunciation and playback controls
- Original script and speech copy are stored separately
- Voice preferences and project JSON aren't modified by pronunciation rules
- Existing audio and imported recordings remain untouched
- Final GUI and audio-quality confirmation requires the user on CachyOS

## Rollback

Stable v0.1.0 and dev1/dev2 remain installed. To change versions:

```fish
cd ~/Projects/NAnnersCreatorHub
python tools/manage_install.py list
python tools/manage_install.py rollback 0.2.0-dev2
```

This development checkpoint remains local and is **not published as a stable GitHub release**.
