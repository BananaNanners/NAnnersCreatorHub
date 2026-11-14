"""Persistent save-state banner should never be hidden by operation messages."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from nanners_creator_hub.projects import new_project
from nanners_creator_hub.sections import new_section


class SaveStateUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import os
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        from nanners_creator_hub.app import MainWindow
        self.window = MainWindow()


    def test_no_project_and_new_project_state(self):
        self.assertEqual(self.window.save_state_label.text(), "NO PROJECT OPEN")
        self.window.create_project()
        self.assertTrue(self.window.dirty)
        self.assertIn("UNSAVED CHANGES", self.window.save_state_label.text())
        self.assertIn("UNSAVED", self.window.windowTitle())

    def test_batch_assignment_status_and_save_state_independent(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "test.json"
            project = new_project("Tutorial")
            project["sections"].append(new_section("Intro"))
            self.window.set_project(project, path)
            self.assertEqual(self.window.save_state_label.text(), "SAVED")
            self.window.status_label.setText("Assigned 2 new narration references")
            self.window.mark_dirty()
            self.assertEqual(
                self.window.status_label.text(), "Assigned 2 new narration references"
            )
            self.assertEqual(
                self.window.save_state_label.text(),
                "UNSAVED CHANGES — Save Project",
            )
            self.window.save_current()
            self.assertEqual(self.window.save_state_label.text(), "SAVED")
            self.assertTrue(self.window.status_label.text().startswith("Saved:"))
            self.assertNotIn("UNSAVED", self.window.windowTitle())
            self.assertTrue(path.is_file())

    def test_other_actions_do_not_remove_unsaved_warning(self):
        self.window.set_project(new_project("New"), None)
        self.window.mark_dirty()
        self.window.status_label.setText("Report exported")
        self.assertEqual(
            self.window.save_state_label.text(), "UNSAVED CHANGES — Save Project"
        )
        self.window.mark_clean()
        self.assertEqual(self.window.save_state_label.text(), "NOT SAVED — Save Project")

    def tearDown(self):
        if self.window.dirty:
            from PySide6.QtWidgets import QMessageBox
            with patch.object(
                QMessageBox, "question", return_value=QMessageBox.StandardButton.Discard
            ):
                self.window.close()


if __name__ == "__main__":
    unittest.main()
