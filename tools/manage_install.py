#!/usr/bin/env python3
"""User-local, reversible installation of NAnners Creator Hub.

Does not access, modify or copy source video, narration or project JSON files.
Designed for CachyOS/KDE with an existing system Python + PySide6 + FFprobe.
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

APP_ID = "org.nanners.CreatorHub"
OWNER_MARKER = "Managed by NAnners Creator Hub installer"
PROJECT_ROOT = Path(__file__).resolve().parent.parent


def app_paths():
    home = Path.home()
    data_home = Path(os.environ.get("XDG_DATA_HOME", str(home / ".local/share"))).expanduser()
    return {
        "app": data_home / "nanners-creator-hub",
        "releases": data_home / "nanners-creator-hub" / "releases",
        "current": data_home / "nanners-creator-hub" / "current",
        "launcher": home / ".local/bin/nanners-creator-hub",
        "desktop": data_home / "applications" / f"{APP_ID}.desktop",
    }


def source_version() -> str:
    text = (PROJECT_ROOT / "src/nanners_creator_hub/__init__.py").read_text()
    match = re.search(r'^__version__\s*=\s*"([^"]+)"$', text, re.MULTILINE)
    if not match:
        raise RuntimeError("Version could not be read from source package")
    return match.group(1)


def valid_version(version: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", version):
        raise ValueError("Unsafe release version")
    if version in (".", ".."):
        raise ValueError("Invalid release version")
    return version


def check_prerequisites() -> None:
    missing = [program for program in ("python3", "ffprobe") if not shutil.which(program)]
    if missing:
        raise RuntimeError(f"Missing required commands: {', '.join(missing)}")
    result = subprocess.run(
        [sys.executable, "-c", "import PySide6.QtWidgets"],
        capture_output=True, text=True, check=False,
    )
    if result.returncode:
        raise RuntimeError("PySide6 unavailable in current Python environment")


def managed_file(path: Path) -> bool:
    if not path.exists() and not path.is_symlink():
        return True
    if path.is_symlink() or not path.is_file():
        return False
    return OWNER_MARKER in path.read_text(encoding="utf-8", errors="replace")[:500]


def atomic_managed_write(path: Path, content: str, executable=False) -> None:
    if not managed_file(path):
        raise RuntimeError(f"Refusing to replace an unmanaged file: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_name = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent,
            prefix=".nanners-", delete=False
        ) as tmp:
            temp_name = Path(tmp.name)
            tmp.write(content)
            tmp.flush()
            os.fsync(tmp.fileno())
        temp_name.chmod(0o755 if executable else 0o644)
        os.replace(temp_name, path)
        temp_name = None
    finally:
        if temp_name is not None:
            temp_name.unlink(missing_ok=True)


def selected_release(paths: dict) -> str | None:
    current = paths["current"]
    if not current.is_symlink():
        if current.exists():
            raise RuntimeError(f"Refusing to use non-symlink current path: {current}")
        return None
    resolved = current.resolve(strict=False)
    parent = paths["releases"].resolve(strict=False)
    if resolved.parent != parent:
        raise RuntimeError("Current symlink points outside managed releases")
    return resolved.name


def activate(paths: dict, version: str) -> None:
    version = valid_version(version)
    target = paths["releases"] / version
    if target.is_symlink() or not target.is_dir() or not (target / "src/nanners_creator_hub/__main__.py").is_file():
        raise RuntimeError(f"Version is not installed: {version}")
    current = paths["current"]
    if current.exists() and not current.is_symlink():
        raise RuntimeError("Refusing to replace unmanaged current path")
    temp = paths["app"] / f".next-current-{os.getpid()}"
    if temp.exists() or temp.is_symlink():
        raise RuntimeError("Temporary release selector already exists")
    try:
        temp.symlink_to(target)
        os.replace(temp, current)
    finally:
        temp.unlink(missing_ok=True)


def install(args) -> None:
    paths = app_paths()
    version = valid_version(source_version())
    check_prerequisites()
    # Reject conflicting launchers before staging or selecting a version.
    for key in ("launcher", "desktop"):
        if not managed_file(paths[key]):
            raise RuntimeError(f"Unmanaged {key} already exists: {paths[key]}")
    # Verify any existing selector belongs to our managed version directory.
    selected_release(paths)
    target = paths["releases"] / version
    if target.exists() or target.is_symlink():
        raise RuntimeError(f"Version {version} already installed; use list or rollback")
    paths["releases"].mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".nanners-stage-", dir=paths["releases"]))
    try:
        (stage / "src").mkdir()
        shutil.copytree(PROJECT_ROOT / "src/nanners_creator_hub", stage / "src/nanners_creator_hub",
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        for filename in ("README.md", "pyproject.toml", "LICENSE"):
            if (PROJECT_ROOT / filename).is_file():
                shutil.copy2(PROJECT_ROOT / filename, stage / filename)
        os.replace(stage, target)
    finally:
        if stage.exists():
            shutil.rmtree(stage)

    # Keep launcher independent of source/repository path. Updating "current"
    # changes which retained release the launcher runs.
    launcher_content = (
        "#!/bin/sh\n"
        f"# {OWNER_MARKER}\n"
        'set -eu\n'
        f'export PYTHONPATH="{paths["current"] / "src"}"\n'
        'exec python3 -m nanners_creator_hub "$@"\n'
    )
    desktop_content = (
        "[Desktop Entry]\n"
        f"# {OWNER_MARKER}\n"
        "Type=Application\n"
        "Name=NAnners Creator Hub\n"
        "Comment=Local-first YouTube tutorial production assistant\n"
        f"Exec={paths['launcher']}\n"
        "Icon=applications-multimedia\n"
        "Terminal=false\n"
        "Categories=AudioVideo;Video;Utility;\n"
    )
    atomic_managed_write(paths["launcher"], launcher_content, executable=True)
    atomic_managed_write(paths["desktop"], desktop_content)
    activate(paths, version)
    print(f"Installed {version} in {target}")
    print(f"Launcher: {paths['launcher']}")
    print(f"Desktop shortcut: {paths['desktop']}")
    print("Existing project files and recordings were not accessed or modified.")


def list_releases(args) -> None:
    paths = app_paths()
    active = selected_release(paths)
    found = sorted(
        (p.name for p in paths["releases"].iterdir() if p.is_dir() and not p.name.startswith("."))
        if paths["releases"].is_dir() else []
    )
    if not found:
        print("No installed NAnners Creator Hub releases.")
        return
    for name in found:
        print(f"{'*' if name == active else ' '} {name}")
    print("* = active version")


def rollback(args) -> None:
    paths = app_paths()
    target = valid_version(args.version)
    previous = selected_release(paths)
    activate(paths, target)
    print(f"Active version: {target} (previously {previous or 'none'})")
    print("Installed versions and project files were not deleted.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    command = parser.add_subparsers(dest="command", required=True)
    command.add_parser("install", help="Install this source snapshot user-locally")
    command.add_parser("list", help="List retained installed versions")
    rollback_parser = command.add_parser("rollback", help="Activate an installed version")
    rollback_parser.add_argument("version")
    args = parser.parse_args()
    try:
        if args.command == "install":
            install(args)
        elif args.command == "list":
            list_releases(args)
        elif args.command == "rollback":
            rollback(args)
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
