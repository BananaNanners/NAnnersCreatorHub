"""Assisted-editing sections. This module does not read or modify media files."""
from __future__ import annotations

from difflib import SequenceMatcher
from pathlib import Path
from uuid import uuid4

STATUSES = ("draft", "needs_review", "confirmed")


def new_section(title: str) -> dict:
    title = title.strip()
    if not title:
        raise ValueError("Section title cannot be empty")
    return {
        "id": uuid4().hex,
        "title": title,
        "script": "",
        "narration_path": "",
        "footage_path": "",
        "footage_in_seconds": 0.0,
        "footage_out_seconds": 0.0,
        "status": "draft",
        "notes": "",
    }


def validate_section(section: dict) -> None:
    if not isinstance(section, dict):
        raise ValueError("Section must be an object")
    if not isinstance(section.get("id"), str) or not section["id"]:
        raise ValueError("Section ID is required")
    if not isinstance(section.get("title"), str) or not section["title"].strip():
        raise ValueError("Section title is required")
    if section.get("status") not in STATUSES:
        raise ValueError("Unsupported section status")
    for field in ("script", "notes", "narration_path", "footage_path"):
        if not isinstance(section.get(field), str):
            raise ValueError(f"Invalid section field: {field}")
    for field in ("footage_in_seconds", "footage_out_seconds"):
        val = section.get(field)
        if isinstance(val, bool) or not isinstance(val, (float, int)):
            raise ValueError(f"{field} must be a number")
        if not 0 <= val <= 86400:
            raise ValueError(f"{field} is outside the supported range")
    if section["footage_out_seconds"] and (
        section["footage_out_seconds"] <= section["footage_in_seconds"]
    ):
        raise ValueError("Footage out must be after footage in")


def footage_duration(section: dict) -> float | None:
    start = section.get("footage_in_seconds", 0)
    end = section.get("footage_out_seconds", 0)
    return round(end - start, 3) if end > start else None


def section_warnings(section: dict, media: list[dict]) -> list[str]:
    """Non-blocking suggestions; a time mismatch does not mean a failed edit."""
    messages = []
    library = {entry.get("path"): entry for entry in media}
    narration = section.get("narration_path", "")
    footage = section.get("footage_path", "")
    if not narration:
        messages.append("No narration assigned")
    if not footage:
        messages.append("No footage assigned")
    for label, path in (("Narration", narration), ("Footage", footage)):
        if path and path not in library:
            messages.append(f"{label} is not in the media library")
        elif path and library[path].get("status") != "ready":
            messages.append(f"{label} reference needs review")
    length = footage_duration(section)
    if footage and length is None:
        messages.append("Choose footage in/out points")
    if footage and length is not None:
        video = library.get(footage, {})
        total = video.get("duration_seconds")
        if total is not None and section["footage_out_seconds"] > total + 0.05:
            messages.append("Out point exceeds recording duration")
        audio = library.get(narration, {})
        speech = audio.get("duration_seconds")
        if speech is not None and abs(speech - length) > 1:
            messages.append(f"Footage/narration timing differs by {abs(speech - length):.1f}s")
    return messages


def suggest_footage(title: str, media: list[dict]) -> dict | None:
    """Filename-only heuristic. A suggestion always requires human review."""
    candidates = [
        entry for entry in media
        if entry.get("status") == "ready" and entry.get("kind", "").startswith("Video")
    ]
    if not candidates:
        return None
    title_words = set(title.lower().replace("-", " ").replace("_", " ").split())
    def score(entry: dict) -> tuple[float, float]:
        stem = Path(entry.get("name", "")).stem.lower()
        words = set(stem.replace("-", " ").replace("_", " ").split())
        overlap = len(title_words & words) / max(1, len(title_words))
        similarity = SequenceMatcher(None, title.lower(), stem).ratio()
        return overlap, similarity
    best = max(candidates, key=score)
    if score(best)[0] == 0 and score(best)[1] < 0.4:
        return None
    return best
