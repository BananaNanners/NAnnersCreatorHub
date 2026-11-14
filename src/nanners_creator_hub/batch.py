"""Plan and apply Kokoro batch narration without modifying a live project.

Immutable snapshots guard against unintended re-assignment. Producing WAVs
is separate from (user-approved) changes to the in-memory project.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass
from pathlib import Path

from .media import inspect_media
from .projects import validate_project


@dataclass(frozen=True)
class SectionTake:
    section_id: str
    section_number: int
    title: str
    script: str
    previous_narration: str


@dataclass(frozen=True)
class CompletedTake:
    section: SectionTake
    wav_path: Path


def select_sections(project: dict, ids: list[str]) -> list[SectionTake]:
    validate_project(project)
    if not ids or len(ids) != len(set(ids)):
        raise ValueError("Choose unique tutorial sections for batch narration.")
    selected = set(ids)
    result = []
    for number, section in enumerate(project["sections"], 1):
        if section["id"] not in selected:
            continue
        if not section["script"].strip():
            raise ValueError(f"Section {number} ({section['title']}) has no script.")
        result.append(SectionTake(section["id"], number, section["title"],
                                  section["script"], section["narration_path"]))
    if len(result) != len(ids):
        raise ValueError("One or more selected sections are no longer in the project.")
    return result


def assign_completed_takes(project: dict, completed: list[CompletedTake],
                           selected_ids: list[str],
                           *, allow_replace: bool = False) -> dict:
    """Return a validated updated copy; never mutate project or write the JSON.

    Caller has to obtain explicit approval before passing replacement=True.
    Files are always scanned before any in-memory changes are committed.
    """
    validate_project(project)
    selected = set(selected_ids)
    if not selected or len(selected) != len(selected_ids):
        raise ValueError("Select at least one unique completed take to assign.")
    mapping = {item.section.section_id: item for item in completed}
    if len(mapping) != len(completed) or not selected.issubset(mapping):
        raise ValueError("Selected take is unavailable or duplicated.")
    sections = {section["id"]: section for section in project["sections"]}
    checks = []
    for section_id in selected_ids:
        if section_id not in sections:
            raise ValueError("A selected section no longer exists.")
        existing = sections[section_id]
        result = mapping[section_id]
        snapshot = result.section
        if (existing["script"] != snapshot.script or
                existing["narration_path"] != snapshot.previous_narration):
            raise ValueError(f"Section '{snapshot.title}' changed during generation; review again.")
        if existing["narration_path"] and not allow_replace:
            raise ValueError(f"Section '{snapshot.title}' has an existing narration. "
                             "Explicit replacement confirmation required.")
        path = Path(result.wav_path).expanduser().resolve()
        if not path.is_file():
            raise ValueError(f"New narration file is missing: {path.name}")
        meta = inspect_media(path)
        if meta["kind"] != "Audio" or meta["status"] != "ready":
            raise ValueError(f"Invalid audio take: {path.name}")
        checks.append((section_id, meta))

    updated = copy.deepcopy(project)
    updated_sections = {s["id"]: s for s in updated["sections"]}
    known = {m["path"] for m in updated["media"]}
    for section_id, meta in checks:
        if meta["path"] not in known:
            updated["media"].append(meta)
            known.add(meta["path"])
        updated_sections[section_id]["narration_path"] = meta["path"]
        # An assignment is not equivalent to a human review.
        updated_sections[section_id]["status"] = "needs_review"
    validate_project(updated)
    return updated
