"""Thumbnail sampling and read-only browse-to-preview behavior."""
from __future__ import annotations

import copy
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from nanners_creator_hub.thumbnails import (
    thumbnail_args, thumbnail_times, timestamp_label, video_entries,
)


class ThumbnailMathTests(unittest.TestCase):
    def test_evenly_spaced_and_bounded(self):
        stamps = thumbnail_times(52.433)
        self.assertEqual(len(stamps), 12)
        self.assertEqual(stamps[0], 0.5)
        self.assertLess(stamps[-1], 52.433)
        self.assertTrue(all(a <= b for a, b in zip(stamps, stamps[1:])))

    def test_short_video(self):
        stamps = thumbnail_times(0.5)
        self.assertEqual(len(stamps), 12)
        self.assertGreaterEqual(stamps[0], 0)
        self.assertLessEqual(stamps[-1], .5)

    def test_invalid_duration_and_count(self):
        for length in (0, -1, float("nan"), float("inf")):
            with self.subTest(length=length), self.assertRaises(ValueError):
                thumbnail_times(length)
        for count in (0, 13):
            with self.assertRaises(ValueError):
                thumbnail_times(10, count)

    def test_ffmpeg_is_stdout_only(self):
        args = thumbnail_args(Path("/tmp/clip.mkv"), 3.5)
        self.assertEqual(args[-1], "pipe:1")
        self.assertIn("-frames:v", args)
        self.assertIn("-nostdin", args)
        self.assertEqual(args[args.index("-i") + 1], "/tmp/clip.mkv")

    def test_filters_only_video(self):
        sample = [
            {"kind": "Video + Audio", "path": "/tmp/one.mp4"},
            {"kind": "Audio", "path": "/tmp/a.wav"},
            {"kind": "Video", "path": "/tmp/two.mkv"},
        ]
        self.assertEqual(len(video_entries(sample)), 2)
        self.assertEqual(timestamp_label(90), "01:30")


class ThumbnailGuiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.video = self.folder / "fake-footage.mkv"
        self.video.write_bytes(b"original file - unchanged")
        self.other = self.folder / "second-footage.mkv"
        self.other.write_bytes(b"other file")
        self.media = [
            {"path": str(self.video), "name": "Intro footage",
             "kind": "Video + Audio", "duration_seconds": 24.0},
            {"path": str(self.other), "name": "Other footage",
             "kind": "Video", "duration_seconds": 30.0},
        ]

    def test_browser_initialization_and_no_files_created(self):
        from nanners_creator_hub.thumbnail_browser import ThumbnailBrowserDialog
        from PySide6.QtCore import QProcess
        with patch.object(QProcess, "start", autospec=True):
            dlg = ThumbnailBrowserDialog(self.media, str(self.other))
            self.assertEqual(dlg.source_selector.count(), 2)
            self.assertEqual(dlg.source_selector.currentData(), str(self.other))
            self.assertEqual(len(dlg._times), 12)
            self.assertIsNone(dlg.selected_source)
            self.assertIsNone(dlg.selected_seconds)
            dlg.reject()
            self.assertTrue(dlg._closed)
            dlg._launch_next()
            self.assertIsNone(dlg._process)
        self.assertEqual(self.video.read_bytes(), b"original file - unchanged")
        self.assertEqual(self.other.read_bytes(), b"other file")
        self.assertEqual(sorted(p.name for p in self.folder.iterdir()),
                         ["fake-footage.mkv", "second-footage.mkv"])

    def test_browser_requires_video(self):
        from nanners_creator_hub.thumbnail_browser import ThumbnailBrowserDialog
        with self.assertRaises(ValueError):
            ThumbnailBrowserDialog([{"kind": "Audio", "path": "x.wav"}])

    def test_preview_starts_at_thumbnail_timestamp(self):
        from PySide6.QtMultimedia import QMediaPlayer
        from nanners_creator_hub.footage_preview import FootagePreviewDialog
        with patch.object(QMediaPlayer, "setSource", autospec=True):
            dialog = FootagePreviewDialog(
                self.video, 24.0, 0, 0,
                seek_seconds=9.5, allow_apply=False
            )
            self.assertEqual(dialog._pending_seek_ms, 9500)
            self.assertFalse(dialog.apply_button.isEnabled())
            self.assertIsNone(dialog.applied_range)
            dialog.reject()


if __name__ == "__main__":
    unittest.main()
