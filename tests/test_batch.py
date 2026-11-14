"""Batch section selection, explicit assignment, and Qt batch sequencing tests."""
from __future__ import annotations

import copy
import os
import sys
import tempfile
import unittest
import wave
import zipfile
from pathlib import Path
from unittest.mock import patch

from nanners_creator_hub.batch import (
    CompletedTake, assign_completed_takes, select_sections
)
from nanners_creator_hub.kokoro import default_preferences, inspect_kokoro
from nanners_creator_hub.projects import new_project
from nanners_creator_hub.sections import new_section


def make_audio(path: Path):
    with wave.open(str(path), "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(24000)
        audio.writeframes(b"\x00\x00" * 2400)


def project_fixture(folder: Path):
    project = new_project("Batch safety")
    one, two, three = [new_section(s) for s in ("Welcome", "Setup", "No Script")]
    one["script"] = "Welcome to NAnners Creator Hub."
    two["script"] = "Next, select Wineland eleven point zero."
    three["script"] = ""
    existing = folder / "existing.wav"
    make_audio(existing)
    two["narration_path"] = str(existing)
    project["sections"] = [one, two, three]
    return project


class AssignmentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.project = project_fixture(self.folder)
        self.one, self.two, _ = self.project["sections"]
        self.wav1 = self.folder / "new-welcome.wav"
        self.wav2 = self.folder / "new-setup.wav"
        make_audio(self.wav1)
        make_audio(self.wav2)
        self.selected = select_sections(self.project, [self.one["id"], self.two["id"]])
        self.takes = [CompletedTake(self.selected[0], self.wav1),
                      CompletedTake(self.selected[1], self.wav2)]

    def test_selection_skips_unselected_and_rejects_blank(self):
        self.assertEqual(len(select_sections(self.project, [self.one["id"]])), 1)
        with self.assertRaises(ValueError):
            select_sections(self.project, [self.project["sections"][2]["id"]])
        with self.assertRaises(ValueError):
            select_sections(self.project, ["missing-section"])

    def test_assignment_is_copy_and_marks_needs_review(self):
        original = copy.deepcopy(self.project)
        result = assign_completed_takes(self.project, self.takes, [self.one["id"]])
        self.assertEqual(self.project, original)
        self.assertEqual(result["sections"][0]["narration_path"], str(self.wav1))
        self.assertEqual(result["sections"][0]["status"], "needs_review")
        self.assertEqual(result["sections"][1]["narration_path"], str(self.folder / "existing.wav"))
        self.assertEqual(len(result["media"]), 1)
        self.assertEqual(result["media"][0]["kind"], "Audio")
        self.assertTrue(self.wav1.is_file())

    def test_existing_assignment_cannot_be_replaced_implicitly(self):
        before = copy.deepcopy(self.project)
        with self.assertRaisesRegex(ValueError, "Explicit replacement"):
            assign_completed_takes(self.project, self.takes, [self.one["id"], self.two["id"]])
        self.assertEqual(self.project, before)

    def test_explicit_replacement_preserves_original(self):
        before = (self.folder / "existing.wav").read_bytes()
        result = assign_completed_takes(
            self.project, self.takes, [self.two["id"]], allow_replace=True
        )
        self.assertEqual(result["sections"][1]["narration_path"], str(self.wav2))
        self.assertEqual((self.folder / "existing.wav").read_bytes(), before)

    def test_snapshot_changes_rejected(self):
        altered = copy.deepcopy(self.project)
        altered["sections"][0]["script"] = "Edited while Kokoro was running"
        with self.assertRaisesRegex(ValueError, "changed during generation"):
            assign_completed_takes(altered, self.takes, [self.one["id"]])

    def test_missing_wav_rejected_atomically(self):
        self.wav2.unlink()
        with self.assertRaises(ValueError):
            assign_completed_takes(self.project, self.takes,
                                   [self.one["id"], self.two["id"]], allow_replace=True)
        self.assertEqual(self.project["media"], [])


class BatchDialogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.project = project_fixture(self.folder)
        model = self.folder / "kokoro-v1.0.onnx"
        voices = self.folder / "voices-v1.0.bin"
        model.write_bytes(b"fake model")
        with zipfile.ZipFile(voices, "w") as archive:
            archive.writestr("em_alex.npy", b"voice")
        self.prefs = dict(default_preferences(), model_path=str(model),
                          voices_path=str(voices), voice="em_alex")
        self.executable = self.folder / "fake-kokoro"
        self.executable.write_text(
            f"#!{sys.executable}\n"
            "import sys, wave\n"
            "input_path, output_path = sys.argv[1:3]\n"
            "script = open(input_path, encoding='utf-8').read()\n"
            "assert 'NAnners' not in script and 'Wineland' not in script\n"
            "with wave.open(output_path, 'wb') as audio:\n"
            "    audio.setnchannels(1)\n"
            "    audio.setsampwidth(2)\n"
            "    audio.setframerate(24000)\n"
            "    audio.writeframes(b'\\x00\\x00' * 2400)\n",
        )
        self.executable.chmod(0o755)
        self.fake_inspect = lambda prefs: inspect_kokoro(
            prefs, executable=str(self.executable)
        )

    def build_dialog(self):
        from nanners_creator_hub.kokoro_studio import KokoroStudio
        from nanners_creator_hub.batch_dialog import BatchNarrationDialog
        with patch("nanners_creator_hub.kokoro_studio.load_preferences", return_value=self.prefs), patch(
            "nanners_creator_hub.kokoro_studio.inspect_kokoro", self.fake_inspect
        ), patch("nanners_creator_hub.batch_dialog.inspect_kokoro", self.fake_inspect):
            studio = KokoroStudio()
            studio.output_dir.setText(str(self.folder / "takes"))
            dialog = BatchNarrationDialog(self.project, studio)
        self.addCleanup(studio.close)
        self.addCleanup(dialog.close)
        return dialog

    def finish(self, dialog):
        from PySide6.QtCore import QEventLoop, QTimer
        loop = QEventLoop()
        timer = QTimer()
        timer.setInterval(10)
        def poll():
            if not dialog.running:
                loop.quit()
        timer.timeout.connect(poll)
        timer.start()
        guard = QTimer()
        guard.setSingleShot(True)
        guard.timeout.connect(loop.quit)
        guard.start(4000)
        if dialog.running:
            loop.exec()
        timer.stop()
        guard.stop()
        self.assertFalse(dialog.running, "Batch did not finish within 4 seconds")

    def test_defaults_skip_existing_and_empty(self):
        from PySide6.QtCore import Qt
        dialog = self.build_dialog()
        self.assertEqual(dialog.table.rowCount(), 3)
        self.assertEqual(dialog.selected_for_generation(), [self.project["sections"][0]["id"]])
        self.assertEqual(dialog.table.item(1, 0).checkState(), Qt.CheckState.Unchecked)
        self.assertEqual(dialog.table.item(2, 3).text(), "No script — unavailable")

    def test_confirm_rejects_missing_wav_without_closing(self):
        dialog = self.build_dialog()
        with patch("nanners_creator_hub.batch_dialog.inspect_kokoro", self.fake_inspect):
            dialog.start_batch()
        self.finish(dialog)
        self.assertEqual(len(dialog.completed), 1)
        new_wav = dialog.completed[0].wav_path
        new_wav.unlink()
        with patch("nanners_creator_hub.batch_dialog.QMessageBox.warning") as warning:
            dialog.review_and_accept()
        self.assertTrue(warning.called)
        self.assertEqual(dialog.selected_assignments, [])
        self.assertEqual(dialog.result(), 0)
        self.assertEqual(self.project["media"], [])

    def test_cancel_before_running_leaves_project_unmodified(self):
        dialog = self.build_dialog()
        before = copy.deepcopy(self.project)
        dialog.reject()
        self.assertEqual(dialog.completed, [])
        self.assertEqual(self.project, before)

    def test_two_takes_sequential_and_explicit_assignment(self):
        from PySide6.QtCore import Qt
        dialog = self.build_dialog()
        dialog.table.item(1, 0).setCheckState(Qt.CheckState.Checked)
        with patch("nanners_creator_hub.batch_dialog.inspect_kokoro", self.fake_inspect):
            dialog.start_batch()
        self.finish(dialog)
        self.assertEqual(len(dialog.completed), 2)
        self.assertEqual(len(dialog.failed), 0)
        self.assertEqual(dialog.selected_for_assignment(), [self.project["sections"][0]["id"]])
        self.assertEqual(dialog.table.item(1, 4).checkState(), Qt.CheckState.Unchecked)
        self.assertEqual(len(list((self.folder / "takes").glob("*.wav"))), 2)
        self.assertEqual(len(list((self.folder / "takes").glob("*.txt"))), 2)
        first = dialog.completed[0]
        self.assertEqual(first.wav_path.with_suffix(".txt").read_text(), "Welcome to NAnners Creator Hub.")
        self.assertFalse(any(p.name.endswith(".speech.txt") for p in (self.folder / "takes").iterdir()))
        dialog.review_and_accept()
        self.assertEqual(dialog.selected_assignments, [self.project["sections"][0]["id"]])
        self.assertFalse(dialog.replacement_approved)


if __name__ == "__main__":
    unittest.main()
