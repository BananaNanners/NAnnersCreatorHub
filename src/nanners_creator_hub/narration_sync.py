"""Narration waveform and footage-length comparison without editing source files."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QProcess, QUrl
from PySide6.QtGui import QColor, QPainter, QPalette, QPen
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtWidgets import (
    QDialog, QDoubleSpinBox, QFormLayout, QHBoxLayout, QLabel, QPushButton,
    QSlider, QVBoxLayout, QWidget,
)

from .waveform import (
    MAX_WAVEFORM_DURATION, Alignment, ffmpeg_waveform_args,
    peaks_from_pcm, suggested_out_point, validate_sync_range,
)


class TimingWaveform(QWidget):
    """Relative-duration comparison: narration begins at t=0 of chosen footage."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.peaks: tuple[float, ...] = ()
        self.narration_duration = 0.0
        self.footage_duration = 0.0
        self.setMinimumHeight(220)
        self.setObjectName("narrationTimingWaveform")

    def set_timing(self, narration: float, footage: float):
        self.narration_duration = max(0.0, narration)
        self.footage_duration = max(0.0, footage)
        self.update()

    def set_peaks(self, peaks: tuple[float, ...]):
        self.peaks = peaks
        self.update()

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        palette = self.palette()
        background = palette.color(QPalette.ColorRole.Base)
        foreground = palette.color(QPalette.ColorRole.Text)
        accent = palette.color(QPalette.ColorRole.Highlight)
        secondary = palette.color(QPalette.ColorRole.Mid)
        painter.fillRect(self.rect(), background)

        w = self.width()
        x0, width = 42, max(20, w - 64)
        duration = max(self.narration_duration, self.footage_duration, 0.01)
        painter.setPen(foreground)
        painter.drawText(x0, 18, "Narration waveform")
        painter.drawText(x0, 161, "Selected footage length")
        painter.setPen(QPen(secondary, 1))
        painter.drawLine(x0, 92, x0 + width, 92)
        painter.drawLine(x0, 185, x0 + width, 185)

        narration_x = max(1, int(width * self.narration_duration / duration))
        if self.peaks:
            painter.setPen(QPen(accent, 1.6))
            half_height = 58
            for i, peak in enumerate(self.peaks):
                x = x0 + int(i * narration_x / len(self.peaks))
                h = max(1, int(half_height * peak))
                painter.drawLine(x, 92 - h, x, 92 + h)
        else:
            painter.setPen(secondary)
            painter.drawText(x0 + 12, 95, "Waveform loading or unavailable")
        if self.footage_duration > 0:
            footage_width = max(1, int(width * self.footage_duration / duration))
            painter.fillRect(x0, 175, footage_width, 21, accent)
        painter.setPen(foreground)
        painter.drawText(x0, 219, "0 s")
        painter.drawText(
            x0 + max(0, width - 90), 219, f"{duration:.2f} s"
        )
        painter.end()


