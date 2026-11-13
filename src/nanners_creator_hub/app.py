"""Single-window PySide6 application for milestone dev2."""
from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication, QFileDialog, QHBoxLayout, QLabel, QLineEdit,
    QMainWindow, QMessageBox, QPushButton, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget,
)

from . import __version__
from .media import MediaProbeError, inspect_media, inspect_reference
from .projects import load_project, new_project, save_project


def duration_display(seconds: float | None) -> str:
    if seconds is None:
        return "Unknown"
    minutes, secs = divmod(seconds, 60)
    hours, minutes = divmod(int(minutes), 60)
    if hours:
        return f"{hours:02}:{minutes:02}:{secs:06.3f}"
    return f"{minutes:02}:{secs:06.3f}"


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"NAnners Creator Hub — {__version__}")
        self.resize(1060, 650)
        self.project: dict | None = None
        self.project_path: Path | None = None
        container = QWidget(self)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)
        title = QLabel("NAnners Creator Hub")
        title.setStyleSheet("font-size: 27px; font-weight: 700;")
        layout.addWidget(title)
        layout.addWidget(QLabel(
            "Assisted Editing  •  Originals preserved  •  Section markers enabled"
        ))
        controls = QHBoxLayout()
        for caption, action in (
            ("New Project", self.create_project),
            ("Open Project", self.open_project),
            ("Save Project", self.save_current),
        ):
            button = QPushButton(caption)
            button.clicked.connect(action)
            controls.addWidget(button)
        controls.addStretch()
        layout.addLayout(controls)
        layout.addWidget(QLabel("Project name"))
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Create or open a project to get started")
        self.name_edit.textChanged.connect(self.update_name)
        layout.addWidget(self.name_edit)

        media_controls = QHBoxLayout()
        media_controls.addWidget(QLabel("Media library — referenced files (read-only)"))
        media_controls.addStretch()
        import_button = QPushButton("Import Media")
        import_button.clicked.connect(self.import_media)
        media_controls.addWidget(import_button)
        scan_button = QPushButton("Rescan Media")
        scan_button.clicked.connect(self.rescan_media)
        media_controls.addWidget(scan_button)
        layout.addLayout(media_controls)
        self.media_table = QTableWidget(0, 7)
        self.media_table.setHorizontalHeaderLabels(
            ["Filename", "Type", "Duration", "Resolution", "FPS", "Codecs", "Status"]
        )
        self.media_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.media_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.media_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.media_table, 1)
        self.status_label = QLabel("No project loaded. Original recordings are never modified.")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)
        self.setCentralWidget(container)

    def update_name(self, name: str) -> None:
        if self.project is not None:
            self.project["name"] = name

    def set_project(self, project: dict, path: Path | None) -> None:
        self.project = project
        self.project_path = path
        self.name_edit.setText(project["name"])
        self.refresh_media_table()

    def create_project(self) -> None:
        self.set_project(new_project("Untitled Tutorial"), None)
        self.status_label.setText("New unsaved project. Import media or choose Save Project.")

    def open_project(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(
            self, "Open Creator Hub Project", str(Path.home()), "Project JSON (*.json)"
        )
        if not filename:
            return
        try:
            loaded = load_project(Path(filename))
        except (ValueError, OSError) as exc:
            QMessageBox.warning(self, "Unable to open project", str(exc))
            return
        self.set_project(loaded, Path(filename))
        self.status_label.setText(f"Opened: {filename}")

    def save_current(self) -> None:
        if self.project is None:
            QMessageBox.information(self, "No project", "Create or open a project first.")
            return
        if self.project_path is None:
            filename, _ = QFileDialog.getSaveFileName(
                self, "Save Creator Hub Project",
                str(Path.home() / "Projects" / "NAnnersCreatorHub" / "tutorial.json"),
                "Project JSON (*.json)",
            )
            if not filename:
                return
            selected = Path(filename)
            if selected.suffix != ".json":
                selected = selected.with_suffix(".json")
            self.project_path = selected
        try:
            save_project(self.project_path, self.project)
        except (ValueError, OSError) as exc:
            QMessageBox.warning(self, "Save failed", str(exc))
            return
        self.status_label.setText(f"Saved: {self.project_path}")

    def import_media(self) -> None:
        if self.project is None:
            QMessageBox.information(self, "No project", "Create or open a project first.")
            return
        filenames, _ = QFileDialog.getOpenFileNames(
            self, "Import Referenced Media", str(Path.home()),
            "Media files (*.mp4 *.mkv *.mov *.webm *.avi *.wav *.mp3 *.flac *.ogg *.m4a);;All files (*)",
        )
        if not filenames:
            return
        refs = self.project.setdefault("media", [])
        known = {item["path"] for item in refs}
        added = 0
        issues = []
        for filename in filenames:
            path = str(Path(filename).expanduser().resolve())
            if path in known:
                continue
            try:
                entry = inspect_media(path)
            except (MediaProbeError, OSError) as exc:
                entry = {"path": path, "name": Path(path).name, "status": "error", "error": str(exc)}
                issues.append(Path(path).name)
            refs.append(entry)
            known.add(path)
            added += 1
        self.refresh_media_table()
        self.status_label.setText(
            f"Imported {added} reference(s); {len(issues)} need review. "
            "Save Project to keep changes. Source files unchanged."
        )

    def rescan_media(self) -> None:
        if self.project is None:
            QMessageBox.information(self, "No project", "Create or open a project first.")
            return
        previous = self.project.get("media", [])
        self.project["media"] = [inspect_reference(entry) for entry in previous]
        errors = sum(entry.get("status") != "ready" for entry in self.project["media"])
        self.refresh_media_table()
        self.status_label.setText(
            f"Rescanned {len(previous)} reference(s); {errors} need review. "
            "Save Project to keep changes."
        )

    def refresh_media_table(self) -> None:
        media = self.project.get("media", []) if self.project else []
        self.media_table.setRowCount(len(media))
        for row, entry in enumerate(media):
            resolution = (
                f"{entry['width']}×{entry['height']}"
                if entry.get("width") and entry.get("height") else "—"
            )
            codecs = "/".join(
                str(entry[key]) for key in ("video_codec", "audio_codec") if entry.get(key)
            ) or "—"
            values = [
                entry.get("name", Path(entry.get("path", "")).name),
                entry.get("kind", "Unknown"),
                duration_display(entry.get("duration_seconds")),
                resolution,
                str(entry["frame_rate"]) if entry.get("frame_rate") else "—",
                codecs,
                entry.get("status", "unknown"),
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                if col == 0:
                    item.setToolTip(entry.get("path", ""))
                if col == 6 and entry.get("error"):
                    item.setToolTip(entry["error"])
                self.media_table.setItem(row, col, item)
        self.media_table.resizeColumnsToContents()


def main() -> int:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
