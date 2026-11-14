"""Pronunciation transformation is opt-in, reversible, and original-safe."""
import tempfile
import unittest
from pathlib import Path

from nanners_creator_hub.pronunciations import (
    DEFAULT_RULES, load_rules, parse_rules, render_rules, save_rules, speech_text,
)
from nanners_creator_hub.kokoro import default_preferences
from nanners_creator_hub.narration import cleanup_job, prepare_job


class PronunciationRulesTests(unittest.TestCase):
    def test_brand_name_and_wineland(self):
        original = "Welcome to NAnners Creator Hub. Next, select Wineland 11."
        spoken = speech_text(original, DEFAULT_RULES)
        self.assertEqual(spoken, "Welcome to Nanners Creator Hub. Next, select Wine land 11.")
        self.assertEqual(original, "Welcome to NAnners Creator Hub. Next, select Wineland 11.")

    def test_word_boundary_case_insensitive(self):
        self.assertEqual(
            speech_text("NAnners and nanners, not NAnnersVRhub.", DEFAULT_RULES),
            "Nanners and Nanners, not NAnnersVRhub."
        )

    def test_save_and_load_editable_rules(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "rules.json"
            rules = parse_rules("NAnners => Nanners\nWineland => Wine land")
            save_rules(rules, path)
            self.assertEqual(load_rules(path), rules)
            self.assertEqual(parse_rules(render_rules(rules)), rules)

    def test_invalid_rules_rejected(self):
        for content in ("NAnners = Nanners", "NAnners => ", "NAnners => Nanners\nnanners => Foo"):
            with self.subTest(content=content), self.assertRaises(ValueError):
                parse_rules(content)

    def test_original_and_speech_snapshot_separate(self):
        with tempfile.TemporaryDirectory() as directory:
            original = "Welcome to NAnners Creator Hub."
            spoken = speech_text(original, DEFAULT_RULES)
            job = prepare_job(original, "pronunciation", Path(directory), default_preferences(), spoken_script=spoken)
            try:
                self.assertEqual(job.original_script.read_text(), original)
                self.assertEqual(job.input_script.read_text(), "Welcome to Nanners Creator Hub.")
            finally:
                cleanup_job(job)


class PronunciationGuiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import os
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def test_speech_preview_and_playback_buttons(self):
        from nanners_creator_hub.kokoro_studio import KokoroStudio
        studio = KokoroStudio()
        studio.script_editor.setPlainText("NAnners and Wineland.")
        self.assertEqual(studio.speech_preview.toPlainText(), "Nanners and Wine land.")
        self.assertFalse(studio.play_button.isEnabled())
        self.assertFalse(studio.stop_button.isEnabled())
        studio.rules_editor.setPlainText("NAnners => BananaNanners")
        self.assertEqual(studio.speech_preview.toPlainText(), "BananaNanners and Wineland.")
        studio.rules_editor.setPlainText("this rule is invalid")
        self.assertFalse(studio.generate_button.isEnabled())
        studio.close()


if __name__ == "__main__":
    unittest.main()
