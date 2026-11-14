"""Safe Kokoro discovery, preferences, and dev1 GUI checks."""
import os
import tempfile
import unittest
import zipfile
from pathlib import Path

from nanners_creator_hub.kokoro import (
    default_preferences, discover_voices, inspect_kokoro, load_preferences,
    save_preferences,
)


class KokoroDiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.model = self.folder / "kokoro-v1.0.onnx"
        self.voices = self.folder / "voices-v1.0.bin"
        self.exe = self.folder / "kokoro-tts"
        self.model.write_bytes(b"example model metadata")
        self.exe.write_text("#!/bin/sh\nexit 0\n")
        with zipfile.ZipFile(self.voices, "w") as archive:
            archive.writestr("em_alex.npy", b"fake bytes")
            archive.writestr("af_sarah.npy", b"fake bytes")
            archive.writestr("../ignore.npy", b"not a voice")
        self.prefs = dict(default_preferences())
        self.prefs.update(model_path=str(self.model), voices_path=str(self.voices), voice="em_alex")

    def test_discover_voices_without_loading_tensor(self):
        self.assertEqual(discover_voices(self.voices), ("af_sarah", "em_alex"))

    def test_ready_configuration(self):
        status = inspect_kokoro(self.prefs, executable=str(self.exe))
        self.assertTrue(status.ready, status.problems)
        self.assertIn("em_alex", status.available_voices)

    def test_missing_model(self):
        self.model.unlink()
        status = inspect_kokoro(self.prefs, executable=str(self.exe))
        self.assertFalse(status.ready)
        self.assertTrue(any("model" in issue.lower() for issue in status.problems))

    def test_missing_voice(self):
        self.voices.unlink()
        self.assertFalse(inspect_kokoro(self.prefs, executable=str(self.exe)).ready)

    def test_voice_not_in_archive(self):
        self.prefs["voice"] = "em_santa"
        status = inspect_kokoro(self.prefs, executable=str(self.exe))
        self.assertFalse(status.ready)
        self.assertTrue(any("em_santa" in issue for issue in status.problems))

    def test_corrupt_voice_archive(self):
        self.voices.write_bytes(b"invalid zip")
        self.assertFalse(inspect_kokoro(self.prefs, executable=str(self.exe)).ready)

    def test_preference_roundtrip_does_not_touch_model(self):
        model_bytes = self.model.read_bytes()
        voices_bytes = self.voices.read_bytes()
        target = self.folder / "config" / "kokoro.json"
        save_preferences(self.prefs, target)
        loaded = load_preferences(target)
        self.assertEqual(loaded["voice"], "em_alex")
        self.assertEqual(loaded["model_path"], str(self.model))
        self.assertEqual(self.model.read_bytes(), model_bytes)
        self.assertEqual(self.voices.read_bytes(), voices_bytes)

    def test_rejects_bad_speed_and_language(self):
        self.prefs["speed"] = 4
        with self.assertRaises(ValueError):
            save_preferences(self.prefs, self.folder / "bad.json")
        self.prefs["speed"] = 1.0
        self.prefs["language"] = "nonexistent"
        with self.assertRaises(ValueError):
            save_preferences(self.prefs, self.folder / "bad.json")

    def test_default_voice(self):
        self.assertEqual(default_preferences()["voice"], "em_alex")


class KokoroGuiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def test_narration_tab_present_and_generation_disabled(self):
        from nanners_creator_hub.app import MainWindow
        window = MainWindow()
        self.assertEqual(window.tabs.count(), 2)
        self.assertIn("Kokoro Narration Studio", window.tabs.tabText(1))
        self.assertFalse(window.kokoro_studio.generate_button.isEnabled())
        window.close()


if __name__ == "__main__":
    unittest.main()
