"""Deterministic editing-readiness analysis and portable Markdown reports.

Read-only: the analyzer never opens, modifies, or deletes referenced media.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from .sections import footage_duration, section_warnings

TIMING_TOLERANCE_SECONDS = 1.0


def analyze_section(section: dict, media: list[dict]) -> dict:
    library = {item["path"]: item for item in media}
    narration = library.get(section["narration_path"])
    footage = library.get(section["footage_path"])
    narration_duration = narration.get("duration_seconds") if narration else None
    selected_duration = footage_duration(section)
    difference = (
        round(selected_duration - narration_duration, 3)
        if selected_duration is not None and narration_duration is not None
        else None
    )
    issues = list(section_warnings(section, media))
    if not section["script"].strip():
        issues.append("Script text is missing")
    if not narration or narration.get("kind") not in ("Audio", "Video + Audio"):
        if section["narration_path"] and "No narration assigned" not in issues:
            issues.append("Assigned narration has no verified audio stream")
    if not footage or footage.get("kind") not in ("Video", "Video + Audio"):
        if section["footage_path"] and "No footage assigned" not in issues:
            issues.append("Assigned footage has no verified video stream")
    if section["status"] != "confirmed":
        issues.append("Section has not been manually confirmed")
    if narration_duration is None and section["narration_path"]:
        issues.append("Narration duration is unknown")
    if footage and footage.get("duration_seconds") is None:
        issues.append("Footage duration is unknown")
    # Explicit confirmation + absence of blockers define readiness; timing
    # warnings remain suggestions because longer visuals can be intentional.
    ready = not issues
    return {
        "id": section["id"],
        "title": section["title"],
        "review_status": section["status"],
        "narration_duration_seconds": narration_duration,
        "selected_footage_duration_seconds": selected_duration,
        "difference_seconds": difference,
        "issues": issues,
        "ready": ready,
    }


def analyze_project(project: dict) -> dict:
    media = project.get("media", [])
    results = [analyze_section(section, media) for section in project["sections"]]
    return {
        "project_name": project["name"],
        "section_count": len(results),
        "ready_count": sum(row["ready"] for row in results),
        "review_count": sum(not row["ready"] for row in results),
        "sections": results,
    }


def _time(value: float | None) -> str:
    return "Unknown" if value is None else f"{value:.3f}s"


def _safe_cell(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def report_markdown(project: dict) -> str:
    """Render a snapshot of editing readiness, not a Kdenlive timeline."""
    analysis = analyze_project(project)
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    lines = [
        "# NAnners Creator Hub — Editing Readiness",
        "",
        f"Project: {_safe_cell(analysis['project_name'])}",
        f"Generated: {now}",
        "Mode: Assisted Editing",
        "Source media: references only; originals are not modified",
        "",
        f"Sections: {analysis['section_count']} | Ready: {analysis['ready_count']} | "
        f"Needs review: {analysis['review_count']}",
        "",
        "| Section | Status | Narration | Footage range | Delta (footage − narration) |",
        "|---|---|---:|---:|---:|",
    ]
    for row in analysis["sections"]:
        diff = row["difference_seconds"]
        lines.append(
            f"| {_safe_cell(row['title'])} | {'Ready' if row['ready'] else 'Review'} "
            f"| {_time(row['narration_duration_seconds'])} "
            f"| {_time(row['selected_footage_duration_seconds'])} "
            f"| {'Unknown' if diff is None else f'{diff:+.3f}s'} |"
        )
    lines += ["", "## Section review"]
    if not analysis["sections"]:
        lines += ["", "No sections exist yet."]
    for index, row in enumerate(analysis["sections"], start=1):
        lines.extend([
            "",
            f"### {index:02}. {row['title']}",
            f"- Manual status: {row['review_status']}",
            f"- Readiness: {'Ready' if row['ready'] else 'Needs review'}",
        ])
        if row["issues"]:
            lines.extend(f"- [ ] {item}" for item in row["issues"])
        else:
            lines.append("- [x] No detected issues; manually confirmed")
    lines += [
        "",
        "## Interpretation",
        "",
        "Duration differences are advisory. A longer or shorter visual may be intentional.",
        "Readiness confirms metadata coverage and human review, not semantic footage matching.",
        "No automatic edits, transitions, marker exports, or Kdenlive project changes are performed.",
        "",
    ]
    return "\n".join(lines)


def export_report(path: Path, project: dict) -> None:
    """Write only to a *new* Markdown file; never overwrite projects or media."""
    from .projects import validate_project
    validate_project(project)
    path = Path(path)
    if path.suffix.lower() != ".md":
        raise ValueError("Reports must have a .md extension")
    # Exclusive creation rejects overwrites and races.
    with path.open("x", encoding="utf-8") as target:
        target.write(report_markdown(project))
