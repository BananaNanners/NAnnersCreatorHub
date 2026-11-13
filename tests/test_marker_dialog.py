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


if __name__ == "__main__":
    unittest.main()
