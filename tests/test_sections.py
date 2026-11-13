import tempfile
import unittest
from pathlib import Path

from nanners_creator_hub.projects import load_project, new_project, save_project
from nanners_creator_hub.sections import (
    footage_duration, new_section, section_warnings, suggest_footage,
)


class SectionTests(unittest.TestCase):
    def test_new_section_defaults(self):
        section = new_section("Compatibility")
        self.assertEqual(section["status"], "draft")
        self.assertEqual(section["footage_in_seconds"], 0)
        self.assertEqual(section["footage_out_seconds"], 0)

    def test_sections_survive_save_load(self):
        with tempfile.TemporaryDirectory() as folder:
            project = new_project("Tutorial")
            section = new_section("Introduction")
            section["script"] = "Start the game."
            section["footage_in_seconds"] = 2
            section["footage_out_seconds"] = 12
            section["status"] = "needs_review"
            project["sections"].append(section)
            output = Path(folder) / "project.json"
            save_project(output, project)
            self.assertEqual(load_project(output)["sections"], [section])

    def test_out_before_in_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            project = new_project("Tutorial")
            section = new_section("Bad range")
            section["footage_in_seconds"] = 15
            section["footage_out_seconds"] = 5
            project["sections"].append(section)
            with self.assertRaises(ValueError):
                save_project(Path(folder) / "project.json", project)

    def test_duplicate_id_rejected(self):
        project = new_project("Tutorial")
        section = new_section("First")
        project["sections"] = [section, dict(section)]
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(ValueError):
                save_project(Path(folder) / "project.json", project)

    def test_missing_assignments_warn(self):
        warnings = section_warnings(new_section("Intro"), [])
        self.assertIn("No narration assigned", warnings)
        self.assertIn("No footage assigned", warnings)

    def test_out_of_bounds_and_timing_warn(self):
        section = new_section("Demo")
        section.update(
            narration_path="/tmp/n.wav", footage_path="/tmp/v.mkv",
            footage_in_seconds=0, footage_out_seconds=12,
        )
        media = [
            {"path": "/tmp/n.wav", "status": "ready", "duration_seconds": 3},
            {"path": "/tmp/v.mkv", "status": "ready", "duration_seconds": 10},
        ]
        notes = section_warnings(section, media)
        self.assertTrue(any("exceeds" in n for n in notes))
        self.assertTrue(any("timing differs" in n for n in notes))
        self.assertEqual(footage_duration(section), 12)

    def test_suggestion_uses_filename_only(self):
        media = [
            {"path": "/tmp/steam-compatibility.mkv", "name": "steam-compatibility.mkv",
             "kind": "Video", "status": "ready"},
            {"path": "/tmp/unrelated.mp4", "name": "unrelated.mp4",
             "kind": "Video", "status": "ready"},
        ]
        self.assertEqual(
            suggest_footage("Steam Compatibility", media)["path"],
            "/tmp/steam-compatibility.mkv",
        )

    def test_no_match_without_relevant_filename(self):
        media = [
            {"path": "/tmp/2026-11-13.mkv", "name": "2026-11-13.mkv",
             "kind": "Video", "status": "ready"},
        ]
        self.assertIsNone(suggest_footage("Steam Compatibility", media))


if __name__ == "__main__":
    unittest.main()
