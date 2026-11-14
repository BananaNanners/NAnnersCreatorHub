# NAnners Creator Hub — v0.1.0 installation and rollback

## Requirements

- Linux desktop (tested on CachyOS / KDE Plasma)
- Python 3.11 or newer with PySide6 available to `python3`
- FFprobe on `PATH`
- Kdenlive optional for editing and guide import

The installer uses existing system tools; it does not require sudo and installs no dependencies.

## Install

From this source checkout:

```fish
cd ~/Projects/NAnnersCreatorHub
python tools/manage_install.py install
```

The installer stages a versioned copy at `~/.local/share/nanners-creator-hub/releases/0.1.0`, activates it with the `current` symlink and manages `~/.local/bin/nanners-creator-hub` and the `NAnners Creator Hub` KDE menu entry. It refuses to replace an unrelated launcher or replace an installed release of the same version.

## Launch

Open **NAnners Creator Hub** from KDE or run:

```fish
~/.local/bin/nanners-creator-hub
```

## List versions and rollback

```fish
cd ~/Projects/NAnnersCreatorHub
python tools/manage_install.py list
python tools/manage_install.py rollback 0.1.0-dev8
```

Rollback requires the named version to be installed already. It only changes the active app version and preserves every retained version. Project schema compatibility must be verified when rolling back after future format changes.

To return to release version:

```fish
python tools/manage_install.py rollback 0.1.0
```

## Upgrade

Use a newer checkout whose source package version differs from every installed release, then run `python tools/manage_install.py install`. It retains older releases for rollback.

## Data safety

Projects are saved as standalone JSON manifests in paths explicitly chosen by the user; source recordings and `.kdenlive` projects are never edited by the application. Marker and Markdown exports refuse to overwrite existing files.

## Tests

```fish
env PYTHONPATH=src python -m unittest discover -s tests -v
```

Installer automated tests use isolated temporary HOME and XDG paths. The interactive KDE launcher test and Kdenlive marker import tests were completed on CachyOS during dev verification.
