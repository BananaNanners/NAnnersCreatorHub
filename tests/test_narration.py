"""Kokoro WAV generation regression tests; no real user audio is created."""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
import wave
import zipfile
from pathlib import Path
from unittest.mock import patch

from nanners_creator_hub.kokoro import default_preferences, inspect_kokoro
from nanners_creator_hub.narration import (
    cleanup_job, kokoro_arguments, prepare_job, publish_take, safe_stem,
    validate_wav,
)


def fake_wav(destination: Path):
    with wave.open(str(destination), "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(24000)
        audio.writeframes(b"\\0\\0" * 2400)


class NarrationFileTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.folder = Path(temp.name)
        self.prefs = default_preferences()
        self.prefs["voice"] = "em_alex"
        self.prefs["model_path"] = str(self.folder / "fake-model.onnx")
        self.prefs["voices_path"] = str(self.folder / "fake-voices.bin")

    def test_reject_blank_and_excessively_long_scripts(self):
        with self.assertRaises(ValueError):
            prepare_job("  ", "narration", self.folder / "takes", self.prefs)
        with self.assertRaises(ValueError):
            prepare_job("A" * 60001, "narration", self.folder / "takes", self.prefs)

    def test_filename_sanitization_and_argument_boundaries(self):
        self.assertEqual(safe_stem("../../My Script?!"), "My-Script")
        job = prepare_job("Hello, Linux!", "../hi", self.folder / "takes", self.prefs)
        try:
            args = kokoro_arguments(job)
            self.assertEqual(args[0], str(job.input_script))
            self.assertEqual(args[1], str(job.temporary_wav))
            self.assertEqual(args[args.index("--voice") + 1], "em_alex")
            self.assertEqual(job.input_script.read_text(), "Hello, Linux!")
            self.assertEqual(job.stem, "hi")
        finally:
            cleanup_job(job)

    def test_publish_twice_creates_unique_unmodified_wavs_and_scripts(self):
        output = self.folder / "takes"
        original = output / "preexisting.wav"
        output.mkdir()
        original.write_bytes(b"DO NOT TOUCH")
        outputs = []
        for index in range(2):
            job = prepare_job(f"Take {index}", "Example", output, self.prefs)
            try:
                fake_wav(job.temporary_wav)
                target = publish_take(job)
                outputs.append(target)
                self.assertEqual(target.with_suffix(".txt").read_text(), f"Take {index}")
                self.assertFalse(target.with_suffix(".speech.txt").exists())
                validate_wav(target)
            finally:
                cleanup_job(job)
        self.assertNotEqual(outputs[0], outputs[1])
        self.assertEqual(original.read_bytes(), b"DO NOT TOUCH")
        self.assertTrue(all(p.is_file() for p in outputs))
        self.assertEqual(len(list(output.glob("*.txt"))), 2)  # one TXT for each WAV
        self.assertEqual(len(list(output.glob("*.wav"))), 3)  # two takes + untouched original
        self.assertFalse(any(p.name.startswith(".nanners-tts-") for p in output.iterdir()))

    def test_invalid_audio_never_published(self):
        job = prepare_job("Hello", "bad", self.folder / "takes", self.prefs)
        try:
            job.temporary_wav.write_bytes(b"NOT A WAV")
            with self.assertRaises(ValueError):
                publish_take(job)
        finally:
            cleanup_job(job)
        self.assertFalse(list((self.folder / "takes").glob("*.wav")))


class NarrationGuiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        # Qt FFmpeg decoder is exercised separately. GUI tests need only a
        # source URL assignment, not active backend decode threads.
        from PySide6.QtMultimedia import QMediaPlayer
        media_patcher = patch.object(QMediaPlayer, "setSource", autospec=True)
        media_patcher.start()
        self.addCleanup(media_patcher.stop)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.model = self.folder / "kokoro-v1.0.onnx"
        self.voices = self.folder / "voices-v1.0.bin"
        self.model.write_bytes(b"not a real model")
        with zipfile.ZipFile(self.voices, "w") as archive:
            archive.writestr("em_alex.npy", b"voice")
        self.prefs = default_preferences()
        self.prefs.update(
            model_path=str(self.model), voices_path=str(self.voices),
            voice="em_alex"
        )
        self.executable = self.folder / "mock-kokoro"
        self.make_fake_executable(success=True)

    def make_fake_executable(self, success: bool):
        if success:
            script = (
                f"#!{sys.executable}\n"
                "import sys, wave\n"
                "input_path, output_path = sys.argv[1:3]\n"
                "assert '--model' in sys.argv and '--voice' in sys.argv\n"
                "assert open(input_path, encoding='utf-8').read().strip()\n"
                "with wave.open(output_path, 'wb') as audio:\n"
                "    audio.setnchannels(1)\n"
                "    audio.setsampwidth(2)\n"
                "    audio.setframerate(24000)\n"
                "    audio.writeframes(b'\\x00\\x00' * 2400)\n"
            )
        else:
            script = f"#!{sys.executable}\nimport sys\nsys.exit(5)\n"
        self.executable.write_text(script)
        self.executable.chmod(0o755)

    def create_studio(self):
        from nanners_creator_hub.kokoro_studio import KokoroStudio
        fake_inspect = lambda prefs: inspect_kokoro(prefs, executable=str(self.executable))
        with patch("nanners_creator_hub.kokoro_studio.inspect_kokoro", fake_inspect), patch(
            "nanners_creator_hub.kokoro_studio.load_preferences", return_value=self.prefs
        ):
            studio = KokoroStudio()
            studio._mock_scan = fake_inspect
            studio.output_dir.setText(str(self.folder / "takes"))
            return studio

    def finish_job(self, studio):
        self.assertIsNotNone(studio.process)
        proc = studio.process
        if proc.state() != proc.ProcessState.NotRunning:
            self.assertTrue(proc.waitForFinished(6000), "Mock Kokoro process did not finish")
        self.app.processEvents()

    def test_generate_button_and_wav_take(self):
        studio = self.create_studio()
        self.assertFalse(studio.generate_button.isEnabled())
        studio.script_editor.setPlainText("Hello from the GUI")
        self.assertTrue(studio.generate_button.isEnabled())
        with patch("nanners_creator_hub.kokoro_studio.inspect_kokoro", studio._mock_scan):
            studio.generate_button.click()
        self.finish_job(studio)
        self.assertFalse(studio.is_generating)
        self.assertIsNotNone(studio.last_output)
        self.assertTrue(studio.last_output.is_file())
        self.assertEqual(studio.last_output.with_suffix(".txt").read_text(), "Hello from the GUI")
        self.assertFalse(studio.last_output.with_suffix(".speech.txt").exists())
        self.assertTrue(studio.play_button.isEnabled())
        self.assertIn("WAV created", studio.generation_status.text())
        self.assertTrue(studio.generate_button.isEnabled())
        studio.close()

    def test_failed_generation_preserves_output_folder(self):
        self.make_fake_executable(success=False)
        studio = self.create_studio()
        output = self.folder / "takes"
        output.mkdir(exist_ok=True)
        old_file = output / "older.wav"
        old_file.write_bytes(b"OLD")
        studio.script_editor.setPlainText("This must fail")
        with patch("nanners_creator_hub.kokoro_studio.inspect_kokoro", studio._mock_scan):
            studio.generate()
        self.finish_job(studio)
        self.assertIsNone(studio.last_output)
        self.assertEqual(old_file.read_bytes(), b"OLD")
        self.assertEqual(sorted(p.name for p in output.iterdir()), ["older.wav"])
        self.assertIn("exited with code", studio.generation_status.text())
        studio.close()


if __name__ == "__main__":
    unittest.main()
