import tempfile
import unittest
from pathlib import Path

from nanners_creator_hub.projects import new_project
from nanners_creator_hub.readiness import analyze_project, export_report, report_markdown
from nanners_creator_hub.sections import new_section


def complete_project():
    project = new_project("Creator Test")
    section = new_section("Steam Compatibility")
    section.update(
        script="Open Compatibility.",
        narration_path="/tmp/test-voice.wav",
        footage_path="/tmp/test-steam.mkv",
        footage_in_seconds=2.0,
        footage_out_seconds=10.0,
        status="confirmed",
    )
    project["sections"].append(section)
    project["media"] = [
        {"path": "/tmp/test-voice.wav", "kind": "Audio", "status": "ready",
         "duration_seconds": 8.0},
        {"path": "/tmp/test-steam.mkv", "kind": "Video", "status": "ready",
         "duration_seconds": 30.0},
    ]
    return project


class ReadinessTests(unittest.TestCase):
    def test_confirmed_complete_section_ready(self):
        report = analyze_project(complete_project())
        self.assertEqual(report["ready_count"], 1)
        self.assertEqual(report["sections"][0]["difference_seconds"], 0.0)

    def test_duration_mismatch_advisory(self):
        project = complete_project()
        project["sections"][0]["footage_out_seconds"] = 16.0
        report = analyze_project(project)
        self.assertEqual(report["review_count"], 1)
        self.assertAlmostEqual(report["sections"][0]["difference_seconds"], 6)
        self.assertTrue(any("timing differs" in msg for msg in report["sections"][0]["issues"]))

    def test_unconfirmed_requires_review(self):
        project = complete_project()
        project["sections"][0]["status"] = "needs_review"
        self.assertFalse(analyze_project(project)["sections"][0]["ready"])

    def test_no_script_requires_review(self):
        project = complete_project()
        project["sections"][0]["script"] = ""
        self.assertIn("Script text is missing", analyze_project(project)["sections"][0]["issues"])

    def test_missing_media_reference_requires_review(self):
        project = complete_project()
        project["media"] = []
        self.assertEqual(analyze_project(project)["review_count"], 1)

    def test_empty_project_report(self):
        text = report_markdown(new_project("Empty"))
        self.assertIn("No sections exist yet", text)
        self.assertIn("Sections: 0", text)

    def test_export_is_exclusive_and_preserves_existing_files(self):
        project = complete_project()
        with tempfile.TemporaryDirectory() as folder:
            report = Path(folder) / "readiness.md"
            media = Path(folder) / "source.mkv"
            media.write_bytes(b"unmodified source")
            export_report(report, project)
            self.assertIn("Steam Compatibility", report.read_text())
            with self.assertRaises(FileExistsError):
                export_report(report, project)
            self.assertEqual(media.read_bytes(), b"unmodified source")


if __name__ == "__main__":
    unittest.main()
