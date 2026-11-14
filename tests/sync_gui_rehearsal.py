"""Narration alignment calculations, waveform extraction, and GUI safeguards."""
from __future__ import annotations

import os
import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import patch

from nanners_creator_hub.waveform import (
    ffmpeg_waveform_args, peaks_from_pcm, suggested_out_point, validate_sync_range
)
from nanners_creator_hub.projects import new_project
from nanners_creator_hub.sections import new_section


class WaveformMathTests(unittest.TestCase):
    def test_peak_normalization(self):
        import struct
        samples = struct.pack("<8h", 0, 1000, -32768, 200, 0, 12000, -32000, 3)
        bins = peaks_from_pcm(samples, bins=2)
        self.assertEqual(len(bins), 2)
        self.assertAlmostEqual(bins[0], 1.0)
        self.assertGreater(bins[1], 0.9)

    def test_rejects_invalid_waveform_data(self):
        for data in (b"", b"x"):
            with self.assertRaises(ValueError):
                peaks_from_pcm(data)
        with self.assertRaises(ValueError):
            peaks_from_pcm(b"\x00\x00", bins=0)

    def test_ffmpeg_args_do_not_modify_input(self):
        args = ffmpeg_waveform_args(Path("/tmp/example.wav"))
        self.assertIn("-nostdin", args)
        self.assertIn("-vn", args)
        self.assertEqual(args[-1], "pipe:1")
        self.assertEqual(args[args.index("-i") + 1], "/tmp/example.wav")

    def test_timing_difference_and_proposal(self):
        item = validate_sync_range(2.5, 10, 20, 6.0)
        self.assertEqual(item.footage_seconds, 7.5)
        self.assertEqual(item.delta_seconds, 1.5)
        self.assertEqual(suggested_out_point(2.5, 6, 20), 8.5)

    def test_exceeding_footage_is_rejected(self):
        with self.assertRaises(ValueError):
            suggested_out_point(18, 6, 20)
        with self.assertRaises(ValueError):
            validate_sync_range(8, 3, 20, 6)
        with self.assertRaises(ValueError):
            validate_sync_range(0, 22, 20, 6)


class WaveformGuiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        # Avoid Qt's asynchronous FFmpeg decoder threads in offscreen GUI unit
        # tests; waveform extraction and project/range logic are tested separately.
        from PySide6.QtCore import QProcess
        # Keep mocked GUI unit tests free of Qt Multimedia backend threads.
        # Actual FFmpeg waveform extraction is integration-tested separately.
        player_patch = patch("nanners_creator_hub.narration_sync.QMediaPlayer")
        audio_patch = patch("nanners_creator_hub.narration_sync.QAudioOutput")
        process_patch = patch.object(QProcess, "start", autospec=True)
        player_patch.start()
        audio_patch.start()
        process_patch.start()
        self.addCleanup(process_patch.stop)
        self.addCleanup(audio_patch.stop)
        self.addCleanup(player_patch.stop)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.dir = Path(self.temp.name)
        self.audio = self.dir / "narration.wav"
        with wave.open(str(self.audio), "wb") as file:
            file.setnchannels(1)
            file.setsampwidth(2)
            file.setframerate(24000)
            file.writeframes(b"\x01\x00" * 24000)
        self.original = self.audio.read_bytes()
        self.video = self.dir / "video.mkv"
        self.video.write_bytes(b"not an actual video")
        project = new_project("Timing")
        section = new_section("Intro")
        section.update(
            narration_path=str(self.audio), footage_path=str(self.video),
            footage_in_seconds=2, footage_out_seconds=7
        )
        project["sections"] = [section]
        project["media"] = [
            {"path": str(self.audio), "kind": "Audio", "duration_seconds": 1.0, "status": "ready"},
            {"path": str(self.video), "kind": "Video", "duration_seconds": 20.0, "status": "ready"}
        ]
        self.project = project

    def test_no_footage_still_previews_audio(self):
        from nanners_creator_hub.narration_sync import NarrationSyncDialog
        dialog = NarrationSyncDialog(self.audio, 1.0)
        self.assertFalse(dialog.apply_button.isEnabled())
        self.assertFalse(dialog.match_button.isEnabled())
        dialog.reject()
        self.assertEqual(self.audio.read_bytes(), self.original)

    def test_match_and_apply(self):
        from nanners_creator_hub.narration_sync import NarrationSyncDialog
        dialog = NarrationSyncDialog(self.audio, 1.0, self.video, 20.0, 2, 7)
        dialog.match_narration()
        self.assertEqual(dialog.out_spin.value(), 3.0)
        self.assertIsNone(dialog.applied_range)
        dialog.apply_range()
        self.assertEqual(dialog.applied_range, (2, 3))
        self.assertEqual(self.audio.read_bytes(), self.original)

    def test_window_cancel_vs_apply(self):
        from PySide6.QtWidgets import QMessageBox
        from nanners_creator_hub.app import MainWindow
        from nanners_creator_hub.narration_sync import NarrationSyncDialog
        window = MainWindow()
        window.set_project(self.project, None)
        def cancel_preview(dialog):
            dialog.shutdown()
            return NarrationSyncDialog.DialogCode.Rejected
        with patch.object(NarrationSyncDialog, "exec", cancel_preview):
            window.open_narration_sync()
        self.assertFalse(window.dirty)
        self.assertEqual(window.selected_section()["footage_out_seconds"], 7)
        def apply_preview(dialog):
            dialog.applied_range = (2, 3)
            dialog.shutdown()
            return NarrationSyncDialog.DialogCode.Accepted
        with patch.object(NarrationSyncDialog, "exec", apply_preview):
            window.open_narration_sync()
        self.assertTrue(window.dirty)
        self.assertEqual(window.selected_section()["footage_out_seconds"], 3)
        self.assertIn("UNSAVED CHANGES", window.save_state_label.text())
        with patch.object(QMessageBox, "question",
                          return_value=QMessageBox.StandardButton.Discard):
            window.close()


if __name__ == "__main__":
    unittest.main()
