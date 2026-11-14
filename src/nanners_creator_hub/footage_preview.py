"""Qt video preview and non-destructive source in/out selection."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import (
    QDialog, QDoubleSpinBox, QFormLayout, QHBoxLayout, QLabel,
    QMessageBox, QPushButton, QSlider, QVBoxLayout,
)


def validate_preview_range(start: float, end: float, duration: float | None) -> tuple[float, float]:
    if not 0 <= start < end:
        raise ValueError("Out point must be later than in point.")
    if duration is not None and (duration <= 0 or end > duration + 0.05):
        raise ValueError("Selected range exceeds the source recording duration.")
    if end > 86400:
        raise ValueError("Source range exceeds the supported 24-hour limit.")
    return (round(start, 3), round(end, 3))


def format_position(ms: int) -> str:
    seconds = max(0, ms) // 1000
    hours, remaining = divmod(seconds, 3600)
    minutes, seconds = divmod(remaining, 60)
    return f"{hours:02}:{minutes:02}:{seconds:02}"


class FootagePreviewDialog(QDialog):
    """Playback and scrubbing never alter footage or the editor's section fields."""
    def __init__(self, source: Path, duration: float | None = None,
                 start: float = 0, end: float = 0, parent=None,
                 *, seek_seconds: float | None = None, allow_apply: bool = True):
        super().__init__(parent)
        self.source = Path(source).expanduser().resolve()
        if not self.source.is_file():
            raise FileNotFoundError(f"Recording is missing: {self.source}")
        if self.source.suffix.lower() not in {
            ".mp4", ".mkv", ".mov", ".webm", ".avi", ".m4v"
        }:
            raise ValueError("Choose an imported video recording to preview.")
        self.source_duration = duration if duration and duration > 0 else None
        self.applied_range: tuple[float, float] | None = None
        self.allow_apply = allow_apply
        self._pending_seek_ms = (
            max(0, round(seek_seconds * 1000))
            if seek_seconds is not None else None
        )
        self.setWindowTitle(f"Footage Preview — {self.source.name}")
        self.resize(850, 640)
        self.setMinimumSize(650, 470)

        layout = QVBoxLayout(self)
        self.help_label = QLabel(
            "Preview and scrub the ORIGINAL recording. Set IN and OUT with the current "
            "playhead or edit the seconds below. Only 'Apply Range to Section' updates "
            "the project's source range; no video is cut or altered."
        )
        self.help_label.setWordWrap(True)
        if not allow_apply:
            self.help_label.setText(
                "Browsing this imported recording only. It is not assigned to the "
                "selected tutorial section; assign it using the Footage selector "
                "before applying source IN/OUT points. No files are changed."
            )
        layout.addWidget(self.help_label)

        self.player = QMediaPlayer(self)
        self.audio = QAudioOutput(self)
        self.player.setAudioOutput(self.audio)
        self.audio.setVolume(0.8)
        self.video = QVideoWidget()
        self.video.setMinimumHeight(220)
        self.player.setVideoOutput(self.video)
        layout.addWidget(self.video, 1)

        playback_row = QHBoxLayout()
        self.play_button = QPushButton("Play / Pause")
        self.play_button.setObjectName("footagePreviewPlay")
        self.play_button.clicked.connect(self.toggle_playback)
        playback_row.addWidget(self.play_button)
        self.stop_button = QPushButton("Stop")
        self.stop_button.clicked.connect(self.player.stop)
        playback_row.addWidget(self.stop_button)
        self.position_label = QLabel("00:00:00 / --:--:--")
        playback_row.addWidget(self.position_label)
        layout.addLayout(playback_row)

        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setObjectName("footagePreviewScrubber")
        self.slider.setRange(0, max(1, int((self.source_duration or 1) * 1000)))
        self.slider.sliderMoved.connect(self.player.setPosition)
        layout.addWidget(self.slider)

        self.start_spin = QDoubleSpinBox()
        self.end_spin = QDoubleSpinBox()
        self.start_spin.setObjectName("footagePreviewIn")
        self.end_spin.setObjectName("footagePreviewOut")
        for field in (self.start_spin, self.end_spin):
            field.setRange(0, 86400)
            field.setDecimals(3)
            field.setSingleStep(0.1)
            field.setSuffix(" s")
        self.start_spin.setValue(max(0, start))
        self.end_spin.setValue(max(0, end))
        form = QFormLayout()
        start_row = QHBoxLayout()
        start_row.addWidget(self.start_spin)
        self.mark_in_button = QPushButton("Mark IN at Playhead")
        self.mark_in_button.clicked.connect(
            lambda: self.start_spin.setValue(self.player.position() / 1000)
        )
        start_row.addWidget(self.mark_in_button)
        form.addRow("IN point", start_row)
        end_row = QHBoxLayout()
        end_row.addWidget(self.end_spin)
        self.mark_out_button = QPushButton("Mark OUT at Playhead")
        self.mark_out_button.clicked.connect(
            lambda: self.end_spin.setValue(self.player.position() / 1000)
        )
        end_row.addWidget(self.mark_out_button)
        form.addRow("OUT point", end_row)
        layout.addLayout(form)

        self.message = QLabel("No changes have been applied.")
        self.message.setWordWrap(True)
        layout.addWidget(self.message)
        buttons = QHBoxLayout()
        self.apply_button = QPushButton("Apply Range to Section")
        self.apply_button.setObjectName("footagePreviewApply")
        self.apply_button.clicked.connect(self.apply_range)
        self.apply_button.setEnabled(allow_apply)
        buttons.addWidget(self.apply_button)
        self.cancel_button = QPushButton("Cancel / Close")
        self.cancel_button.clicked.connect(self.reject)
        buttons.addWidget(self.cancel_button)
        layout.addLayout(buttons)

        self.player.positionChanged.connect(self.position_changed)
        self.player.durationChanged.connect(self.duration_changed)
        self.player.errorOccurred.connect(self.playback_error)
        self.player.mediaStatusChanged.connect(self._seek_when_ready)
        self.player.setSource(QUrl.fromLocalFile(str(self.source)))

    def _seek_when_ready(self, status):
        if self._pending_seek_ms is None:
            return
        if status in (
            QMediaPlayer.MediaStatus.LoadedMedia,
            QMediaPlayer.MediaStatus.BufferedMedia,
            QMediaPlayer.MediaStatus.BufferingMedia,
        ):
            seek = self._pending_seek_ms
            self._pending_seek_ms = None
            self.player.setPosition(seek)

    def position_changed(self, value: int):
        if not self.slider.isSliderDown():
            self.slider.setValue(value)
        self.refresh_position()

    def duration_changed(self, duration_ms: int):
        if duration_ms > 0:
            self.slider.setMaximum(duration_ms)
            if self.source_duration is None:
                self.source_duration = duration_ms / 1000
        self.refresh_position()

    def refresh_position(self):
        elapsed = format_position(self.player.position())
        duration = format_position(self.player.duration()) if self.player.duration() > 0 else "--:--:--"
        self.position_label.setText(f"{elapsed} / {duration}")

    def toggle_playback(self):
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
        else:
            self.player.play()

    def playback_error(self, _error, message):
        self.message.setText(f"Playback unavailable: {message}")

    def apply_range(self):
        if not self.allow_apply:
            return
        try:
            start, end = validate_preview_range(
                self.start_spin.value(), self.end_spin.value(), self.source_duration
            )
        except ValueError as exc:
            self.message.setText(f"Cannot apply source range: {exc}")
            return
        self.applied_range = (start, end)
        self.accept()

    def stop_preview(self):
        self.player.stop()
        self.player.setSource(QUrl())

    def accept(self):
        self.stop_preview()
        super().accept()

    def reject(self):
        self.stop_preview()
        super().reject()
