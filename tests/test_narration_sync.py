"""Waveform and narration synchronization validation (headless-safe)."""
import unittest
from pathlib import Path

from nanners_creator_hub.waveform import (
    ffmpeg_waveform_args, peaks_from_pcm, suggested_out_point, validate_sync_range,
)


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
            peaks_from_pcm(b"\\x00\\x00", bins=0)

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


if __name__ == "__main__":
    unittest.main()
