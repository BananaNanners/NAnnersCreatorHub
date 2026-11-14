"""Footage playback UI and source range application safeguards."""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from nanners_creator_hub.footage_preview import format_position, validate_preview_range
from nanners_creator_hub.projects import new_project
from nanners_creator_hub.sections import new_section


class PreviewRangeTests(unittest.TestCase):
    def test_format_position(self):
        self.assertEqual(format_position(81000), "00:01:21")
        self.assertEqual(format_position(-1), "00:00:00")

    def test_range_validation(self):
        self.assertEqual(validate_preview_range(1.25, 4.5, 8), (1.25, 4.5))
        for args in ((4, 2, 10), (1, 1, 10), (-1, 1, 10), (1, 12, 10)):
            with self.subTest(args=args), self.assertRaises(ValueError):
                validate_preview_range(*args)


class PreviewGuiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.video = Path(self.tmp.name) / "test-video.mkv"
        self.video.write_bytes(b"mock video data - must not change")
        self.original = self.video.read_bytes()
        self.project = new_project("Video preview")
        section = new_section("Intro")
        section["footage_path"] = str(self.video)
        section["footage_in_seconds"] = 1.0
        section["footage_out_seconds"] = 4.0
        self.project["media"] = [{
            "path": str(self.video), "kind": "Video",
            "name": self.video.name, "status": "ready",
            "duration_seconds": 12.0,
        }]
        self.project["sections"] = [section]

    def test_preview_reject_keeps_range_and_source(self):
        from nanners_creator_hub.footage_preview import FootagePreviewDialog
        dialog = FootagePreviewDialog(self.video, 12.0, 1.0, 4.0)
        self.assertEqual(dialog.start_spin.value(), 1)
        self.assertEqual(dialog.end_spin.value(), 4)
        dialog.start_spin.setValue(2)
        dialog.reject()
        self.assertIsNone(dialog.applied_range)
        self.assertEqual(self.video.read_bytes(), self.original)

    def test_dialog_valid_and_invalid_apply(self):
        from nanners_creator_hub.footage_preview import FootagePreviewDialog
        dialog = FootagePreviewDialog(self.video, 12, 1, 4)
        dialog.start_spin.setValue(8)
        dialog.end_spin.setValue(2)
        dialog.apply_range()
        self.assertIsNone(dialog.applied_range)
        dialog.start_spin.setValue(2)
        dialog.end_spin.setValue(7.5)
        dialog.apply_range()
        self.assertEqual(dialog.applied_range, (2, 7.5))
        self.assertEqual(self.video.read_bytes(), self.original)

    def test_main_window_only_applies_confirmed_range(self):
        from nanners_creator_hub.app import MainWindow
        from nanners_creator_hub.footage_preview import FootagePreviewDialog
        window = MainWindow()
        window.set_project(self.project, None)
        self.assertFalse(window.dirty)
        with patch.object(FootagePreviewDialog, "exec", return_value=FootagePreviewDialog.DialogCode.Rejected):
            window.preview_footage_range()
        self.assertFalse(window.dirty)
        self.assertEqual(window.selected_section()["footage_in_seconds"], 1)
        def approve(dialog):
            dialog.applied_range = (2.5, 8.0)
            return FootagePreviewDialog.DialogCode.Accepted
        with patch.object(FootagePreviewDialog, "exec", approve):
            window.preview_footage_range()
        self.assertTrue(window.dirty)
        self.assertEqual(window.selected_section()["footage_in_seconds"], 2.5)
        self.assertEqual(window.selected_section()["footage_out_seconds"], 8.0)
        self.assertIn("UNSAVED CHANGES", window.save_state_label.text())
        self.assertEqual(self.video.read_bytes(), self.original)
        from PySide6.QtWidgets import QMessageBox
        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Discard):
            window.close()

    def test_missing_video_refuses_dialog(self):
        from nanners_creator_hub.footage_preview import FootagePreviewDialog
        with self.assertRaises(FileNotFoundError):
            FootagePreviewDialog(Path(self.tmp.name) / "missing.mkv")


if __name__ == "__main__":
    unittest.main()
