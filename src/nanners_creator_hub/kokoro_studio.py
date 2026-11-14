"""Kokoro Narration Studio — dev1 settings and readiness only."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QComboBox, QDoubleSpinBox, QFileDialog, QFormLayout, QHBoxLayout,
    QLabel, QLineEdit, QMessageBox, QPushButton, QTextEdit, QVBoxLayout,
    QWidget,
)

from .kokoro import (
    LANGUAGES, KokoroStatus, inspect_kokoro, load_preferences, save_preferences,
    default_preferences,
)


class KokoroStudio(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("kokoroNarrationStudio")
        self._loaded_settings = default_preferences()
        layout = QVBoxLayout(self)
        title = QLabel("Kokoro Narration Studio")
        title.setStyleSheet("font-size: 20px; font-weight: 700;")
        layout.addWidget(title)
        explanation = QLabel(
            "dev1: Discover local Kokoro models and voices, choose your defaults, and "
            "verify readiness. Script editing, speech generation and WAV previews arrive in dev2."
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

        self.generate_button = QPushButton("Generate WAV — coming in dev2")
        self.generate_button.setEnabled(False)
        layout.addWidget(self.generate_button)

        self._initial_load()
        self.model_path.editingFinished.connect(self.scan)
        self.voices_path.editingFinished.connect(self.scan)

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
            f"✓ Kokoro ready — {len(status.available_voices)} voices detected. "
            "No audio will be created in dev1."
            if status.ready
            else "Needs review: " + "; ".join(status.problems)
        )
        self.save_button.setEnabled(bool(status.available_voices) and status.ready)
        return status

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