class NarrationSyncDialog(QDialog):
    """Read-only waveform playback; applying source range requires confirmation."""
    def __init__(self, audio_path: Path, narration_duration: float,
                 footage_path: Path | None = None,
                 footage_duration: float | None = None,
                 start: float = 0.0, end: float = 0.0, parent=None):
        super().__init__(parent)
        self.audio_path = Path(audio_path).expanduser().resolve()
        if not self.audio_path.is_file():
            raise FileNotFoundError("Assigned narration audio is missing.")
        if narration_duration <= 0:
            raise ValueError("Narration duration is unavailable; rescan the media.")
        self.narration_duration = narration_duration
        self.footage_path = Path(footage_path).expanduser().resolve() if footage_path else None
        self.footage_duration = footage_duration
        self.applied_range: tuple[float, float] | None = None
        self.setWindowTitle("Narration Sync — Waveform & Footage Timing")
        self.resize(860, 590)
        self.setMinimumSize(680, 520)

        root = QVBoxLayout(self)
        self.help_label = QLabel(
            "Compare the narration waveform with your selected footage range. "
            "Both start at the section's proposed timeline start (relative 0 s), "
            "not at the source video's absolute IN point. "
            "Only Apply Range changes the section; no audio/video file is edited."
        )
        self.help_label.setWordWrap(True)
        root.addWidget(self.help_label)
        self.waveform = TimingWaveform()
        root.addWidget(self.waveform, 2)

        self.waveform_status = QLabel("Loading narration waveform…")
        self.waveform_status.setObjectName("narrationWaveformStatus")
        self.waveform_status.setWordWrap(True)
        root.addWidget(self.waveform_status)

        self.player = QMediaPlayer(self)
        self.audio = QAudioOutput(self)
        self.audio.setVolume(0.8)
        self.player.setAudioOutput(self.audio)
        self.player.setSource(QUrl.fromLocalFile(str(self.audio_path)))
        playback = QHBoxLayout()
        self.play_button = QPushButton("Play / Pause Narration")
        self.play_button.setObjectName("syncPlayNarration")
        self.play_button.clicked.connect(self.toggle_play)
        playback.addWidget(self.play_button)
        self.stop_button = QPushButton("Stop")
        self.stop_button.clicked.connect(self.player.stop)
        playback.addWidget(self.stop_button)
        self.time_label = QLabel("00:00 / 00:00")
        playback.addWidget(self.time_label)
        root.addLayout(playback)
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setObjectName("syncNarrationScrubber")
        self.slider.setRange(0, max(1, round(narration_duration * 1000)))
        self.slider.sliderMoved.connect(self.player.setPosition)
        root.addWidget(self.slider)
        self.player.positionChanged.connect(self.update_position)
        self.player.durationChanged.connect(self.update_duration)
        self.player.errorOccurred.connect(self.audio_error)

        self.in_spin = QDoubleSpinBox()
        self.out_spin = QDoubleSpinBox()
        self.in_spin.setObjectName("syncFootageIn")
        self.out_spin.setObjectName("syncFootageOut")
        for spin in (self.in_spin, self.out_spin):
            spin.setDecimals(3)
            spin.setRange(0, 86400)
            spin.setSingleStep(0.1)
            spin.setSuffix(" s")
        self.in_spin.setValue(start)
        self.out_spin.setValue(end)
        settings = QFormLayout()
        settings.addRow("Footage source IN", self.in_spin)
        settings.addRow("Footage source OUT", self.out_spin)
        root.addLayout(settings)

        self.match_button = QPushButton("Match Footage Length to Narration")
        self.match_button.setObjectName("syncMatchNarrationLength")
        self.match_button.clicked.connect(self.match_narration)
        root.addWidget(self.match_button)
        self.alignment_label = QLabel()
        self.alignment_label.setObjectName("narrationAlignmentStatus")
        self.alignment_label.setWordWrap(True)
        root.addWidget(self.alignment_label)

        actions = QHBoxLayout()
        self.apply_button = QPushButton("Apply Range to Section")
        self.apply_button.setObjectName("syncApplyRange")
        self.apply_button.clicked.connect(self.apply_range)
        actions.addWidget(self.apply_button)
        self.cancel_button = QPushButton("Cancel / Close")
        self.cancel_button.clicked.connect(self.reject)
        actions.addWidget(self.cancel_button)
        root.addLayout(actions)

        if not self.footage_path:
            self.in_spin.setEnabled(False)
            self.out_spin.setEnabled(False)
            self.match_button.setEnabled(False)
            self.apply_button.setEnabled(False)
            self.alignment_label.setText(
                "No footage assigned. Narration preview is available; assign footage "
                "in Assisted Editing to compare and adjust a range."
            )
        else:
            self.in_spin.valueChanged.connect(self.update_alignment)
            self.out_spin.valueChanged.connect(self.update_alignment)
            self.update_alignment()

        self.waveform_process: QProcess | None = None
        if narration_duration > MAX_WAVEFORM_DURATION:
            self.waveform_status.setText(
                "Waveform preview is limited to 15-minute narration clips. "
                "Playback and duration comparison remain available."
            )
        else:
            self.waveform_process = QProcess(self)
            self.waveform_process.setProgram("ffmpeg")
            self.waveform_process.setArguments(ffmpeg_waveform_args(self.audio_path))
            self.waveform_process.finished.connect(self.waveform_finished)
            self.waveform_process.errorOccurred.connect(self.waveform_error)
            self.waveform_process.start()

    def update_alignment(self):
        start, end = self.in_spin.value(), self.out_spin.value()
        length = max(0.0, end - start)
        self.waveform.set_timing(self.narration_duration, length)
        try:
            alignment = validate_sync_range(
                start, end, self.footage_duration, self.narration_duration
            )
        except ValueError as exc:
            self.alignment_label.setText(f"Choose a valid footage range: {exc}")
            return
        delta = alignment.delta_seconds
        if abs(delta) <= 0.05:
            label = "Lengths match (within 0.05 s)."
        elif delta > 0:
            label = f"Footage is {delta:.3f} s LONGER than narration."
        else:
            label = f"Footage is {-delta:.3f} s SHORTER than narration."
        self.alignment_label.setText(
            f"Narration {alignment.narration_seconds:.3f} s · "
            f"Footage {alignment.footage_seconds:.3f} s · {label}"
        )

    def match_narration(self):
        try:
            proposed = suggested_out_point(
                self.in_spin.value(), self.narration_duration, self.footage_duration
            )
        except ValueError as exc:
            self.alignment_label.setText(
                f"Cannot match lengths: {exc} Select more source footage or a different IN point."
            )
            return
        self.out_spin.setValue(proposed)
        self.update_alignment()

    def apply_range(self):
        if self.footage_path is None:
            return
        try:
            validated = validate_sync_range(
                self.in_spin.value(), self.out_spin.value(),
                self.footage_duration, self.narration_duration
            )
        except ValueError as exc:
            self.alignment_label.setText(f"Cannot apply: {exc}")
            return
        self.applied_range = (validated.in_seconds, validated.out_seconds)
        self.accept()

    def toggle_play(self):
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
        else:
            self.player.play()

    def update_position(self, ms: int):
        if not self.slider.isSliderDown():
            self.slider.setValue(ms)
        self.update_time_label()

    def update_duration(self, ms: int):
        if ms > 0:
            self.slider.setMaximum(ms)
        self.update_time_label()

    def update_time_label(self):
        pos = max(0, self.player.position()) // 1000
        length = max(0, self.player.duration()) // 1000
        self.time_label.setText(
            f"{pos // 60:02}:{pos % 60:02} / {length // 60:02}:{length % 60:02}"
        )

    def audio_error(self, _error, message):
        self.waveform_status.setText(f"Narration playback error: {message}")

    def waveform_error(self, error):
        if error == QProcess.ProcessError.FailedToStart:
            self.waveform_status.setText(
                "FFmpeg could not start; duration comparison still works."
            )

    def waveform_finished(self, exit_code, exit_status):
        process = self.waveform_process
        if process is None:
            return
        if exit_status != QProcess.ExitStatus.NormalExit or exit_code != 0:
            error = bytes(process.readAllStandardError()).decode(
                "utf-8", errors="replace"
            ).strip()[-200:]
            self.waveform_status.setText(
                f"Waveform unavailable (FFmpeg): {error or 'decode failed'}"
            )
            return
        try:
            peaks = peaks_from_pcm(bytes(process.readAllStandardOutput()))
        except ValueError as exc:
            self.waveform_status.setText(f"Waveform unavailable: {exc}")
            return
        self.waveform.set_peaks(peaks)
        self.waveform_status.setText(
            "Waveform ready. This is a relative timing guide, not a Kdenlive timeline."
        )

    def shutdown(self):
        self.player.stop()
        self.player.setSource(QUrl())
        if self.waveform_process and (
            self.waveform_process.state() != QProcess.ProcessState.NotRunning
        ):
            self.waveform_process.kill()
            self.waveform_process.waitForFinished(2000)

    def accept(self):
        self.shutdown()
        super().accept()

    def reject(self):
        self.shutdown()
        super().reject()

    def closeEvent(self, event):
        self.shutdown()
        super().closeEvent(event)
