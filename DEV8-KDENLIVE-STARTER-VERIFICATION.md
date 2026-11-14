# NAnners Creator Hub 0.2.0-dev8 — Automatic Kdenlive Starter Timeline Prototype

## Scope

This is a **new-project-only** prototype for Kdenlive 26.08.3 using the MLT XML project format. The exporter builds:
- One sequential V1 track of confirmed source video selections (source IN/OUT applied).
- One A1 narration track, beginning with each section's video clip.
- Section-start guides embedded in the sequence at absolute timeline frames.
- Project-bin references for the original videos and audio recordings.
- A project profile matching the first confirmed recording's resolution and the chosen FPS.

Only sections with Review Status **Confirmed** are included. Sections marked Draft or Needs Review are excluded with an explicit explanation. A confirmed section with missing narration, missing footage or invalid range **blocks export**.

## Constraints and safeguards

- The project is a rough starting arrangement, not a completed edit.
- Tracks are gapless, with no transitions, titles or automatic B-roll.
- The audio of original footage is muted; A1 contains only narration.
- A shorter narration is followed by silence; narration longer than footage is *truncated at the boundary*, with a warning that requires confirmation.
- Source time boundaries are rounded to whole output frames; the first timeline frame is zero.
- Kdenlive's saved FPS preference is only a hint, not necessarily the FPS of any existing timeline.
- No existing project can be replaced: complete XML is first written in a temporary file, then linked atomically to a new destination; if the destination exists, export is refused.
- All input video, WAV, JSON and existing .kdenlive files remain unchanged.
- The export is experimental. Kdenlive's UI editability and guide display still need a manual desktop test.

## Verified checks

- Automated tests cover confirmed-only sections, invalid media, timing, source trims, guides, separate audio/video tracks, frame-rate selection, exclusive output and file preservation.
- An isolated 2-section example was generated in a temporary directory and accepted by the local MLT renderer, which produced a short FFV1 video + PCM audio preview.
- Kdenlive is installed at v26.08.3; the XML is formatted for its current sequence-based project format.
- Automated tests are run with `python tools/run_tests.py` for safe Qt teardown.

## GUI verification

1. Open **NAnners Creator Hub 0.2.0-dev8** and load a **disposable copy** of a tutorial project.
2. Mark at least two sections as **Confirmed**, ensuring they each have an assigned recording, narration, and valid footage IN/OUT points. (The current sample project's sections were both Needs Review, so export will remain disabled until manually confirmed.)
3. Open **Automatic Kdenlive Starter Timeline…**, review the proposed V1/A1 sections and the frame rate (60 FPS is the saved local preference).
4. Save the output to a **new, disposable .kdenlive filename**.
5. Open the generated file in Kdenlive 26.08.3; verify the project loads without errors, V1 and A1 clips exist and remain editable, and guide positions correspond to section starts.
6. Play a few seconds to confirm video and narration. Check that any footage/narration length mismatch matches the documented silence/truncation policy.
7. Confirm the hub project, original footage, narration, and pre-existing Kdenlive projects were not modified.
8. Report whether the project loads and all clips/guides appear correctly; if not, do not use the exported project for production editing until corrected.

## Rollback

v0.2.0-dev7 and the stable v0.1.0 remain installed. From the source checkout:
```fish
cd ~/Projects/NAnnersCreatorHub
python tools/manage_install.py list
python tools/manage_install.py rollback 0.2.0-dev7
```

Development changes remain local and have **not** been pushed to GitHub.
