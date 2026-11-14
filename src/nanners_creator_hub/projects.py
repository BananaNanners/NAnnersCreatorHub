"""Versioned, non-destructive project manifests with atomic saves."""
from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from .sections import validate_section

SCHEMA_VERSION = 1


def new_project(name: str) -> dict:
    name = name.strip()
    if not name:
        raise ValueError("Project name must not be empty")
    return {
        "schema_version": SCHEMA_VERSION,
        "name": name,
        "editing_mode": "assisted",
        "preserve_originals": True,
        "section_markers": True,
        "transition_suggestions": False,
        "sections": [],
        "media": [],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def validate_project(data: dict) -> None:
    if not isinstance(data, dict):
        raise ValueError("Project must be a JSON object")
    if data.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("Unsupported project schema version")
    if not isinstance(data.get("name"), str) or not data["name"].strip():
        raise ValueError("Project name is missing")
    if data.get("editing_mode") != "assisted":
        raise ValueError("Only the assisted-editing project schema is supported")
    if data.get("preserve_originals") is not True:
        raise ValueError("Original-media preservation must remain enabled")
    if not isinstance(data.get("sections"), list):
        raise ValueError("Sections must be a list")
    ids = set()
    for section in data["sections"]:
        validate_section(section)
        if section["id"] in ids:
            raise ValueError("Duplicate section IDs")
        ids.add(section["id"])
    media = data.get("media", [])
    if not isinstance(media, list):
        raise ValueError("Media must be a list")
    for item in media:
        if not isinstance(item, dict) or not isinstance(item.get("path"), str) or not item["path"]:
            raise ValueError("Every media reference must contain a file path")


def save_project(path: Path, data: dict) -> None:
    """Atomically replace a manifest; never write to referenced media."""
    validate_project(data)
    path = Path(path)
    if path.suffix != ".json":
        raise ValueError("Project file must have a .json extension")
    if not path.parent.is_dir():
        raise FileNotFoundError("Destination folder does not exist")
    payload = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent,
            prefix=f".{path.stem}.", suffix=".tmp", delete=False
        ) as handle:
            temporary = Path(handle.name)
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def load_project(path: Path) -> dict:
    with Path(path).open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    validate_project(data)
    return data
