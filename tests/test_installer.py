"""Installer tests run against an isolated HOME and XDG_DATA_HOME."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools/manage_install.py"


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name) / "home"
        self.data = self.home / ".local/share"
        self.home.mkdir()
        self.env = dict(os.environ, HOME=str(self.home), XDG_DATA_HOME=str(self.data))
        self.bin = self.home / ".local/bin/nanners-creator-hub"
        self.release_root = self.data / "nanners-creator-hub"

    def call(self, *args):
        return subprocess.run(
            [sys.executable, str(TOOL), *args],
            env=self.env, cwd=ROOT, capture_output=True, text=True,
        )

    def test_install_creates_launcher_and_shortcut(self):
        result = self.call("install")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(self.bin.is_file())
        self.assertTrue(os.access(self.bin, os.X_OK))
        self.assertTrue((self.data / "applications/org.nanners.CreatorHub.desktop").is_file())
        self.assertTrue((self.release_root / "current").is_symlink())
        self.assertTrue((self.release_root / "current/src/nanners_creator_hub/app.py").is_file())
        self.assertEqual(self.call("list").returncode, 0)
        self.assertIn("* 0.1.0-dev5", self.call("list").stdout)

    def test_refuses_unmanaged_launcher(self):
        self.bin.parent.mkdir(parents=True)
        self.bin.write_text("unrelated user script")
        original = self.bin.read_bytes()
        result = self.call("install")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.bin.read_bytes(), original)

    def test_existing_release_does_not_get_replaced(self):
        self.assertEqual(self.call("install").returncode, 0)
        existing = self.release_root / "releases/0.1.0-dev5/src/nanners_creator_hub/app.py"
        before = existing.read_bytes()
        result = self.call("install")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(existing.read_bytes(), before)

    def test_rollback_to_previous_installed_version(self):
        self.assertEqual(self.call("install").returncode, 0)
        release_path = self.release_root / "releases"
        archived = release_path / "0.1.0-dev4"
        shutil.copytree(release_path / "0.1.0-dev5", archived)
        result = self.call("rollback", "0.1.0-dev4")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.release_root / "current").resolve(), archived)
        self.assertIn("* 0.1.0-dev4", self.call("list").stdout)
        self.assertEqual(self.call("rollback", "0.1.0-dev5").returncode, 0)
        self.assertEqual((self.release_root / "current").resolve(), release_path / "0.1.0-dev5")

    def test_nonexistent_rollback_rejected(self):
        result = self.call("rollback", "unknown")
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.release_root / "current").exists())

    def test_install_does_not_touch_unrelated_files(self):
        keep = self.home / "Projects/tutorial.json"
        keep.parent.mkdir()
        keep.write_bytes(b"preserve user projects")
        self.assertEqual(self.call("install").returncode, 0)
        self.assertEqual(keep.read_bytes(), b"preserve user projects")


if __name__ == "__main__":
    unittest.main()
