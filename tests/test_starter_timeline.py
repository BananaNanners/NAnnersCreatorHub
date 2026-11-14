"""Experimental Kdenlive starter project structure and non-destructive export."""
from __future__ import annotations

import copy
import json
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from nanners_creator_hub.projects import new_project
from nanners_creator_hub.sections import new_section
from nanners_creator_hub.starter_timeline import (
    StarterTimelineError, build_kdenlive_xml, export_starter_timeline, plan_timeline,
)


def props(node):
    return {
        child.get("name"): child.text
        for child in node.findall("property")
    }


class StarterTimelineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        folder = Path(self.tmp.name)
        video = folder / "example-video.mkv"
        wav = folder / "speech.wav"
        video.write_bytes(b"video bytes that must not be changed")
        wav.write_bytes(b"audio bytes that must not be changed")
        self.video, self.wav = video, wav
        self.project = new_project("Starter timeline test")
        self.project["media"] = [
            {"path": str(video), "kind": "Video + Audio", "status": "ready",
             "duration_seconds": 30.0, "width": 1920, "height": 1080},
            {"path": str(wav), "kind": "Audio", "status": "ready",
             "duration_seconds": 4.0},
        ]
        first = new_section("Welcome")
        first.update(
            status="confirmed", footage_path=str(video),
            narration_path=str(wav), footage_in_seconds=2, footage_out_seconds=7,
        )
        second = new_section("Not Reviewed")
        second["footage_path"] = str(video)
        self.project["sections"] = [first, second]

    def test_only_confirmed_sections_are_exported(self):
        plan = plan_timeline(self.project, "60")
        self.assertEqual(len(plan.clips), 1)
        self.assertEqual(plan.total_frames, 300)
        self.assertEqual(plan.clips[0].video_source_in, 120)
        self.assertEqual(plan.clips[0].video_source_out, 419)
        self.assertEqual(plan.clips[0].audio_source_out, 239)
        self.assertEqual(len(plan.skipped), 1)

    def test_two_clips_are_sequential_and_guides_match(self):
        second = self.project["sections"][1]
        second.update(status="confirmed", narration_path=str(self.wav),
                      footage_in_seconds=10, footage_out_seconds=15)
        plan = plan_timeline(self.project, "60")
        self.assertEqual(len(plan.clips), 2)
        self.assertEqual([c.timeline_in for c in plan.clips], [0, 300])
        self.assertEqual([c.timeline_out for c in plan.clips], [299, 599])
        xml = build_kdenlive_xml(plan, Path(self.tmp.name) / "new.kdenlive")
        root = ET.fromstring(xml)
        self.assertEqual(root.tag, "mlt")
        self.assertEqual(root.find("profile").get("frame_rate_num"), "60")
        video_entries = root.find("./playlist[@id='video_playlist']").findall("entry")
        audio_entries = root.find("./playlist[@id='narration_playlist']").findall("entry")
        self.assertEqual(len(video_entries), 2)
        self.assertEqual(len(audio_entries), 2)
        self.assertEqual([a.get("in") for a in video_entries], ["120", "600"])
        self.assertTrue(root.find("./playlist[@id='narration_playlist']").findall("blank"))
        seq = next(x for x in root.findall("tractor") if "kdenlive:uuid" in props(x))
        guides = json.loads(props(seq)["kdenlive:sequenceproperties.guides"])
        self.assertEqual([x["pos"] for x in guides], [0, 300])
        self.assertEqual(len(root.findall("./playlist[@id='main_bin']/entry")), 3)
        self.assertIn("kdenlive:projectTractor", props(root.findall("tractor")[-1]))

    def test_unconfirmed_only_is_blocked(self):
        for section in self.project["sections"]:
            section["status"] = "needs_review"
        with self.assertRaisesRegex(StarterTimelineError, "No confirmed sections"):
            plan_timeline(self.project)

    def test_invalid_inputs_are_rejected(self):
        with self.assertRaises(StarterTimelineError):
            plan_timeline(self.project, "unknown")
        self.project["sections"][0]["footage_out_seconds"] = 31
        with self.assertRaises(StarterTimelineError):
            plan_timeline(self.project)

    def test_narration_longer_than_footage_warns_and_trims(self):
        self.project["sections"][0]["footage_out_seconds"] = 3
        plan = plan_timeline(self.project, "60")
        self.assertTrue(plan.clips[0].narration_truncated)
        self.assertEqual(plan.clips[0].audio_source_out, 59)

    def test_new_export_exclusive_and_original_files_untouched(self):
        old = copy.deepcopy(self.project)
        old_video, old_wav = self.video.read_bytes(), self.wav.read_bytes()
        target = Path(self.tmp.name) / "new-starter.kdenlive"
        plan = export_starter_timeline(target, self.project)
        self.assertEqual(len(plan.clips), 1)
        self.assertTrue(target.is_file())
        content = target.read_bytes()
        with self.assertRaises(FileExistsError):
            export_starter_timeline(target, self.project)
        self.assertEqual(target.read_bytes(), content)
        self.assertEqual(self.project, old)
        self.assertEqual(self.video.read_bytes(), old_video)
        self.assertEqual(self.wav.read_bytes(), old_wav)

    def test_reject_wrong_extension_and_missing_file(self):
        with self.assertRaises(StarterTimelineError):
            export_starter_timeline(Path(self.tmp.name)/"bad.xml", self.project)
        self.video.unlink()
        with self.assertRaisesRegex(StarterTimelineError, "missing"):
            plan_timeline(self.project)


class StarterDialogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import os
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def test_dialog_blocks_unconfirmed_and_shows_sections(self):
        from nanners_creator_hub.starter_dialog import StarterTimelineDialog
        project = new_project("Unconfirmed")
        project["sections"].append(new_section("Draft"))
        dialog = StarterTimelineDialog(project, Path("/tmp"))
        self.assertFalse(dialog.export_button.isEnabled())
        self.assertIn("No confirmed sections", dialog.preview.toPlainText())
        dialog.close()


if __name__ == "__main__":
    unittest.main()
