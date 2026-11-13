import tempfile
import unittest
from pathlib import Path

from nanners_creator_hub.marker_dialog import detected_kdenlive_fps


class KdenlivePreferenceTests(unittest.TestCase):
    def test_60fps_saved_preference(self):
        with tempfile.TemporaryDirectory() as folder:
            config = Path(folder) / "kdenliverc"
            config.write_text("[unmanaged]\nproject_fps=60\n")
            self.assertEqual(detected_kdenlive_fps(config), "60")

    def test_missing_preference_falls_back(self):
        self.assertIsNone(detected_kdenlive_fps(Path("/tmp/nanners-nonexistent-config-987")))

    def test_fps_2997_alias(self):
        with tempfile.TemporaryDirectory() as folder:
            config = Path(folder) / "kdenliverc"
            config.write_text("[unmanaged]\nproject_fps=29.97\n")
            self.assertEqual(detected_kdenlive_fps(config), "29.97 (30000/1001)")


class BannerVisibilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import os
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def test_mismatch_banner_toggles(self):
        from nanners_creator_hub.marker_dialog import MarkerExportDialog
        from nanners_creator_hub.projects import new_project
        dialog = MarkerExportDialog(new_project("Banner test"), Path("/tmp"))
        dialog.kdenlive_fps_preference = "60"
        dialog.fps_box.setCurrentText("30")
        dialog.show()
        self.app.processEvents()
        self.assertTrue(dialog.warning_banner.isVisible())
        self.assertIn("FRAME-RATE MISMATCH", dialog.warning_label.text())
        dialog.fps_box.setCurrentText("60")
        self.app.processEvents()
        self.assertFalse(dialog.warning_banner.isVisible())
        dialog.close()

    def test_blocking_error_banner_visible(self):
        from nanners_creator_hub.marker_dialog import MarkerExportDialog
        from nanners_creator_hub.projects import new_project
        dialog = MarkerExportDialog(new_project("Empty project"), Path("/tmp"))
        dialog.show()
        self.app.processEvents()
        self.assertTrue(dialog.error_banner.isVisible())
        self.assertFalse(dialog.export_button.isEnabled())
        dialog.close()


if __name__ == "__main__":
    unittest.main()
