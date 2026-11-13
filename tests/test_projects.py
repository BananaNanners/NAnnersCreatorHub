import json
import tempfile
import unittest
from pathlib import Path

from nanners_creator_hub.projects import (
    load_project, new_project, save_project, validate_project,
)


class ProjectPersistenceTests(unittest.TestCase):
    def test_defaults_are_safe(self):
        project = new_project("Tutorial #2")
        self.assertEqual(project["editing_mode"], "assisted")
        self.assertTrue(project["preserve_originals"])
        self.assertTrue(project["section_markers"])
        self.assertFalse(project["transition_suggestions"])

    def test_reopen_roundtrip(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "tutorial.json"
            original = new_project("Witcher 3")
            save_project(target, original)
            self.assertEqual(load_project(target), original)
            self.assertEqual(list(Path(folder).glob("*.tmp")), [])

    def test_invalid_name_does_not_overwrite(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "tutorial.json"
            save_project(target, new_project("Safe"))
            original_contents = target.read_bytes()
            damaged = new_project("Other")
            damaged["name"] = " "
            with self.assertRaises(ValueError):
                save_project(target, damaged)
            self.assertEqual(target.read_bytes(), original_contents)

    def test_unknown_schema_is_rejected(self):
        project = new_project("Safe")
        project["schema_version"] = 999
        with self.assertRaises(ValueError):
            validate_project(project)

    def test_cannot_disable_original_preservation(self):
        project = new_project("Safe")
        project["preserve_originals"] = False
        with self.assertRaises(ValueError):
            validate_project(project)

    def test_no_media_path_writes(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "recording.mp4"
            source.write_bytes(b"example recording content")
            before = source.read_bytes()
            project = new_project("Safe")
            from nanners_creator_hub.sections import new_section
            section = new_section("Source preservation")
            section["footage_path"] = str(source)
            project["sections"] = [section]
            save_project(Path(folder) / "project.json", project)
            self.assertEqual(source.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
