"""Review-first batch Kokoro narration for tutorial sections."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QProcess, Qt, QTimer
from PySide6.QtWidgets import (
    QAbstractItemView, QDialog, QHBoxLayout, QLabel, QMessageBox, QPushButton,
    QTableWidget, QTableWidgetItem, QVBoxLayout,
)

from .batch import CompletedTake, SectionTake, select_sections, assign_completed_takes
from .media import MediaProbeError
from .kokoro import inspect_kokoro
from .narration import cleanup_job, kokoro_arguments, prepare_job, publish_take, safe_stem
from .pronunciations import parse_rules, speech_text


class BatchNarrationDialog(QDialog):
    def __init__(self, project: dict, studio, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Batch Kokoro Narration — review before assignment")
        self.resize(860, 570)
        self.project = project
        self.studio = studio
        self.output_dir = Path(studio.output_dir.text()).expanduser()
        self.prefs = studio.current_prefs()
        self.rules = parse_rules(studio.rules_editor.toPlainText())
        self.backend = inspect_kokoro(self.prefs)
        self.sections = list(project.get("sections", []))
        self.pending: list[SectionTake] = []
        self.completed: list[CompletedTake] = []
        self.failed: list[tuple[SectionTake, str]] = []
        self.current: SectionTake | None = None
        self.job = None
        self.process: QProcess | None = None
        self.running = False
        self.stop_requested = False
        self.selected_assignments: list[str] = []
        self.replacement_approved = False

        layout = QVBoxLayout(self)
        heading = QLabel(
            f"Choose sections to narrate using {self.prefs['voice']} "
            f"({self.prefs['language']}, {self.prefs['speed']:.2f}×). "
            "Each take creates one new WAV and one TXT; existing files are preserved."
        )
        heading.setWordWrap(True)
        layout.addWidget(heading)
        subtitle = QLabel(
            "Sections with existing narration start UNCHECKED. "
            "Generated takes are only linked to your project after explicit review and approval."
        )
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)
        self.table = QTableWidget(len(self.sections), 5)
        self.table.setObjectName("batchSectionsTable")
        self.table.setHorizontalHeaderLabels(
            ["Generate", "Section", "Current narration", "Result", "Assign new WAV"]
        )
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setColumnWidth(0, 100)
        self.table.setColumnWidth(1, 200)
        self.table.setColumnWidth(2, 180)
        self.table.setColumnWidth(3, 200)
        for i, section in enumerate(self.sections):
            eligible = bool(section["script"].strip())
            old = section["narration_path"]
            selection = QTableWidgetItem()
            selection.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable)
            if not eligible:
                selection.setFlags(Qt.ItemFlag.NoItemFlags)
            selection.setCheckState(
                Qt.CheckState.Checked if eligible and not old else Qt.CheckState.Unchecked
            )
            self.table.setItem(i, 0, selection)
            self.table.setItem(i, 1, QTableWidgetItem(f"{i+1:02} — {section['title']}"))
            self.table.setItem(i, 2, QTableWidgetItem(
                Path(old).name if old else "Not assigned"
            ))
            self.table.setItem(i, 3, QTableWidgetItem(
                "Ready" if eligible else "No script — unavailable"
            ))
            self.table.setItem(i, 4, QTableWidgetItem("Not generated"))
        layout.addWidget(self.table, 1)

        self.info = QLabel(
            f"New take output folder: {self.output_dir}\n"
            "Choose sections, then click Start Batch."
        )
        self.info.setWordWrap(True)
        layout.addWidget(self.info)

        controls = QHBoxLayout()
        self.start_button = QPushButton("Start Batch")
        self.start_button.setObjectName("batchStartButton")
        self.start_button.clicked.connect(self.start_batch)
        controls.addWidget(self.start_button)
        self.cancel_button = QPushButton("Cancel Remaining")
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self.cancel_remaining)
        controls.addWidget(self.cancel_button)
        self.apply_button = QPushButton("Assign Checked WAVs to Project")
        self.apply_button.setObjectName("batchApplyButton")
        self.apply_button.setEnabled(False)
        self.apply_button.clicked.connect(self.review_and_accept)
        controls.addWidget(self.apply_button)
        self.keep_button = QPushButton("Keep WAVs Only / Close")
        self.keep_button.clicked.connect(self.reject)
        controls.addWidget(self.keep_button)
        layout.addLayout(controls)
        self.table.itemChanged.connect(self.refresh_actions)
        self.refresh_actions()

    def selected_for_generation(self) -> list[str]:
        return [
            section["id"]
            for i, section in enumerate(self.sections)
            if self.table.item(i, 0).checkState() == Qt.CheckState.Checked
            and section["script"].strip()
        ]

    def refresh_actions(self):
        if self.running:
            return
        self.start_button.setEnabled(bool(self.selected_for_generation()) and not self.completed)
        self.apply_button.setEnabled(
            bool(self.completed) and bool(self.selected_for_assignment())
        )

    def selected_for_assignment(self) -> list[str]:
        completed_ids = {item.section.section_id for item in self.completed}
        return [
            section["id"] for i, section in enumerate(self.sections)
            if section["id"] in completed_ids
            and self.table.item(i, 4).checkState() == Qt.CheckState.Checked
        ]

    def start_batch(self):
        if self.running or self.completed:
            return
        try:
            ids = self.selected_for_generation()
            self.pending = select_sections(self.project, ids)
            self.rules = parse_rules(self.studio.rules_editor.toPlainText())
            self.prefs = self.studio.current_prefs()
            self.backend = inspect_kokoro(self.prefs)
            if not self.backend.ready:
                raise ValueError("; ".join(self.backend.problems))
            if not self.output_dir.is_dir() and self.output_dir.exists():
                raise ValueError("WAV output path is not a folder")
            if len(self.pending) > 100:
                raise ValueError("Generate at most 100 sections per batch")
        except (ValueError, OSError) as exc:
            QMessageBox.warning(self, "Batch not ready", str(exc))
            return
        self.running = True
        self.stop_requested = False
        self.start_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.apply_button.setEnabled(False)
        self.keep_button.setEnabled(False)
        for i in range(self.table.rowCount()):
            self.table.item(i, 0).setFlags(Qt.ItemFlag.NoItemFlags)
        self._launch_next()

    def _launch_next(self):
        if not self.running:
            return
        if self.stop_requested or not self.pending:
            self._finish_batch()
            return
        section = self.pending.pop(0)
        self.current = section
        self.info.setText(
            f"Generating section {section.section_number}: {section.title} "
            f"({len(self.completed)} completed; {len(self.failed)} failed)."
        )
        try:
            job = prepare_job(
                section.script, f"{section.section_number:02}-{safe_stem(section.title)}",
                self.output_dir, self.prefs,
                spoken_script=speech_text(section.script, self.rules),
            )
        except (OSError, ValueError) as exc:
            self.failed.append((section, str(exc)))
            self._set_result(section, "Failed: " + str(exc)[:65])
            self.current = None
            QTimer.singleShot(0, self._launch_next)
            return
        self.job = job
        self.process = QProcess(self)
        self.process.setProgram(str(self.backend.executable))
        self.process.setArguments(kokoro_arguments(job))
        self.process.setWorkingDirectory(str(job.work_dir))
        self.process.finished.connect(self._on_finished)
        self.process.errorOccurred.connect(self._on_error)
        self.process.start()

    def _on_error(self, error):
        if error == QProcess.ProcessError.FailedToStart and self.current is not None:
            self._fail_current("Kokoro could not be started")

    def _on_finished(self, exit_code, exit_status):
        if self.current is None or self.job is None:
            return
        if self.stop_requested:
            self._fail_current("Cancelled", count_failure=False)
            return
        if exit_status != QProcess.ExitStatus.NormalExit or exit_code:
            detail = bytes(self.process.readAllStandardError()).decode(
                "utf-8", errors="replace"
            ).strip()[-200:] if self.process else ""
            self._fail_current(f"Kokoro error ({exit_code}) {detail}")
            return
        try:
            new_wav = publish_take(self.job)
        except (OSError, ValueError) as exc:
            self._fail_current(f"Output error: {exc}")
            return
        section = self.current
        self.completed.append(CompletedTake(section, new_wav))
        self._set_result(section, new_wav.name)
        row = section.section_number - 1
        assign_item = QTableWidgetItem()
        assign_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable)
        assign_item.setCheckState(
            Qt.CheckState.Unchecked if section.previous_narration else Qt.CheckState.Checked
        )
        self.table.setItem(row, 4, assign_item)
        self._end_current()
        QTimer.singleShot(0, self._launch_next)

    def _set_result(self, section, message: str):
        self.table.item(section.section_number - 1, 3).setText(message)

    def _fail_current(self, message: str, *, count_failure: bool = True):
        if self.current is None:
            return
        section = self.current
        if count_failure:
            self.failed.append((section, message))
        self._set_result(section, message[:120])
        self._end_current()
        QTimer.singleShot(0, self._launch_next)

    def _end_current(self):
        cleanup_job(self.job)
        self.job = None
        if self.process is not None:
            self.process.deleteLater()
        self.process = None
        self.current = None

    def _finish_batch(self):
        self.running = False
        self.cancel_button.setEnabled(False)
        self.keep_button.setEnabled(True)
        self.info.setText(
            f"Batch finished: {len(self.completed)} WAV take(s) generated, "
            f"{len(self.failed)} failure(s). "
            "Check Assign new WAV on the desired rows, then confirm. "
            "Assignments are not saved to your project until you use Save Project."
        )
        self.refresh_actions()

    def cancel_remaining(self):
        if self.running:
            self.stop_requested = True
            self.pending.clear()
            if self.process is not None:
                self.process.kill()
            else:
                self._finish_batch()

    def review_and_accept(self):
        if self.running or not self.completed:
            return
        chosen = self.selected_for_assignment()
        if not chosen:
            return
        mapping = {item.section.section_id: item for item in self.completed}
        replacing = [mapping[sid].section.title for sid in chosen
                     if mapping[sid].section.previous_narration]
        if replacing:
            titles = ", ".join(replacing)
            answer = QMessageBox.question(
                self, "Replace existing section assignments?",
                "These sections already have narration:\n"
                f"{titles}\n\n"
                "Change their project references to the NEW WAVs? "
                "The old WAV files will not be touched.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
        try:
            # Preflight every selected WAV and section before closing this review.
            assign_completed_takes(
                self.project, self.completed, chosen, allow_replace=bool(replacing),
            )
        except (OSError, ValueError, MediaProbeError) as exc:
            QMessageBox.warning(
                self, "Cannot assign selected WAVs",
                f"Review these selections before continuing:\n\n{exc}\n\n"
                "All generated WAVs remain on disk. Project unchanged.",
            )
            return
        self.selected_assignments = chosen
        self.replacement_approved = bool(replacing)
        self.accept()

    def reject(self):
        if self.running:
            QMessageBox.information(
                self, "Generation active", "Use Cancel Remaining before closing. "
                "Already completed takes will be kept."
            )
            return
        super().reject()

    def closeEvent(self, event):
        if self.running:
            event.ignore()
            self.cancel_remaining()
            return
        event.accept()
