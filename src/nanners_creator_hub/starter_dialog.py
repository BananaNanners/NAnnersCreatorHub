"""Preview and export a new Kdenlive starter timeline project (prototype)."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QComboBox, QDialog, QFileDialog, QFormLayout, QHBoxLayout,
    QLabel, QMessageBox, QPushButton, QTextEdit, QVBoxLayout,
)

from .markers import FRAME_RATES
from .marker_dialog import detected_kdenlive_fps
from .starter_timeline import (
    StarterTimelineError, export_starter_timeline, plan_timeline,
)


class StarterTimelineDialog(QDialog):
    def __init__(self, project: dict, default_directory: Path, parent=None):
        super().__init__(parent)
        self.project = project
        self.default_directory = Path(default_directory)
        self.export_path: Path | None = None
        self.setWindowTitle("Automatic Kdenlive Starter Timeline — Prototype")
        self.resize(750, 580)
        self.setMinimumSize(650, 500)
        layout = QVBoxLayout(self)
        description = QLabel(
            "Creates a NEW .kdenlive editing project with sequential confirmed footage "
            "ranges on V1, Kokoro narration on A1, and section guides. "
            "This is a starter timeline, not a finished edit. No source videos or "
            "existing Kdenlive projects are modified."
        )
        description.setWordWrap(True)
        layout.addWidget(description)
        form = QFormLayout()
        self.fps_selector = QComboBox()
        self.fps_selector.setObjectName("starterTimelineFps")
        self.fps_selector.addItems(list(FRAME_RATES))
        self.saved_fps = detected_kdenlive_fps()
        self.fps_selector.setCurrentText(self.saved_fps or "60")
        self.fps_selector.currentTextChanged.connect(self.update_preview)
        form.addRow("New project frame rate", self.fps_selector)
        layout.addLayout(form)
        self.fps_label = QLabel()
        self.fps_label.setWordWrap(True)
        layout.addWidget(self.fps_label)
        self.preview = QTextEdit()
        self.preview.setObjectName("starterTimelinePreview")
        self.preview.setReadOnly(True)
        layout.addWidget(self.preview, 1)
        self.safety = QLabel(
            "Source trims are rounded to output frames. Narration is not time-stretched. "
            "Audio shorter than its footage leaves silence; longer audio is truncated "
            "at the section boundary. Original recording audio is muted. "
            "Review all generated clips and guides in Kdenlive."
        )
        self.safety.setWordWrap(True)
        layout.addWidget(self.safety)
        buttons = QHBoxLayout()
        self.export_button = QPushButton("Export New Kdenlive Project…")
        self.export_button.setObjectName("starterTimelineExport")
        self.export_button.clicked.connect(self.export_project)
        buttons.addWidget(self.export_button)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        buttons.addWidget(cancel)
        layout.addLayout(buttons)
        self.update_preview()

    def update_preview(self):
        fps = self.fps_selector.currentText()
        self.fps_label.setText(
            (f"Kdenlive saved FPS preference: {self.saved_fps}. "
             + ("⚠ Selected FPS differs from the saved preference."
                if fps != self.saved_fps else "Frame rate matches saved preference."))
            if self.saved_fps else
            "Kdenlive saved FPS preference is unavailable; check Project Settings."
        )
        try:
            plan = plan_timeline(self.project, fps)
        except (StarterTimelineError, ValueError) as exc:
            self.preview.setPlainText(f"Cannot export yet:\n{exc}")
            self.export_button.setEnabled(False)
            return
        self.export_button.setEnabled(True)
        lines = [
            "NEW .kdenlive PROJECT — starter prototype",
            f"{len(plan.clips)} confirmed section(s), {plan.total_frames} frames at {fps} fps",
            f"Project dimensions: {plan.width} × {plan.height}",
            "V1: selected footage ranges  |  A1: narration  |  Section guides",
            "",
        ]
        for clip in plan.clips:
            frames = clip.timeline_out - clip.timeline_in + 1
            lines.extend([
                f"{clip.number:02}  {clip.title}",
                f"   Timeline {clip.timeline_in}–{clip.timeline_out} "
                f"({frames} frames) | Footage {clip.video_source_in}–{clip.video_source_out}",
                f"   Narration: {Path(clip.narration).name}"
                + ("  ⚠ AUDIO TRUNCATED" if clip.narration_truncated else ""),
            ])
        if plan.skipped:
            lines.extend(["", "NOT EXPORTED — review status is not Confirmed:"])
            lines.extend(f"• {text}" for text in plan.skipped)
        self.preview.setPlainText("\n".join(lines))

    def export_project(self):
        fps = self.fps_selector.currentText()
        try:
            plan = plan_timeline(self.project, fps)
        except (ValueError, StarterTimelineError) as exc:
            QMessageBox.warning(self, "Starter timeline not ready", str(exc))
            return
        mismatched = bool(self.saved_fps and self.saved_fps != fps)
        truncated = [clip.title for clip in plan.clips if clip.narration_truncated]
        if mismatched or truncated:
            warnings = []
            if mismatched:
                warnings.append(
                    f"Selected {fps} FPS differs from Kdenlive's saved "
                    f"preference ({self.saved_fps} FPS)."
                )
            if truncated:
                warnings.append(
                    "Narration extends beyond the chosen footage for: "
                    + ", ".join(truncated[:8]) + ". Audio will be truncated."
                )
            confirm = QMessageBox.question(
                self, "Review starter timeline warnings",
                "\n\n".join(warnings) + "\n\nCreate the new project anyway?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if confirm != QMessageBox.StandardButton.Yes:
                return
        default = self.default_directory / "nanners-kdenlive-starter.kdenlive"
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save NEW Kdenlive Starter Project",
            str(default), "Kdenlive project (*.kdenlive)",
        )
        if not filename:
            return
        target = Path(filename).expanduser()
        if target.suffix.lower() != ".kdenlive":
            target = target.with_suffix(".kdenlive")
        try:
            export_starter_timeline(target, self.project, fps)
        except FileExistsError:
            QMessageBox.warning(
                self, "Project already exists",
                "Choose a new filename. Existing editing projects are never overwritten.",
            )
            return
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, "Export failed", str(exc))
            return
        self.export_path = target
        self.accept()
