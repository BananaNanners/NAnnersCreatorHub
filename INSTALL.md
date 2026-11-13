# NAnners Creator Hub — 0.1.0 release preparation

Status: **release candidate preparation; NOT final v0.1.0**.

## Supported environment

CachyOS / KDE Plasma, Python 3.11+, PySide6 and FFprobe on PATH. This is a user-local installation using the existing system Python environment. No sudo or system-wide package changes.

## Install or upgrade

From the checked-out source folder:

```fish
cd ~/Projects/NAnnersCreatorHub
python tools/manage_install.py install
```

This creates a version-specific source copy under `~/.local/share/nanners-creator-hub/releases/VERSION`, switches the `current` symlink atomically, and creates a launcher in `~/.local/bin/nanners-creator-hub` plus a KDE application entry. Installed release versions are retained. The installer refuses to overwrite another app's existing launcher or to replace an already installed version of the same name. To upgrade, use a source tree with a **new version**.

## Run

Start `NAnners Creator Hub` from KDE's app launcher or run:

```fish
~/.local/bin/nanners-creator-hub
```

## List / rollback

```fish
python tools/manage_install.py list
python tools/manage_install.py rollback 0.1.0-dev5
```

Rollback can only select versions actually installed and retained in the versioned release directory. It changes the active application version and leaves project files as-is. If future app versions change project JSON schema, backward-compatible rollback will need separate verification.

## Testing

```fish
env PYTHONPATH=src python -m unittest discover -s tests -v
```

Installer tests set an isolated temporary HOME/XDG_DATA_HOME; they do not change your actual app installation.

## Known limitations and release gate

- All dev1–dev5 features work as assisted-editing planning tools, not a video editor
- Existing `.kdenlive` projects are never modified
- Kdenlive JSON import was tested with a single section marker at frame zero; **multi-marker timing remains unverified in a real Kdenlive timeline**
- The generated guide plan assumes sequential sections; real footage transitions, gaps, and B-roll may shift guides
- PySide6 must already be importable by the Python interpreter used by the launcher
- Final 0.1.0 packaging, license choice, install/rollback UI tests, release tagging and any GitHub publishing are not yet complete

**Source recordings, tutorial.json, exported reports and marker JSON remain untouched by install/upgrade/rollback.**
