# NAnners Creator Hub

Local-first YouTube production assistant for Linux, Kdenlive, OBS and Kokoro.

## Current milestone: 0.1.0-dev5 (release candidate, awaiting KDE/Kdenlive validation)

- Assisted section editing and media references from dev1–dev3
- Readiness analysis and Markdown report export from dev4
- **Kdenlive Markers**: preview and export an optional new JSON file of proposed timeline markers
- Supported rates: 23.976, 24, 25, 29.97, 30, 50, 59.94, 60 fps (rational rates)
- Choose sequence length basis: selected footage ranges or narration durations
- Select a starting timeline frame; markers are generated at successive section starts
- Marker file: JSON list with integer `pos` frame indices, `comment` and `type`
- Exports refuse overwrite; existing media and .kdenlive projects are not altered
- Source projects from dev1–dev4 remain compatible

## Important marker limitation

**These are proposed sequential markers, not marker positions extracted from the actual Kdenlive timeline.** The exporter assumes every section begins immediately after the previous section's selected footage range or narration duration. In real edits, gaps, transitions, B-roll, multiple tracks, etc. can change the true positions. Review and adjust markers in Kdenlive. Choose the exact timeline FPS.

Marker export is separate from automatic timeline generation, which remains out of scope for 0.1.0.

## Launch

```fish
cd ~/Projects/NAnnersCreatorHub
env PYTHONPATH=src python -m nanners_creator_hub
```

## Automated tests

```fish
env PYTHONPATH=src python -m unittest discover -s tests -v
```

## Manual dev5 verification

1. Open your saved `tutorial.json`; ensure imported media and the Welcome section are preserved.
2. Click **Kdenlive Markers**.
3. Select the FPS of a **disposable or backed-up** Kdenlive test project. Set section lengths from **Selected footage ranges**; choose **First timeline frame = 0**.
4. Review preview: with one section, its only marker will be at frame 0. Add a second section with valid sources and ranges if you want to test cumulative positions.
5. Export a **new** `kdenlive-section-markers.json`; verify it opens as JSON with fields `pos`, `comment`, `type`.
6. In a disposable Kdenlive project, import the JSON as **timeline guides** and confirm guide names and frame positions match the preview.
7. Do not import this JSON as clip-specific markers if you want timeline section boundaries.
8. Verify the original `tutorial.json`, recordings and Kdenlive projects have not been modified.

## Release status

Pending hands-on Kdenlive 26.08.3 marker-import validation, UI visual check, and documented install/upgrade procedure. Do not tag a final `v0.1.0` release until these pass.
