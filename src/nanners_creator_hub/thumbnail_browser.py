"""Non-destructive thumbnail browser for imported video recordings.

FFmpeg frame decoding runs asynchronously, one bounded JPEG at a time.
Results are kept in memory only; no source videos or project files are changed.
"""
from __future__ import annotations

from pathlib import Path
import shutil

from PySide6.QtCore import QProcess, Qt, QTimer, QSize
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QComboBox, QDialog, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QMessageBox, QPushButton, QVBoxLayout,
)

from .thumbnails import thumbnail_args, thumbnail_times, timestamp_label, video_entries


class ThumbnailBrowserDialog(QDialog):
    def __init__(self, media: list[dict], preferred_path: str | None = None,
                 parent=None):
        super().__init__(parent)
        self.videos = video_entries(media)
        if not self.videos:
            raise ValueError("Import at least one video before opening the thumbnail browser.")
        self.selected_source: Path | None = None
        self.selected_seconds: float | None = None
        self._times: tuple[float, ...] = ()
        self._current_index = 0
        self._decoded = 0
        self._failed = 0
        self._closed = False
        self._process: QProcess | None = None
        self._ffmpeg = shutil.which("ffmpeg")
        self.setWindowTitle("Footage Thumbnail Browser — imported recordings")
        self.resize(910, 680)
        self.setMinimumSize(680, 500)

        root = QVBoxLayout(self)
        info = QLabel(
            "Browse sampled frames from imported footage. Double-click a thumbnail or "
            "choose 'Preview Selected Moment' to jump to that time in the video preview. "
            "Browsing never changes a tutorial section or a source recording."
        )
        info.setWordWrap(True)
        root.addWidget(info)
        source_row = QHBoxLayout()
        source_row.addWidget(QLabel("Recording"))
        self.source_selector = QComboBox()
        self.source_selector.setObjectName("thumbnailSourceSelector")
        for item in self.videos:
            self.source_selector.addItem(
                item.get("name") or Path(item["path"]).name,
                item["path"],
            )
        source_row.addWidget(self.source_selector, 1)
        self.reload_button = QPushButton("Refresh Thumbnails")
        self.reload_button.clicked.connect(self.load_current)
        source_row.addWidget(self.reload_button)
        root.addLayout(source_row)

        self.cards = QListWidget()
        self.cards.setObjectName("thumbnailFrameList")
        self.cards.setViewMode(QListWidget.ViewMode.IconMode)
        self.cards.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.cards.setFlow(QListWidget.Flow.LeftToRight)
        self.cards.setWrapping(True)
        self.cards.setMovement(QListWidget.Movement.Static)
        self.cards.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.cards.setIconSize(QSize(210, 118))
        self.cards.setGridSize(QSize(229, 150))
        self.cards.setSpacing(7)
        self.cards.itemSelectionChanged.connect(self.update_preview_button)
        self.cards.itemDoubleClicked.connect(lambda _item: self.preview_selected())
        root.addWidget(self.cards, 1)

        self.progress = QLabel("Select an imported video to load thumbnail previews.")
        self.progress.setObjectName("thumbnailProgressLabel")
        self.progress.setWordWrap(True)
        root.addWidget(self.progress)

        buttons = QHBoxLayout()
        self.preview_button = QPushButton("Preview Selected Moment")
        self.preview_button.setObjectName("thumbnailPreviewButton")
        self.preview_button.setEnabled(False)
        self.preview_button.clicked.connect(self.preview_selected)
        buttons.addWidget(self.preview_button)
        self.close_button = QPushButton("Close")
        self.close_button.clicked.connect(self.reject)
        buttons.addWidget(self.close_button)
        root.addLayout(buttons)

        if preferred_path:
            matched = self.source_selector.findData(preferred_path)
            if matched >= 0:
                self.source_selector.setCurrentIndex(matched)
        self.source_selector.currentIndexChanged.connect(self.load_current)
        self.load_current()

    def update_preview_button(self):
        self.preview_button.setEnabled(bool(self.cards.selectedItems()))

    def load_current(self):
        self._stop_process()
        self.cards.clear()
        self._times = ()
        self._current_index = 0
        self._decoded = 0
        self._failed = 0
        self.selected_source = None
        self.selected_seconds = None
        self.update_preview_button()

        path_str = self.source_selector.currentData()
        if not path_str:
            self.progress.setText("Choose an imported recording.")
            return
        source = Path(path_str).expanduser()
        if not source.is_file():
            self.progress.setText("Recording is missing. Use Rescan Media to check references.")
            return
        entry = self.videos[self.source_selector.currentIndex()]
        duration = entry.get("duration_seconds")
        if not isinstance(duration, (float, int)) or duration <= 0:
            self.progress.setText(
                "Video duration is unavailable. Use Rescan Media before browsing thumbnails."
            )
            return
        try:
            self._times = thumbnail_times(float(duration))
        except ValueError as exc:
            self.progress.setText(str(exc))
            return
        if not self._ffmpeg:
            self.progress.setText("FFmpeg is missing. Install it to generate thumbnails.")
            return
        self.progress.setText(f"Extracting 12 thumbnail samples from {source.name}…")
        self._launch_next()

    def _launch_next(self):
        if self._closed or self._process is not None:
            return
        if self._current_index >= len(self._times):
            self.progress.setText(
                f"Finished: {self._decoded}/{len(self._times)} thumbnails ready"
                + (f"; {self._failed} could not be decoded." if self._failed else ".")
                + " Choose a frame and preview it."
            )
            return
        timestamp = self._times[self._current_index]
        source = Path(self.source_selector.currentData()).expanduser()
        process = QProcess(self)
        self._process = process
        process.setProgram(self._ffmpeg)
        process.setArguments(thumbnail_args(source, timestamp))
        process.finished.connect(
            lambda code, status, job=process, at=timestamp:
            self._on_frame_finished(job, at, code, status)
        )
        process.errorOccurred.connect(
            lambda error, job=process:
            self._on_frame_error(job, error)
        )
        self.progress.setText(
            f"Loading frame {self._current_index + 1}/{len(self._times)} "
            f"at {timestamp_label(timestamp)}…"
        )
        process.start()
        QTimer.singleShot(12000, lambda job=process: self._time_out(job))

    def _time_out(self, job: QProcess):
        if self._process is job and job.state() != QProcess.ProcessState.NotRunning:
            job.kill()

    def _on_frame_error(self, job: QProcess, error):
        if self._process is job and error == QProcess.ProcessError.FailedToStart:
            self.progress.setText("FFmpeg could not start. Check the installation.")
            self._stop_process()

    def _on_frame_finished(self, job: QProcess, timestamp: float, code, status):
        if self._process is not job:
            return
        data = bytes(job.readAllStandardOutput())
        pix = QPixmap()
        if (status == QProcess.ExitStatus.NormalExit and code == 0
                and len(data) < 8_000_000 and pix.loadFromData(data, "JPG")):
            item = QListWidgetItem(QIcon(pix), timestamp_label(timestamp))
            item.setData(Qt.ItemDataRole.UserRole, timestamp)
            item.setToolTip(f"Jump to {timestamp:.3f} s of this source recording")
            self.cards.addItem(item)
            self._decoded += 1
            if self._decoded == 1:
                self.cards.setCurrentItem(item)
        else:
            self._failed += 1
        self._process = None
        job.deleteLater()
        self._current_index += 1
        # Defer the next process so UI rendering and cancellation stay responsive.
        QTimer.singleShot(0, self._launch_next)

    def preview_selected(self):
        items = self.cards.selectedItems()
        if not items:
            return
        self.selected_source = Path(self.source_selector.currentData()).expanduser().resolve()
        self.selected_seconds = float(items[0].data(Qt.ItemDataRole.UserRole))
        self.accept()

    def _stop_process(self):
        job = self._process
        if job is None:
            return
        self._process = None
        job.blockSignals(True)
        if job.state() != QProcess.ProcessState.NotRunning:
            job.kill()
            job.waitForFinished(1500)
        job.deleteLater()

    def accept(self):
        self._closed = True
        self._stop_process()
        super().accept()

    def reject(self):
        self._closed = True
        self._stop_process()
        super().reject()

    def closeEvent(self, event):
        self._closed = True
        self._stop_process()
        super().closeEvent(event)
