# NAnners Creator Hub

Local-first YouTube tutorial production assistant for Linux, Kdenlive, OBS and Kokoro.

## Milestone

**0.1.0-dev1**: PySide6 single-window application and versioned, atomic JSON project persistence.

- Assisted Editing Mode: initial workflow
- Automatic Timeline Mode: later milestone, not yet implemented
- Source recordings: never edited by this application
- Section markers: enabled by project default; exporting comes later
- Transition suggestions: off

## Launch

From the repository root:

```sh
PYTHONPATH=src python -m nanners_creator_hub
```

## Tests

```sh
PYTHONPATH=src python -m unittest discover -s tests -v
```

## Notes

No video editing or Kdenlive project modification is performed in dev1. Projects are standalone JSON manifests. Saved source references are metadata only. Future releases will add section editing and Kdenlive integration.
