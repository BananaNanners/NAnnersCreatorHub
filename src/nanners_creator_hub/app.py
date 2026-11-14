"""Single-window assisted section editor — dev3."""
from __future__ import annotations

import copy
import sys
from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QApplication, QComboBox, QDoubleSpinBox, QFileDialog, QFormLayout,
    QHBoxLayout, QLabel, QLineEdit, QListWidget, QMainWindow,
    QMessageBox, QPushButton, QSplitter, QTableWidget, QTableWidgetItem,
    QTextEdit, QVBoxLayout, QWidget, QTabWidget,
)

from . import __version__
from .media import MediaProbeError, inspect_media, inspect_reference
from .media_library import remove_media_references
from .marker_dialog import MarkerExportDialog
from .kokoro_studio import KokoroStudio
from .batch_dialog import BatchNarrationDialog
from .batch import assign_completed_takes
from .footage_preview import FootagePreviewDialog
from .projects import load_project, new_project, save_project
from .readiness import analyze_project, export_report
from .sections import STATUSES, new_section, section_warnings, suggest_footage


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
        self.resize(1160, 780)
        self.project: dict | None = None
        self.project_path: Path | None = None
        self.dirty = False
        self.loading = False

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(8)
        title = QLabel("NAnners Creator Hub")
        title.setStyleSheet("font-size: 24px; font-weight: 700;")
        layout.addWidget(title)
        layout.addWidget(QLabel("Assisted Editing • Originals preserved • Section markers enabled"))
        controls = QHBoxLayout()
        for text, action in (
            ("New Project", self.create_project),
            ("Open Project", self.open_project),
            ("Save Project", self.save_current),
            ("Import Media", self.import_media),
            ("Rescan Media", self.rescan_media),
            ("Readiness Report", self.show_readiness_report),
            ("Export Report", self.export_readiness_report),
            ("Kdenlive Markers", self.export_kdenlive_markers),
        ):
            btn = QPushButton(text)
            btn.clicked.connect(action)
            controls.addWidget(btn)
        layout.addLayout(controls)
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Project name")
        self.name_edit.textEdited.connect(self.change_project_name)
        layout.addWidget(self.name_edit)
        self.media_table = QTableWidget(0, 7)
        self.media_table.setHorizontalHeaderLabels(
            ["Filename", "Type", "Duration", "Resolution", "FPS", "Codecs", "Status"]
        )
        self.media_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.media_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.media_table.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
        media_controls = QHBoxLayout()
        media_controls.addWidget(QLabel("Imported media references — source files are never deleted"))
        media_controls.addStretch()
        self.remove_media_button = QPushButton("Remove Selected Media…")
        self.remove_media_button.setObjectName("removeMediaReferencesButton")
        self.remove_media_button.setToolTip(
            "Remove selected references from this project only, not files on disk"
        )
        self.remove_media_button.setEnabled(False)
        self.remove_media_button.clicked.connect(self.remove_selected_media)
        media_controls.addWidget(self.remove_media_button)
        layout.addLayout(media_controls)
        layout.addWidget(self.media_table, 2)
        self.media_table.itemSelectionChanged.connect(self.update_remove_media_button)

        editing = QSplitter(Qt.Orientation.Horizontal)
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.addWidget(QLabel("Tutorial sections"))
        self.section_list = QListWidget()
        self.section_list.currentRowChanged.connect(self.show_section)
        left_layout.addWidget(self.section_list)
        left_buttons = QHBoxLayout()
        add = QPushButton("Add Section")
        add.clicked.connect(self.add_section)
        remove = QPushButton("Remove")
        remove.clicked.connect(self.remove_section)
        up = QPushButton("Move Up")
        up.clicked.connect(lambda: self.move_section(-1))
        down = QPushButton("Move Down")
        down.clicked.connect(lambda: self.move_section(1))
        for btn in (add, remove, up, down):
            left_buttons.addWidget(btn)
        left_layout.addLayout(left_buttons)
        batch_button = QPushButton("Batch Kokoro Narration…")
        batch_button.setObjectName("batchNarrationButton")
        batch_button.clicked.connect(self.open_batch_narration)
        left_layout.addWidget(batch_button)
        editing.addWidget(left)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        form = QFormLayout()
        self.section_title = QLineEdit()
        self.section_title.textEdited.connect(lambda val: self.edit_section("title", val))
        form.addRow("Section title", self.section_title)
        self.narration_combo = QComboBox()
        self.narration_combo.currentIndexChanged.connect(
            lambda _: self.edit_section("narration_path", self.narration_combo.currentData() or "")
        )
        narration_row = QHBoxLayout()
        narration_row.addWidget(self.narration_combo)
        play_narration = QPushButton("Open Audio")
        play_narration.clicked.connect(lambda: self.open_assigned_media("narration_path"))
        narration_row.addWidget(play_narration)
        form.addRow("Narration", narration_row)
        footage_row = QHBoxLayout()
        self.footage_combo = QComboBox()
        self.footage_combo.currentIndexChanged.connect(
            lambda _: self.edit_section("footage_path", self.footage_combo.currentData() or "")
        )
        footage_row.addWidget(self.footage_combo)
        open_footage = QPushButton("Open Footage")
        open_footage.clicked.connect(lambda: self.open_assigned_media("footage_path"))
        footage_row.addWidget(open_footage)
        preview_footage = QPushButton("Preview / Set Range…")
        preview_footage.setObjectName("previewFootageButton")
        preview_footage.clicked.connect(self.preview_footage_range)
        footage_row.addWidget(preview_footage)
        suggest = QPushButton("Suggest")
        suggest.clicked.connect(self.suggest_match)
        footage_row.addWidget(suggest)
        form.addRow("Footage", footage_row)
        self.in_point = QDoubleSpinBox()
        self.out_point = QDoubleSpinBox()
        for field, widget in (("footage_in_seconds", self.in_point), ("footage_out_seconds", self.out_point)):
            widget.setRange(0, 86400)
            widget.setDecimals(3)
            widget.setSuffix(" s")
            widget.valueChanged.connect(lambda val, f=field: self.edit_section(f, val))
        form.addRow("In point", self.in_point)
        form.addRow("Out point", self.out_point)
        self.state_combo = QComboBox()
        for status in STATUSES:
            self.state_combo.addItem(status.replace("_", " ").title(), status)
        self.state_combo.currentIndexChanged.connect(
            lambda _: self.edit_section("status", self.state_combo.currentData())
        )
        form.addRow("Review status", self.state_combo)
        right_layout.addLayout(form)
        right_layout.addWidget(QLabel("Script"))
        self.script_edit = QTextEdit()
        self.script_edit.setPlaceholderText("Paste narration script for this section")
        self.script_edit.textChanged.connect(
            lambda: self.edit_section("script", self.script_edit.toPlainText())
        )
        right_layout.addWidget(self.script_edit, 2)
        right_layout.addWidget(QLabel("Review notes"))
        self.notes_edit = QTextEdit()
        self.notes_edit.setMaximumHeight(85)
        self.notes_edit.textChanged.connect(
            lambda: self.edit_section("notes", self.notes_edit.toPlainText())
        )
        right_layout.addWidget(self.notes_edit)
        self.warnings = QLabel("Select a section")
        self.warnings.setWordWrap(True)
        right_layout.addWidget(self.warnings)
        editing.addWidget(right)
        editing.setStretchFactor(0, 2)
        editing.setStretchFactor(1, 3)
        layout.addWidget(editing, 5)
        self.status_label = QLabel("Create or open a project to begin.")
        self.status_label.setWordWrap(True)
        self.save_state_label = QLabel()
        self.save_state_label.setObjectName("projectSaveState")
        self.save_state_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.save_state_label.setMinimumWidth(280)
        status_row = QHBoxLayout()
        status_row.addWidget(self.status_label, 1)
        status_row.addWidget(self.save_state_label)
        layout.addLayout(status_row)
        self.tabs = QTabWidget()
        self.tabs.addTab(container, "Assisted Editing")
        self.kokoro_studio = KokoroStudio(self)
        self.tabs.addTab(self.kokoro_studio, "Kokoro Narration Studio")
        self.setCentralWidget(self.tabs)
        self.show_section(-1)
        self.update_save_state()

    def open_batch_narration(self) -> None:
        if self.project is None:
            QMessageBox.information(self, "No project", "Create or open a project first.")
            return
        if self.kokoro_studio.is_generating:
            QMessageBox.information(
                self, "Kokoro busy",
                "Finish or cancel the single-take generation before starting a batch."
            )
            return
        try:
            dialog = BatchNarrationDialog(self.project, self.kokoro_studio, self)
        except (ValueError, OSError) as exc:
            QMessageBox.warning(self, "Batch unavailable", str(exc))
            return
        if dialog.exec() != BatchNarrationDialog.DialogCode.Accepted:
            if dialog.completed:
                self.status_label.setText(
                    f"Kept {len(dialog.completed)} new WAV take(s) without assigning them."
                )
            return
        try:
            updated = assign_completed_takes(
                self.project, dialog.completed, dialog.selected_assignments,
                allow_replace=dialog.replacement_approved,
            )
        except (OSError, ValueError, MediaProbeError) as exc:
            QMessageBox.warning(
                self, "Assignment not applied",
                f"All new WAVs remain on disk. Project unchanged.\n\n{exc}",
            )
            return
        row = self.section_list.currentRow()
        self.project = updated
        self.refresh_media_table()
        self.refresh_section_list(row)
        self.mark_dirty()
        self.status_label.setText(
            f"UNSAVED CHANGES — Assigned {len(dialog.selected_assignments)} new "
            "narration reference(s). Review them and click Save Project. "
            "Existing audio files were preserved."
        )

    def show_readiness_report(self) -> None:
        if self.project is None:
            QMessageBox.information(self, "No project", "Create or open a project first.")
            return
        analysis = analyze_project(self.project)
        rows = [
            f"{i:02}. {item['title']}: "
            f"{'Ready' if item['ready'] else 'Needs review'} "
            f"({len(item['issues'])} issue(s))"
            for i, item in enumerate(analysis["sections"], 1)
        ]
        summary = (
            f"{analysis['section_count']} sections, "
            f"{analysis['ready_count']} ready, "
            f"{analysis['review_count']} needing review.\n\n"
            + ("\n".join(rows) if rows else "No sections added yet.")
            + "\n\nExport a Markdown report for detailed timing and review notes."
        )
        QMessageBox.information(self, "Editing Readiness", summary)

    def export_readiness_report(self) -> None:
        if self.project is None:
            QMessageBox.information(self, "No project", "Create or open a project first.")
            return
        default_dir = self.project_path.parent if self.project_path else Path.home()
        filename, _ = QFileDialog.getSaveFileName(
            self, "Export Editing Readiness",
            str(default_dir / "editing-readiness.md"), "Markdown report (*.md)"
        )
        if not filename:
            return
        target = Path(filename)
        if target.suffix.lower() != ".md":
            target = target.with_suffix(".md")
        if target.exists():
            QMessageBox.warning(self, "Report exists", "Select a new report filename. Existing files are never overwritten.")
            return
        try:
            export_report(target, self.project)
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, "Export failed", str(exc))
            return
        self.status_label.setText(f"Report exported: {target}")

    def export_kdenlive_markers(self) -> None:
        if self.project is None:
            QMessageBox.information(self, "No project", "Create or open a project first.")
            return
        default_dir = self.project_path.parent if self.project_path else Path.home()
        dialog = MarkerExportDialog(self.project, default_dir, self)
        if dialog.exec() and dialog.export_path is not None:
            self.status_label.setText(f"New marker JSON exported: {dialog.export_path}")

    def update_save_state(self) -> None:
        """Persistent save state, independent of transient operation messages."""
        base_title = f"NAnners Creator Hub — {__version__}"
        if self.project is None:
            label, color = "NO PROJECT OPEN", "#aab3bf"
        elif self.dirty:
            label, color = "UNSAVED CHANGES — Save Project", "#ffcc66"
        elif self.project_path is None:
            label, color = "NOT SAVED — Save Project", "#ffcc66"
        else:
            label, color = "SAVED", "#90d9aa"
        self.save_state_label.setText(label)
        self.save_state_label.setToolTip(
            "Project changes are only written to the JSON file when you click Save Project."
            if self.project is not None and (self.dirty or self.project_path is None)
            else "The project is saved on disk." if self.project is not None
            else "Open an existing tutorial or create a new one."
        )
        self.save_state_label.setStyleSheet(
            f"font-weight: 700; color: {color};"
        )
        self.setWindowTitle(base_title + (" — UNSAVED" if self.dirty else ""))

    def mark_dirty(self) -> None:
        self.dirty = True
        self.update_save_state()

    def mark_clean(self) -> None:
        self.dirty = False
        self.update_save_state()

    def check_discard(self) -> bool:
        if not self.dirty:
            return True
        choice = QMessageBox.question(
            self, "Unsaved changes",
            "This project has unsaved changes. Discard them?",
            QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        return choice == QMessageBox.StandardButton.Discard

    def closeEvent(self, event) -> None:
        if not self.check_discard():
            event.ignore()
            return
        if self.kokoro_studio.is_generating:
            choice = QMessageBox.question(
                self, "Narration generation in progress",
                "Cancel this Kokoro generation and close the hub? "
                "Existing WAV files will be preserved.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if choice != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
            self.kokoro_studio.stop_for_shutdown()
        event.accept()

    def change_project_name(self, value: str) -> None:
        if self.project is not None:
            self.project["name"] = value
            self.mark_dirty()

    def selected_section(self) -> dict | None:
        row = self.section_list.currentRow()
        sections = self.project.get("sections", []) if self.project else []
        return sections[row] if 0 <= row < len(sections) else None

    def set_project(self, project: dict, path: Path | None) -> None:
        self.project = project
        self.project_path = path
        self.name_edit.setText(project["name"])
        self.refresh_media_table()
        self.refresh_section_list()
        self.mark_clean()

    def create_project(self) -> None:
        if self.check_discard():
            self.set_project(new_project("Untitled Tutorial"), None)
            self.mark_dirty()
            self.status_label.setText("New project. Save before closing.")

    def open_project(self) -> None:
        if not self.check_discard():
            return
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
        proposed = self.project_path
        if proposed is None:
            filename, _ = QFileDialog.getSaveFileName(
                self, "Save Creator Hub Project",
                str(Path.home() / "Projects" / "NAnnersCreatorHub" / "tutorial.json"),
                "Project JSON (*.json)",
            )
            if not filename:
                return
            proposed = Path(filename)
            if proposed.suffix != ".json":
                proposed = proposed.with_suffix(".json")
        try:
            save_project(proposed, self.project)
        except (ValueError, OSError) as exc:
            QMessageBox.warning(self, "Save failed", str(exc))
            return
        self.project_path = proposed
        self.mark_clean()
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
        issues = 0
        for filename in filenames:
            path = str(Path(filename).expanduser().resolve())
            if path in known:
                continue
            try:
                entry = inspect_media(path)
            except (MediaProbeError, OSError) as exc:
                entry = {"path": path, "name": Path(path).name, "status": "error", "error": str(exc)}
                issues += 1
            refs.append(entry)
            known.add(path)
            added += 1
        if added:
            self.mark_dirty()
        self.refresh_media_table()
        self.refresh_section_list(self.section_list.currentRow())
        self.status_label.setText(
            f"Imported {added} reference(s), {issues} need review. Source files unchanged."
        )

    def update_remove_media_button(self) -> None:
        self.remove_media_button.setEnabled(
            self.project is not None
            and bool(self.media_table.selectionModel().selectedRows())
        )

    def remove_selected_media(self) -> None:
        if self.project is None:
            return
        selected_rows = sorted(
            index.row() for index in self.media_table.selectionModel().selectedRows()
        )
        if not selected_rows:
            QMessageBox.information(
                self, "No media selected",
                "Select one or more rows in the imported media table first."
            )
            return
        media = self.project["media"]
        selected_paths = [media[row]["path"] for row in selected_rows]
        try:
            updated, affected = remove_media_references(self.project, selected_paths)
        except ValueError as exc:
            QMessageBox.warning(self, "Cannot remove media reference", str(exc))
            return

        filenames = "\n".join(
            f"• {Path(path).name}" for path in selected_paths[:8]
        )
        if len(selected_paths) > 8:
            filenames += f"\n… and {len(selected_paths) - 8} more"
        affected_description = (
            "\n\nAssignments that will be cleared:\n"
            + "\n".join(
                f"• {item['title']}: {', '.join(item['fields'])}"
                for item in affected[:8]
            )
            + (f"\n… and {len(affected) - 8} more sections" if len(affected) > 8 else "")
            if affected else "\n\nNo section assignments use these references."
        )
        answer = QMessageBox.question(
            self, "Remove imported media references?",
            f"Remove {len(selected_paths)} reference(s) from THIS project?\n\n"
            + filenames + affected_description
            + "\n\nThe actual video and audio files WILL NOT be deleted. "
              "Project changes remain unsaved until you click Save Project.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        selected_section_row = self.section_list.currentRow()
        self.project = updated
        self.refresh_media_table()
        self.refresh_section_list(selected_section_row)
        self.mark_dirty()
        self.status_label.setText(
            f"Removed {len(selected_paths)} media reference(s) from this project; "
            f"cleared assignments in {len(affected)} section(s). "
            "Original files untouched. Save Project to keep this change."
        )

    def rescan_media(self) -> None:
        if self.project is None:
            return
        refs = self.project.get("media", [])
        if not refs:
            return
        self.project["media"] = [inspect_reference(entry) for entry in refs]
        self.mark_dirty()
        self.refresh_media_table()
        self.refresh_section_list(self.section_list.currentRow())
        errors = sum(item["status"] != "ready" for item in self.project["media"])
        self.status_label.setText(f"Rescanned {len(refs)} references; {errors} need review.")

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
        self.update_remove_media_button()

    def refresh_section_list(self, selected: int = 0) -> None:
        self.loading = True
        self.section_list.clear()
        if self.project:
            for idx, section in enumerate(self.project["sections"], start=1):
                self.section_list.addItem(f"{idx:02}  {section['title']}  [{section['status']}]")
        count = self.section_list.count()
        self.loading = False
        self.section_list.setCurrentRow(min(max(selected, 0), count - 1) if count else -1)
        self.show_section(self.section_list.currentRow())

    def show_section(self, row: int) -> None:
        if self.loading:
            return
        self.loading = True
        section = self.selected_section()
        fields = (
            self.section_title, self.narration_combo, self.footage_combo,
            self.in_point, self.out_point, self.state_combo,
            self.script_edit, self.notes_edit,
        )
        for field in fields:
            field.setEnabled(section is not None)
        self.narration_combo.clear()
        self.footage_combo.clear()
        self.narration_combo.addItem("— Not assigned —", "")
        self.footage_combo.addItem("— Not assigned —", "")
        for entry in self.project.get("media", []) if self.project else []:
            path = entry["path"]
            if entry.get("kind") in ("Audio", "Video + Audio"):
                self.narration_combo.addItem(entry.get("name", Path(path).name), path)
            if entry.get("kind") in ("Video", "Video + Audio"):
                self.footage_combo.addItem(entry.get("name", Path(path).name), path)
        if section is None:
            self.section_title.clear()
            self.script_edit.clear()
            self.notes_edit.clear()
            self.in_point.setValue(0)
            self.out_point.setValue(0)
            self.state_combo.setCurrentIndex(0)
            self.warnings.setText("Add or select a section.")
        else:
            self.section_title.setText(section["title"])
            self.script_edit.setPlainText(section["script"])
            self.notes_edit.setPlainText(section["notes"])
            for combo, key in (
                (self.narration_combo, "narration_path"),
                (self.footage_combo, "footage_path"),
            ):
                path = section[key]
                idx = combo.findData(path)
                if path and idx == -1:
                    combo.addItem(f"Missing library reference: {Path(path).name}", path)
                    idx = combo.findData(path)
                combo.setCurrentIndex(max(idx, 0))
            self.in_point.setValue(section["footage_in_seconds"])
            self.out_point.setValue(section["footage_out_seconds"])
            self.state_combo.setCurrentIndex(self.state_combo.findData(section["status"]))
            self.refresh_warnings()
        self.loading = False

    def refresh_warnings(self) -> None:
        section = self.selected_section()
        if section is None:
            self.warnings.setText("Add or select a section.")
            return
        messages = section_warnings(section, self.project.get("media", []))
        self.warnings.setText("Review: " + ("; ".join(messages) if messages else "No automatic timing warnings"))

    def edit_section(self, key: str, value) -> None:
        if self.loading:
            return
        section = self.selected_section()
        if section is None or section.get(key) == value:
            return
        section[key] = value
        self.mark_dirty()
        if key in ("title", "status"):
            row = self.section_list.currentRow()
            self.section_list.item(row).setText(
                f"{row+1:02}  {section['title']}  [{section['status']}]"
            )
        if key in ("narration_path", "footage_path", "footage_in_seconds", "footage_out_seconds"):
            self.refresh_warnings()

    def add_section(self) -> None:
        if self.project is None:
            QMessageBox.information(self, "No project", "Create or open a project first.")
            return
        self.project["sections"].append(new_section(f"Section {len(self.project['sections']) + 1:02}"))
        self.mark_dirty()
        self.refresh_section_list(len(self.project["sections"]) - 1)

    def remove_section(self) -> None:
        section = self.selected_section()
        if section is None:
            return
        choice = QMessageBox.question(
            self, "Remove section",
            f"Remove '{section['title']}' from the project? Source media will not be deleted.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if choice != QMessageBox.StandardButton.Yes:
            return
        row = self.section_list.currentRow()
        del self.project["sections"][row]
        self.mark_dirty()
        self.refresh_section_list(max(row - 1, 0))

    def move_section(self, direction: int) -> None:
        row = self.section_list.currentRow()
        if self.project is None or row < 0:
            return
        new_row = row + direction
        if not 0 <= new_row < len(self.project["sections"]):
            return
        sections = self.project["sections"]
        sections[row], sections[new_row] = sections[new_row], sections[row]
        self.mark_dirty()
        self.refresh_section_list(new_row)

    def preview_footage_range(self) -> None:
        section = self.selected_section()
        if section is None or self.project is None:
            QMessageBox.information(self, "No section", "Select a tutorial section first.")
            return
        source = section.get("footage_path", "")
        if not source:
            QMessageBox.information(
                self, "No footage assigned",
                "Choose an imported video recording in the Footage selector first.",
            )
            return
        media = next(
            (item for item in self.project["media"] if item["path"] == source), None
        )
        if media is None or not media.get("kind", "").startswith("Video"):
            QMessageBox.warning(
                self, "Footage unavailable", "Assign a valid video reference before previewing."
            )
            return
        try:
            dialog = FootagePreviewDialog(
                Path(source), media.get("duration_seconds"),
                section["footage_in_seconds"], section["footage_out_seconds"], self,
            )
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, "Cannot preview footage", str(exc))
            return
        selected_id = section["id"]
        if dialog.exec() != FootagePreviewDialog.DialogCode.Accepted:
            return
        if dialog.applied_range is None:
            return
        current = self.selected_section()
        if (current is None or current["id"] != selected_id
                or current["footage_path"] != source):
            QMessageBox.warning(
                self, "Selection changed",
                "The selected footage changed while previewing. No range was applied.",
            )
            return
        start, end = dialog.applied_range
        if (current["footage_in_seconds"], current["footage_out_seconds"]) == (start, end):
            self.status_label.setText("The previewed source range is already assigned.")
            return
        current["footage_in_seconds"] = start
        current["footage_out_seconds"] = end
        self.show_section(self.section_list.currentRow())
        self.mark_dirty()
        self.status_label.setText(
            f"UNSAVED CHANGES — Applied source range {start:.3f}–{end:.3f} s "
            f"to {current['title']}. Source recording untouched. Save Project to keep it."
        )

    def open_assigned_media(self, key: str) -> None:
        section = self.selected_section()
        path = section.get(key, "") if section else ""
        if not path or not Path(path).is_file():
            QMessageBox.information(self, "Media unavailable", "Assign an available media file first.")
            return
        if not QDesktopServices.openUrl(QUrl.fromLocalFile(path)):
            QMessageBox.warning(self, "Open failed", "No desktop media player accepted this file.")

    def suggest_match(self) -> None:
        section = self.selected_section()
        if section is None:
            return
        proposal = suggest_footage(section["title"], self.project.get("media", []))
        if proposal is None:
            QMessageBox.information(self, "No match", "No filename-based footage match found. Select footage manually.")
            return
        answer = QMessageBox.question(
            self, "Review footage suggestion",
            f"Suggested from filename only:\n{proposal['name']}\n\n"
            "Use this recording for this section? This does not verify visual content.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer == QMessageBox.StandardButton.Yes:
            self.footage_combo.setCurrentIndex(self.footage_combo.findData(proposal["path"]))
            self.state_combo.setCurrentIndex(self.state_combo.findData("needs_review"))


def main() -> int:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
