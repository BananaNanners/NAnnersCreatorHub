"""Preview and export a proposed Kdenlive timeline-marker plan."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QComboBox, QDialog, QFileDialog, QFormLayout, QHBoxLayout,
    QLabel, QMessageBox, QPushButton, QSpinBox, QTextEdit,
    QVBoxLayout,
)

from .markers import (
    FRAME_RATES, TIMING_BASES, MarkerPlanError, export_markers, marker_plan
)


class MarkerExportDialog(QDialog):
    def __init__(self, project: dict, default_directory: Path, parent=None):
        super().__init__(parent)
        self.project = project
        self.default_directory = default_directory
        self.export_path: Path | None = None
        self.setWindowTitle("Kdenlive Timeline Marker Export")
        self.resize(640, 460)
        layout = QVBoxLayout(self)
        description = QLabel(
            "Creates a proposed gapless sequence of section-start markers, NOT a "
            "snapshot of an existing Kdenlive timeline. "
            "Select exactly the frame rate used by your Kdenlive project."
        )
        description.setWordWrap(True)
        layout.addWidget(description)
        form = QFormLayout()
        self.fps_box = QComboBox()
        self.fps_box.addItems(list(FRAME_RATES))
        self.fps_box.setCurrentText("30")
        form.addRow("Kdenlive project FPS", self.fps_box)
        self.basis_box = QComboBox()
        for key, label in TIMING_BASES.items():
            self.basis_box.addItem(label, key)
        form.addRow("Section lengths from", self.basis_box)
        self.start_frame_box = QSpinBox()
        self.start_frame_box.setRange(0, 100_000_000)
        self.start_frame_box.setValue(0)
        form.addRow("First timeline frame", self.start_frame_box)
        layout.addLayout(form)
        self.explanation = QLabel(
            "Marker positions are rounded to whole frames; "
            "footage in/out points refer to source ranges, not Kdenlive timeline positions. "
            "If your actual edit has gaps, overlaps, B-roll, or transitions, "
            "you must adjust imported markers in Kdenlive."
        )
        self.explanation.setWordWrap(True)
        layout.addWidget(self.explanation)
        self.preview = QTextEdit()
        self.preview.setReadOnly(True)
        layout.addWidget(self.preview)
        buttons = QHBoxLayout()
        buttons.addStretch()
        self.export_button = QPushButton("Export New JSON…")
        self.export_button.clicked.connect(self.save_json)
        buttons.addWidget(self.export_button)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        buttons.addWidget(cancel)
        layout.addLayout(buttons)
        self.fps_box.currentTextChanged.connect(self.update_preview)
        self.basis_box.currentIndexChanged.connect(self.update_preview)
        self.start_frame_box.valueChanged.connect(self.update_preview)
        self.update_preview()

    def plan_args(self) -> dict:
        return {
            "fps_name": self.fps_box.currentText(),
            "timing_basis": self.basis_box.currentData(),
            "starting_frame": self.start_frame_box.value(),
        }

    def update_preview(self) -> None:
        try:
            plan = marker_plan(self.project, **self.plan_args())
        except (MarkerPlanError, ValueError) as exc:
            self.preview.setPlainText(f"Cannot export yet:\n{exc}")
            self.export_button.setEnabled(False)
            return
        self.export_button.setEnabled(True)
        fps = FRAME_RATES[self.fps_box.currentText()]
        lines = [f"{len(plan)} marker(s) — positions are Kdenlive timeline frames", ""]
        for marker in plan:
            seconds = marker["pos"] / float(fps)
            lines.append(f"Frame {marker['pos']:>7}  (~{seconds:.3f}s)  {marker['comment']}")
        self.preview.setPlainText("\n".join(lines))

    def save_json(self) -> None:
        filename, _ = QFileDialog.getSaveFileName(
            self, "Export Kdenlive Timeline Markers",
            str(self.default_directory / "kdenlive-section-markers.json"),
            "Kdenlive marker JSON (*.json)"
        )
        if not filename:
            return
        target = Path(filename)
        if target.suffix.lower() != ".json":
            target = target.with_suffix(".json")
        if target.exists():
            QMessageBox.warning(
                self, "File exists", "Choose a new filename. Existing files are never overwritten."
            )
            return
        try:
            export_markers(target, self.project, **self.plan_args())
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, "Marker export failed", str(exc))
            return
        self.export_path = target
        self.accept()
