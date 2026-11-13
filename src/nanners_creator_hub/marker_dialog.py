"""Preview and export a proposed Kdenlive timeline-marker plan."""
from __future__ import annotations

from pathlib import Path
import os

from PySide6.QtGui import QPalette
from PySide6.QtWidgets import (
    QApplication, QComboBox, QDialog, QFileDialog, QFormLayout, QFrame,
    QHBoxLayout, QLabel, QMessageBox, QPushButton, QSpinBox, QTextEdit,
    QVBoxLayout,
)

from .markers import (
    FRAME_RATES, TIMING_BASES, MarkerPlanError, export_markers, marker_plan
)


def detected_kdenlive_fps(config_path: Path | None = None) -> str | None:
    """Read Kdenlive's saved preference, not an open project's actual frame rate."""
    path = config_path or (
        Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))) / "kdenliverc"
    )
    try:
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.strip().startswith("project_fps="):
                value = line.partition("=")[2].strip()
                if value in FRAME_RATES:
                    return value
                aliases = {
                    "23.976": "23.976 (24000/1001)",
                    "29.97": "29.97 (30000/1001)",
                    "59.94": "59.94 (60000/1001)",
                }
                return aliases.get(value)
    except OSError:
        pass
    return None


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
        self.kdenlive_fps_preference = detected_kdenlive_fps()
        self.fps_box.setCurrentText(self.kdenlive_fps_preference or "30")
        form.addRow("Kdenlive project FPS", self.fps_box)
        self.fps_hint = QLabel(
            f"Kdenlive saved preference: {self.kdenlive_fps_preference} FPS. "
            "Check Project Settings: the currently open project's FPS can differ."
            if self.kdenlive_fps_preference
            else "Kdenlive FPS preference unavailable. Confirm the actual "
                 "timeline FPS in Kdenlive Project Settings."
        )
        self.fps_hint.setWordWrap(True)
        form.addRow("", self.fps_hint)
        self.basis_box = QComboBox()
        for key, label in TIMING_BASES.items():
            self.basis_box.addItem(label, key)
        form.addRow("Section lengths from", self.basis_box)
        self.start_frame_box = QSpinBox()
        self.start_frame_box.setRange(0, 100_000_000)
        self.start_frame_box.setValue(0)
        form.addRow("First timeline frame", self.start_frame_box)
        layout.addLayout(form)
        self.warning_banner, self.warning_label = self.make_banner("fpsMismatchBanner", "warning")
        self.error_banner, self.error_label = self.make_banner("exportErrorBanner", "error")
        layout.addWidget(self.warning_banner)
        layout.addWidget(self.error_banner)
        self.warning_banner.hide()
        self.error_banner.hide()
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

    @staticmethod
    def make_banner(object_name: str, severity: str) -> tuple[QFrame, QLabel]:
        """High-contrast alert banners for both dark and light Qt palettes."""
        window = QApplication.palette().color(QPalette.ColorRole.Window)
        dark = window.lightness() < 128
        if severity == "warning":
            bg, border, ink = (
                ("#49340e", "#e9ae35", "#ffedbe") if dark
                else ("#fff2c6", "#ad6a00", "#513500")
            )
        else:
            bg, border, ink = (
                ("#4b2025", "#f17b83", "#ffe2e4") if dark
                else ("#ffe3e3", "#b32230", "#600d16")
            )
        frame = QFrame()
        frame.setObjectName(object_name)
        frame.setStyleSheet(
            f"QFrame#{object_name} {{background: {bg}; border: 2px solid {border}; "
            "border-radius: 8px;}"
        )
        row = QHBoxLayout(frame)
        row.setContentsMargins(12, 10, 12, 10)
        label = QLabel()
        label.setWordWrap(True)
        label.setStyleSheet(f"color: {ink}; background: transparent; font-weight: 600;")
        row.addWidget(label)
        return frame, label

    def plan_args(self) -> dict:
        return {
            "fps_name": self.fps_box.currentText(),
            "timing_basis": self.basis_box.currentData(),
            "starting_frame": self.start_frame_box.value(),
        }

    def update_preview(self) -> None:
        mismatched = bool(
            self.kdenlive_fps_preference
            and self.fps_box.currentText() != self.kdenlive_fps_preference
        )
        self.warning_banner.setVisible(mismatched)
        if mismatched:
            self.warning_label.setText(
                f"⚠ FRAME-RATE MISMATCH — Selected {self.fps_box.currentText()} FPS, "
                f"Kdenlive saved preference {self.kdenlive_fps_preference} FPS. "
                "Markers may appear at incorrect times. Check the open project's "
                "actual FPS in Project Settings before exporting."
            )
        try:
            plan = marker_plan(self.project, **self.plan_args())
        except (MarkerPlanError, ValueError) as exc:
            self.preview.setPlainText(f"Cannot export yet:\n{exc}")
            self.error_label.setText(f"⛔ CANNOT EXPORT — {exc}")
            self.error_banner.show()
            self.export_button.setEnabled(False)
            return
        self.error_banner.hide()
        self.export_button.setEnabled(True)
        fps = FRAME_RATES[self.fps_box.currentText()]
        lines = [f"{len(plan)} marker(s) — positions are Kdenlive timeline frames", ""]
        if (self.kdenlive_fps_preference
                and self.fps_box.currentText() != self.kdenlive_fps_preference):
            lines.extend([
                "WARNING: Selected FPS differs from Kdenlive's saved preference "
                f"({self.kdenlive_fps_preference}).",
                "Confirm the open Kdenlive project's FPS before importing.",
                "",
            ])
        for marker in plan:
            seconds = marker["pos"] / float(fps)
            lines.append(f"Frame {marker['pos']:>7}  (~{seconds:.3f}s)  {marker['comment']}")
        self.preview.setPlainText("\n".join(lines))

    def save_json(self) -> None:
        if (self.kdenlive_fps_preference
                and self.fps_box.currentText() != self.kdenlive_fps_preference):
            choice = QMessageBox.question(
                self, "Confirm marker frame rate",
                f"You selected {self.fps_box.currentText()} FPS, but Kdenlive's "
                f"saved preference is {self.kdenlive_fps_preference} FPS. "
                "These can differ from the open project. Have you verified "
                "the actual project's FPS?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if choice != QMessageBox.StandardButton.Yes:
                return
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
