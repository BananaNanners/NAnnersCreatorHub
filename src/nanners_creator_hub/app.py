"""Minimal single-window PySide6 application for milestone dev1."""
from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication, QFileDialog, QHBoxLayout, QLabel, QLineEdit,
    QMainWindow, QMessageBox, QPushButton, QVBoxLayout, QWidget,
)

from . import __version__
from .projects import load_project, new_project, save_project


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"NAnners Creator Hub — {__version__}")
        self.resize(900, 570)
        self.project: dict | None = None
        self.project_path: Path | None = None
        container = QWidget(self)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)
        title = QLabel("NAnners Creator Hub")
        title.setStyleSheet("font-size: 27px; font-weight: 700;")
        layout.addWidget(title)
        layout.addWidget(QLabel("0.1.0-dev1  •  Local-first tutorial workspace"))
        controls = QHBoxLayout()
        for caption, action in (
            ("New Project", self.create_project),
            ("Open Project", self.open_project),
            ("Save Project", self.save_current),
        ):
            button = QPushButton(caption)
            button.clicked.connect(action)
            controls.addWidget(button)
        layout.addLayout(controls)
        layout.addWidget(QLabel("Project name"))
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Create or open a project to get started")
        self.name_edit.textChanged.connect(self.update_name)
        layout.addWidget(self.name_edit)
        self.status_label = QLabel("No project loaded. Original recordings are never modified.")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)
        info = QLabel(
            "Editing mode: Assisted (active)\n"
            "Automatic Timeline: planned, not yet available\n"
            "Preserve originals: Always ON\n"
            "Section markers: ON\n"
            "Transition suggestions: OFF\n\n"
            "Next: media inspection, section management and Kdenlive exports."
        )
        info.setAlignment(Qt.AlignmentFlag.AlignTop)
        info.setStyleSheet("padding: 18px; background: palette(alternate-base);")
        layout.addWidget(info, 1)
        self.setCentralWidget(container)

    def update_name(self, name: str) -> None:
        if self.project is not None:
            self.project["name"] = name

    def create_project(self) -> None:
        default = new_project("Untitled Tutorial")
        self.project = default
        self.project_path = None
        self.name_edit.setText(default["name"])
        self.status_label.setText("New unsaved project. Choose Save Project to store it.")

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
        self.project = loaded
        self.project_path = Path(filename)
        self.name_edit.setText(loaded["name"])
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
            self.project_path = Path(filename)
        try:
            save_project(self.project_path, self.project)
        except (ValueError, OSError) as exc:
            QMessageBox.warning(self, "Save failed", str(exc))
            return
        self.status_label.setText(f"Saved: {self.project_path}")


def main() -> int:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
