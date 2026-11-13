import subprocess
import tempfile
import unittest
from pathlib import Path

from nanners_creator_hub.media import MediaProbeError, inspect_media, inspect_reference


class MediaTests(unittest.TestCase):
    def test_missing_file(self):
        with self.assertRaises(MediaProbeError):
            inspect_media("/nonexistent/nanners-creator-test.mp4")

    def test_invalid_media_error(self):
        with tempfile.TemporaryDirectory() as folder:
            file = Path(folder) / "invalid.mp4"
            file.write_text("not a video")
            with self.assertRaises(MediaProbeError):
                inspect_media(file)

    def test_missing_reference_retained(self):
        result = inspect_reference({"path": "/nonexistent/nanners-creator-test.mp4"})
        self.assertEqual(result["status"], "missing")

    def test_probe_audio_and_video_without_modification(self):
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            wav = folder / "voice.wav"
            mp4 = folder / "screen.mp4"
            subprocess.run(
                ["ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "lavfi",
                 "-i", "sine=frequency=1000:duration=1", "-y", str(wav)],
                check=True,
            )
            subprocess.run(
                ["ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "lavfi",
                 "-i", "color=c=black:s=160x90:r=30:d=1", "-c:v", "mpeg4",
                 "-y", str(mp4)],
                check=True,
            )
            before = [(p.stat().st_size, p.stat().st_mtime_ns) for p in (wav, mp4)]
            audio = inspect_media(wav)
            video = inspect_media(mp4)
            self.assertEqual(audio["kind"], "Audio")
            self.assertEqual(video["kind"], "Video")
            self.assertEqual(video["width"], 160)
            self.assertEqual(video["height"], 90)
            self.assertAlmostEqual(video["frame_rate"], 30, places=1)
            self.assertAlmostEqual(audio["duration_seconds"], 1, places=1)
            after = [(p.stat().st_size, p.stat().st_mtime_ns) for p in (wav, mp4)]
            self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
