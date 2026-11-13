import json
import tempfile
import unittest
from pathlib import Path

from nanners_creator_hub.markers import MarkerPlanError, export_markers, marker_plan
from nanners_creator_hub.projects import new_project
from nanners_creator_hub.sections import new_section


def sample_project(lengths=(4.224, 8.0)):
    project = new_project("Tutorial")
    for i, duration in enumerate(lengths):
        video_path = f"/tmp/video-{i}.mkv"
        audio_path = f"/tmp/audio-{i}.wav"
        section = new_section(f"Section {i+1}")
        section.update({
            "footage_path": video_path,
            "narration_path": audio_path,
            "footage_in_seconds": 1.0,
            "footage_out_seconds": 1.0 + duration,
        })
        project["sections"].append(section)
        project["media"].extend([
            {"path": video_path, "kind": "Video", "status": "ready",
             "duration_seconds": 100.0},
            {"path": audio_path, "kind": "Audio", "status": "ready",
             "duration_seconds": duration},
        ])
    return project


class MarkerTests(unittest.TestCase):
    def test_frame_indices_at_30(self):
        plan = marker_plan(sample_project(), "30", "footage")
        self.assertEqual([marker["pos"] for marker in plan], [0, 127])
        self.assertEqual(plan[0]["type"], 0)

    def test_fractional_fps_uses_rational(self):
        plan = marker_plan(sample_project(), "29.97 (30000/1001)", "footage")
        self.assertEqual([marker["pos"] for marker in plan], [0, 127])

    def test_starting_frame_offset(self):
        plan = marker_plan(sample_project(), "25", "narration", starting_frame=50)
        self.assertEqual([marker["pos"] for marker in plan], [50, 156])

    def test_missing_footage_blocks_footage_export(self):
        project = sample_project()
        project["sections"][0]["footage_path"] = ""
        with self.assertRaises(MarkerPlanError):
            marker_plan(project, "30", "footage")

    def test_invalid_out_point_blocks_export(self):
        project = sample_project()
        project["sections"][0]["footage_out_seconds"] = 150.0
        with self.assertRaises(MarkerPlanError):
            marker_plan(project, "30", "footage")

    def test_unavailable_narration_blocks_export(self):
        project = sample_project()
        project["media"][1]["duration_seconds"] = None
        with self.assertRaises(MarkerPlanError):
            marker_plan(project, "30", "narration")

    def test_empty_sections_and_invalid_fps_block(self):
        with self.assertRaises(MarkerPlanError):
            marker_plan(new_project("Empty"))
        with self.assertRaises(MarkerPlanError):
            marker_plan(sample_project(), "999")

    def test_duplicate_frames_rejected(self):
        project = sample_project(lengths=(0.001, 5.0, 5.0))
        with self.assertRaises(MarkerPlanError):
            marker_plan(project, "30", "footage")

    def test_export_json_non_overwrite(self):
        project = sample_project()
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "markers.json"
            result = export_markers(target, project)
            self.assertEqual(json.loads(target.read_text()), result)
            before = target.read_bytes()
            with self.assertRaises(FileExistsError):
                export_markers(target, project)
            self.assertEqual(before, target.read_bytes())

    def test_source_media_never_written(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            file = root / "recording.mkv"
            file.write_bytes(b"original media")
            project = sample_project((2.0,))
            project["sections"][0]["footage_path"] = str(file)
            project["media"][0]["path"] = str(file)
            export_markers(root / "markers.json", project)
            self.assertEqual(file.read_bytes(), b"original media")


if __name__ == "__main__":
    unittest.main()
