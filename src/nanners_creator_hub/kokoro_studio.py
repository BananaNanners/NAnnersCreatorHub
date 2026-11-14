"""Kokoro Narration Studio — dev2 asynchronous, non-destructive WAV export."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QProcess, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtWidgets import (
    QComboBox, QDoubleSpinBox, QFileDialog, QFormLayout, QHBoxLayout,
    QLabel, QLineEdit, QMessageBox, QPlainTextEdit, QPushButton,
    QVBoxLayout, QWidget,
)

from .kokoro import (
    LANGUAGES, KokoroStatus, inspect_kokoro, load_preferences, save_preferences,
    default_preferences,
)
from .narration import (
    NarrationJob, cleanup_job, kokoro_arguments, prepare_job, publish_take,
)
from .pronunciations import load_rules, parse_rules, render_rules, save_rules, speech_text


def default_output_folder() -> Path:
    return Path.home() / "Music" / "NAnnersCreatorHub" / "Narration"


class KokoroStudio(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("kokoroNarrationStudio")
        self._loaded_settings = default_preferences()
        self._readiness: KokoroStatus | None = None
        self.job: NarrationJob | None = None
        self.process: QProcess | None = None
        self._cancel_requested = False
        self.last_output: Path | None = None
        try:
            self._rules = load_rules()
            self._rule_error = ""
        except (OSError, ValueError) as exc:
            self._rules = ()
            self._rule_error = f"Cannot load saved pronunciation rules: {exc}"
        self.audio_output = QAudioOutput(self)
        self.player = QMediaPlayer(self)
        self.player.setAudioOutput(self.audio_output)
        self.audio_output.setVolume(0.8)

        layout = QVBoxLayout(self)
        title = QLabel("Kokoro Narration Studio")
        title.setStyleSheet("font-size: 20px; font-weight: 700;")
        layout.addWidget(title)
        explanation = QLabel(
            "Write or paste your script, select a voice, and generate a new WAV take. "
            "The hub preserves existing audio and saves a matching script snapshot."
        )
        explanation.setWordWrap(True)
        layout.addWidget(explanation)

        form = QFormLayout()
        self.model_path = QLineEdit()
        self.model_path.setObjectName("kokoroModelPath")
        self.model_path.setPlaceholderText("Select Kokoro ONNX model…")
        model_row = QHBoxLayout()
        model_row.addWidget(self.model_path)
        browse_model = QPushButton("Browse…")
        browse_model.clicked.connect(self.browse_model)
        model_row.addWidget(browse_model)
        form.addRow("Model (.onnx)", model_row)

        self.voices_path = QLineEdit()
        self.voices_path.setObjectName("kokoroVoicesPath")
        self.voices_path.setPlaceholderText("Select Kokoro voices archive…")
        voice_row = QHBoxLayout()
        voice_row.addWidget(self.voices_path)
        browse_voices = QPushButton("Browse…")
        browse_voices.clicked.connect(self.browse_voices)
        voice_row.addWidget(browse_voices)
        form.addRow("Voices (.bin)", voice_row)

        self.voice_selector = QComboBox()
        self.voice_selector.setObjectName("kokoroVoiceSelector")
        form.addRow("Voice", self.voice_selector)
        self.language_selector = QComboBox()
        self.language_selector.addItems(LANGUAGES)
        form.addRow("Language", self.language_selector)
        self.speed_selector = QDoubleSpinBox()
        self.speed_selector.setRange(0.5, 2.0)
        self.speed_selector.setSingleStep(0.05)
        self.speed_selector.setDecimals(2)
        self.speed_selector.setSuffix("×")
        form.addRow("Speaking speed", self.speed_selector)
        layout.addLayout(form)

        self.status_label = QLabel()
        self.status_label.setObjectName("kokoroReadiness")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        buttons = QHBoxLayout()
        self.scan_button = QPushButton("Scan Kokoro Setup")
        self.scan_button.clicked.connect(self.scan)
        buttons.addWidget(self.scan_button)
        self.save_button = QPushButton("Save Voice & Model Preferences")
        self.save_button.clicked.connect(self.save)
        buttons.addWidget(self.save_button)
        layout.addLayout(buttons)

        layout.addWidget(QLabel("Narration script"))
        self.script_editor = QPlainTextEdit()
        self.script_editor.setObjectName("kokoroScriptEditor")
        self.script_editor.setPlaceholderText("Write or paste the text for this narration take…")
        self.script_editor.setMinimumHeight(125)
        layout.addWidget(self.script_editor, 3)

        layout.addWidget(QLabel("Pronunciation rules — one per line: Original => Spoken"))
        self.rules_editor = QPlainTextEdit()
        self.rules_editor.setObjectName("kokoroPronunciationRules")
        self.rules_editor.setPlainText(render_rules(self._rules))
        self.rules_editor.setMaximumHeight(85)
        layout.addWidget(self.rules_editor)
        self.speech_preview = QPlainTextEdit()
        self.speech_preview.setObjectName("kokoroSpeechPreview")
        self.speech_preview.setReadOnly(True)
        self.speech_preview.setMaximumHeight(100)
        layout.addWidget(QLabel("Speech-ready text (original script stays unchanged)"))
        layout.addWidget(self.speech_preview)
        self.rules_status = QLabel(self._rule_error or "Rules only affect speech text.")
        self.rules_status.setWordWrap(True)
        layout.addWidget(self.rules_status)
        rules_row = QHBoxLayout()
        self.save_rules_button = QPushButton("Save Pronunciations")
        self.save_rules_button.clicked.connect(self.save_pronunciations)
        rules_row.addWidget(self.save_rules_button)
        self.reset_rules_button = QPushButton("Reload Saved Rules")
        self.reset_rules_button.clicked.connect(self.reload_rules)
        rules_row.addWidget(self.reset_rules_button)
        layout.addLayout(rules_row)

        output_form = QFormLayout()
        self.take_name = QLineEdit("narration")
        self.take_name.setObjectName("kokoroTakeName")
        self.take_name.setPlaceholderText("e.g. 02-steam-compatibility")
        output_form.addRow("Take name", self.take_name)
        self.output_dir = QLineEdit(str(default_output_folder()))
        self.output_dir.setObjectName("kokoroOutputDir")
        folder_row = QHBoxLayout()
        folder_row.addWidget(self.output_dir)
        browse_output = QPushButton("Folder…")
        browse_output.clicked.connect(self.browse_output)
        folder_row.addWidget(browse_output)
        output_form.addRow("WAV folder", folder_row)
        layout.addLayout(output_form)

        self.generation_status = QLabel(
            "Ready to generate when a script is entered. Each take gets a unique name."
        )
        self.generation_status.setObjectName("kokoroGenerationStatus")
        self.generation_status.setWordWrap(True)
        layout.addWidget(self.generation_status)

        generation_row = QHBoxLayout()
        self.generate_button = QPushButton("Generate WAV")
        self.generate_button.setObjectName("kokoroGenerateWav")
        self.generate_button.clicked.connect(self.generate)
        generation_row.addWidget(self.generate_button)
        self.cancel_button = QPushButton("Cancel Generation")
        self.cancel_button.clicked.connect(self.cancel_generation)
        self.cancel_button.setEnabled(False)
        generation_row.addWidget(self.cancel_button)
        self.open_output_button = QPushButton("Open Output Folder")
        self.open_output_button.setEnabled(False)
        self.open_output_button.clicked.connect(self.open_output_folder)
        generation_row.addWidget(self.open_output_button)
        layout.addLayout(generation_row)

        playback_row = QHBoxLayout()
        self.play_button = QPushButton("Play Last Take")
        self.play_button.setObjectName("kokoroPlayLastTake")
        self.play_button.setEnabled(False)
        self.play_button.clicked.connect(self.play_last_take)
        playback_row.addWidget(self.play_button)
        self.stop_button = QPushButton("Stop Playback")
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self.player.stop)
        playback_row.addWidget(self.stop_button)
        self.playback_status = QLabel("No generated take selected for playback.")
        self.playback_status.setWordWrap(True)
        playback_row.addWidget(self.playback_status, 1)
        layout.addLayout(playback_row)
        self.player.errorOccurred.connect(self.playback_error)
        self.player.playbackStateChanged.connect(self.update_playback_controls)

        self._initial_load()
        self.model_path.editingFinished.connect(self.scan)
        self.voices_path.editingFinished.connect(self.scan)
        self.voice_selector.currentIndexChanged.connect(self.update_generate_enabled)
        self.script_editor.textChanged.connect(self.update_generate_enabled)
        self.script_editor.textChanged.connect(self.update_speech_preview)
        self.rules_editor.textChanged.connect(self.update_speech_preview)
        self.output_dir.textChanged.connect(self.update_generate_enabled)
        self.update_speech_preview()

    @property
    def is_generating(self) -> bool:
        return self.job is not None

    def _initial_load(self):
        try:
            prefs = load_preferences()
        except (ValueError, OSError) as exc:
            prefs = default_preferences()
            self.status_label.setText(f"Saved settings could not be read: {exc}. Using defaults.")
        self._loaded_settings = prefs
        self.model_path.setText(prefs["model_path"])
        self.voices_path.setText(prefs["voices_path"])
        self.language_selector.setCurrentText(prefs["language"])
        self.speed_selector.setValue(prefs["speed"])
        self.scan(preferred_voice=prefs["voice"])

    def current_prefs(self) -> dict:
        return {
            "schema_version": 1,
            "model_path": self.model_path.text().strip(),
            "voices_path": self.voices_path.text().strip(),
            "voice": self.voice_selector.currentData() or self._loaded_settings["voice"],
            "language": self.language_selector.currentText(),
            "speed": self.speed_selector.value(),
        }

    def scan(self, preferred_voice: str | None = None) -> KokoroStatus:
        if isinstance(preferred_voice, bool):
            preferred_voice = None
        voice = preferred_voice or self.voice_selector.currentData() or self._loaded_settings["voice"]
        prefs = self.current_prefs()
        prefs["voice"] = voice
        status = inspect_kokoro(prefs)
        self._readiness = status
        self.voice_selector.blockSignals(True)
        self.voice_selector.clear()
        for name in status.available_voices:
            self.voice_selector.addItem(name, name)
        selected = self.voice_selector.findData(voice)
        if selected >= 0:
            self.voice_selector.setCurrentIndex(selected)
        elif not status.available_voices:
            self.voice_selector.addItem("No voices detected", "")
        self.voice_selector.blockSignals(False)
        self.status_label.setText(
            f"✓ Kokoro ready — {len(status.available_voices)} voices detected."
            if status.ready
            else "Needs review: " + "; ".join(status.problems)
        )
        self.save_button.setEnabled(status.ready and not self.is_generating)
        self.update_generate_enabled()
        return status

    def spoken_text(self) -> str:
        return speech_text(self.script_editor.toPlainText(), parse_rules(self.rules_editor.toPlainText()))

    def update_speech_preview(self):
        try:
            self.speech_preview.setPlainText(self.spoken_text())
            self.rules_status.setText("✓ Pronunciation rules valid. Original script is preserved.")
        except ValueError as exc:
            self.speech_preview.setPlainText("")
            self.rules_status.setText(f"⚠ Invalid pronunciation rule: {exc}")
        self.update_generate_enabled()

    def save_pronunciations(self):
        try:
            rules = parse_rules(self.rules_editor.toPlainText())
            dest = save_rules(rules)
            self._rules = rules
            self.rules_status.setText(f"✓ Pronunciation rules saved to {dest}")
        except (OSError, ValueError) as exc:
            self.rules_status.setText(f"⚠ Cannot save pronunciation rules: {exc}")

    def reload_rules(self):
        try:
            self._rules = load_rules()
            self.rules_editor.setPlainText(render_rules(self._rules))
        except (OSError, ValueError) as exc:
            self.rules_status.setText(f"⚠ Cannot reload saved rules: {exc}")

    def update_generate_enabled(self):
        ready = bool(
            self._readiness is not None and self._readiness.ready
            and self.voice_selector.currentData()
            and self.voice_selector.currentData() in self._readiness.available_voices
        )
        try:
            valid_rules = bool(self.spoken_text().strip())
        except ValueError:
            valid_rules = False
        self.generate_button.setEnabled(
            ready and valid_rules and not self.is_generating
            and bool(self.script_editor.toPlainText().strip())
            and bool(self.output_dir.text().strip())
        )

    def browse_model(self):
        filename, _ = QFileDialog.getOpenFileName(
            self, "Select Kokoro ONNX model", self.model_path.text(),
            "ONNX models (*.onnx);;All files (*)"
        )
        if filename:
            self.model_path.setText(filename)
            self.scan()

    def browse_voices(self):
        filename, _ = QFileDialog.getOpenFileName(
            self, "Select Kokoro voices", self.voices_path.text(),
            "Kokoro voices (*.bin);;All files (*)"
        )
        if filename:
            self.voices_path.setText(filename)
            self.scan()

    def browse_output(self):
        folder = QFileDialog.getExistingDirectory(
            self, "Select Narration Output Folder",
            str(Path(self.output_dir.text()).expanduser())
        )
        if folder:
            self.output_dir.setText(folder)

    def save(self):
        status = self.scan()
        if not status.ready:
            QMessageBox.warning(self, "Kokoro not ready", "\n".join(status.problems))
            return
        prefs = self.current_prefs()
        try:
            path = save_preferences(prefs)
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, "Unable to save Kokoro settings", str(exc))
            return
        self._loaded_settings = prefs
        self.status_label.setText(f"✓ Settings saved to {path}. Kokoro ready.")

    def set_running(self, running: bool):
        self.generate_button.setEnabled(False)
        self.cancel_button.setEnabled(running)
        self.scan_button.setEnabled(not running)
        self.save_button.setEnabled(not running and bool(self._readiness and self._readiness.ready))
        self.model_path.setEnabled(not running)
        self.voices_path.setEnabled(not running)
        self.voice_selector.setEnabled(not running)
        self.language_selector.setEnabled(not running)
        self.speed_selector.setEnabled(not running)
        self.script_editor.setEnabled(not running)
        self.take_name.setEnabled(not running)
        self.output_dir.setEnabled(not running)
        self.rules_editor.setEnabled(not running)
        self.save_rules_button.setEnabled(not running)
        self.reset_rules_button.setEnabled(not running)
        if not running:
            self.update_generate_enabled()

    def generate(self):
        if self.is_generating:
            return
        status = self.scan()
        if not status.ready:
            QMessageBox.warning(self, "Kokoro not ready", "\n".join(status.problems))
            return
        try:
            spoken = self.spoken_text()
            job = prepare_job(
                self.script_editor.toPlainText(), self.take_name.text(),
                Path(self.output_dir.text()), self.current_prefs(), spoken_script=spoken
            )
        except (ValueError, OSError) as exc:
            QMessageBox.warning(self, "Cannot generate narration", str(exc))
            return

        self.job = job
        self._cancel_requested = False
        self.process = QProcess(self)
        self.process.setProgram(str(status.executable))
        self.process.setArguments(kokoro_arguments(job))
        self.process.setWorkingDirectory(str(job.work_dir))
        self.process.finished.connect(self._on_finished)
        self.process.errorOccurred.connect(self._on_error)
        self.generation_status.setText(
            f"Generating {job.stem} with {job.voice}… Existing audio will not be overwritten."
        )
        self.set_running(True)
        self.process.start()

    def _on_error(self, error):
        if error == QProcess.ProcessError.FailedToStart and self.job is not None:
            self._finish_failure("Kokoro could not be started. Check your CLI installation.")

    def _on_finished(self, exit_code: int, exit_status):
        if self.job is None:
            return
        if self._cancel_requested:
            self._finish_failure("Generation cancelled; no new audio was published.")
            return
        if exit_status != QProcess.ExitStatus.NormalExit or exit_code != 0:
            message = ""
            if self.process is not None:
                message = bytes(self.process.readAllStandardError()).decode(
                    "utf-8", errors="replace"
                ).strip()
            self._finish_failure(
                f"Kokoro exited with code {exit_code}. {message[-600:]}"
            )
            return
        try:
            published = publish_take(self.job)
        except (OSError, ValueError) as exc:
            self._finish_failure(f"Output validation failed: {exc}")
            return
        self.last_output = published
        self.play_button.setEnabled(True)
        self.player.stop()
        self.player.setSource(QUrl.fromLocalFile(str(published)))
        self.playback_status.setText(f"Ready: {published.name}")
        self.open_output_button.setEnabled(True)
        self.generation_status.setText(
            f"✓ WAV created: {published.name}. Script: {published.with_suffix('.txt').name}. "
            "Pronunciation-adjusted text remains visible in the Speech-ready preview. "
            f"Folder: {published.parent}"
        )
        self._end_job()

    def _finish_failure(self, message: str):
        self.generation_status.setText("✗ " + message)
        self._end_job()

    def _end_job(self):
        cleanup_job(self.job)
        self.job = None
        process = self.process
        self.process = None
        if process is not None:
            process.deleteLater()
        self.set_running(False)

    def cancel_generation(self):
        if self.process is not None and self.is_generating:
            self._cancel_requested = True
            self.generation_status.setText("Cancelling Kokoro generation…")
            self.process.kill()

    def stop_for_shutdown(self):
        if self.process is not None and self.is_generating:
            self._cancel_requested = True
            self.process.kill()
            self.process.waitForFinished(1500)
            if self.job is not None:
                self._finish_failure("Generation cancelled when closing the hub.")

    def play_last_take(self):
        if self.last_output is not None and self.last_output.is_file():
            self.player.setSource(QUrl.fromLocalFile(str(self.last_output)))
            self.player.play()
        else:
            self.playback_status.setText("Last generated WAV is missing.")

    def update_playback_controls(self, state):
        playing = state == QMediaPlayer.PlaybackState.PlayingState
        self.stop_button.setEnabled(playing)
        self.play_button.setEnabled(self.last_output is not None)

    def playback_error(self, error, message):
        self.playback_status.setText(f"Playback error: {message}")

    def open_output_folder(self):
        if self.last_output is None:
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.last_output.parent)))
