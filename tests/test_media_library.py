"""Removal only unlinks references and never deletes source media."""
import copy
import tempfile
import unittest
from pathlib import Path

from nanners_creator_hub.media_library import remove_media_references
from nanners_creator_hub.projects import new_project
from nanners_creator_hub.sections import new_section


class MediaReferenceRemovalTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name)
        self.video = self.folder / "incorrect-footage.mkv"
        self.audio = self.folder / "existing-narration.wav"
        self.video.write_bytes(b"Original video must survive")
        self.audio.write_bytes(b"Original audio must survive")
        self.project = new_project("Safe media cleanup")
        self.project["media"] = [
            {"path": str(self.video), "kind": "Video", "status": "ready"},
            {"path": str(self.audio), "kind": "Audio", "status": "ready"},
        ]
        section = new_section("Welcome")
        section.update(
            narration_path=str(self.audio), footage_path=str(self.video),
            footage_in_seconds=2.0, footage_out_seconds=8.0, status="confirmed",
        )
        self.project["sections"].append(section)

    def test_remove_footage_resets_in_out_and_requires_review(self):
        before = copy.deepcopy(self.project)
        result, affected = remove_media_references(self.project, [str(self.video)])
        self.assertEqual(self.project, before)
        self.assertEqual(len(result["media"]), 1)
        section = result["sections"][0]
        self.assertEqual(section["footage_path"], "")
        self.assertEqual(section["footage_in_seconds"], 0)
        self.assertEqual(section["footage_out_seconds"], 0)
        self.assertEqual(section["narration_path"], str(self.audio))
        self.assertEqual(section["status"], "needs_review")
        self.assertEqual(len(affected), 1)
        self.assertEqual(self.video.read_bytes(), b"Original video must survive")

    def test_remove_narration_preserves_footage(self):
        result, affected = remove_media_references(self.project, [str(self.audio)])
        section = result["sections"][0]
        self.assertEqual(section["narration_path"], "")
        self.assertEqual(section["footage_path"], str(self.video))
        self.assertEqual(section["footage_in_seconds"], 2)
        self.assertEqual(len(affected), 1)
        self.assertEqual(self.audio.read_bytes(), b"Original audio must survive")

    def test_multi_remove_and_ignore_unrelated_sections(self):
        second = new_section("Other")
        self.project["sections"].append(second)
        result, affected = remove_media_references(
            self.project, [str(self.video), str(self.audio)]
        )
        self.assertEqual(result["media"], [])
        self.assertEqual(len(affected), 1)
        self.assertEqual(result["sections"][1], second)
        self.assertTrue(self.video.exists() and self.audio.exists())

    def test_invalid_selection_never_changes_project(self):
        before = copy.deepcopy(self.project)
        for paths in ([], ["missing"], [str(self.video), str(self.video)]):
            with self.subTest(paths=paths), self.assertRaises(ValueError):
                remove_media_references(self.project, paths)
        self.assertEqual(self.project, before)


class RemovalGuiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import os
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name)
        self.video = self.folder / "incorrect-footage.mkv"
        self.video.write_bytes(b"never delete")
        self.project = new_project("UI removal")
        self.project["media"].append({
            "path": str(self.video), "kind": "Video", "status": "ready"
        })
        section = new_section("First")
        section["footage_path"] = str(self.video)
        section["footage_in_seconds"] = 1
        section["footage_out_seconds"] = 4
        self.project["sections"].append(section)

    def test_confirmation_and_project_dirty(self):
        from unittest.mock import patch
        from PySide6.QtWidgets import QMessageBox
        from nanners_creator_hub.app import MainWindow
        window = MainWindow()
        window.set_project(self.project, None)
        self.assertFalse(window.remove_media_button.isEnabled())
        window.media_table.selectRow(0)
        self.assertTrue(window.remove_media_button.isEnabled())
        with patch.object(QMessageBox, "question",
                          return_value=QMessageBox.StandardButton.No):
            window.remove_selected_media()
        self.assertEqual(len(window.project["media"]), 1)
        self.assertFalse(window.dirty)
        with patch.object(QMessageBox, "question",
                          return_value=QMessageBox.StandardButton.Yes):
            window.remove_selected_media()
        self.assertEqual(window.project["media"], [])
        self.assertEqual(window.project["sections"][0]["footage_path"], "")
        self.assertTrue(window.dirty)
        self.assertTrue(self.video.exists())
        with patch.object(QMessageBox, "question",
                          return_value=QMessageBox.StandardButton.Discard):
            window.close()


if __name__ == "__main__":
    unittest.main()
