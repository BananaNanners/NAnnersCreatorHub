"""Safe removal of imported media *references*, never the actual files."""
from __future__ import annotations

from copy import deepcopy

from .projects import validate_project


def remove_media_references(project: dict, paths: list[str]) -> tuple[dict, list[dict]]:
    """Return a validated project copy and list of affected section assignments.

    Clears stale section links and footage in/out points for removed references.
    Does not open, modify, unlink, or otherwise access any source media file.
    """
    validate_project(project)
    if not paths or len(set(paths)) != len(paths) or any(
        not isinstance(path, str) or not path for path in paths
    ):
        raise ValueError("Choose one or more unique imported media references.")

    selected = set(paths)
    known = {item["path"] for item in project["media"]}
    if not selected.issubset(known):
        raise ValueError("One or more selected references are no longer in the project.")

    updated = deepcopy(project)
    updated["media"] = [
        item for item in updated["media"] if item["path"] not in selected
    ]
    affected = []
    for section in updated["sections"]:
        changed_fields = []
        if section["narration_path"] in selected:
            section["narration_path"] = ""
            changed_fields.append("narration")
        if section["footage_path"] in selected:
            section["footage_path"] = ""
            section["footage_in_seconds"] = 0.0
            section["footage_out_seconds"] = 0.0
            changed_fields.append("footage (and its in/out points)")
        if changed_fields:
            if section["status"] == "confirmed":
                section["status"] = "needs_review"
            affected.append({
                "section_id": section["id"],
                "title": section["title"],
                "fields": tuple(changed_fields),
            })

    validate_project(updated)
    return updated, affected
