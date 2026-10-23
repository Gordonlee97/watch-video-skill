from __future__ import annotations

import contextlib
import io
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import download  # noqa: E402
import frames  # noqa: E402
import setup  # noqa: E402
import whisper  # noqa: E402


class PermissionWarningTest(unittest.TestCase):
    def _warnings_for(self, path: Path) -> str:
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            setup._check_file_permissions(path)
        return err.getvalue()

    @unittest.skipUnless(os.name == "nt", "Windows behaviour")
    def test_no_chmod_warning_on_windows(self):
        with tempfile.TemporaryDirectory() as tmp:
            env_file = Path(tmp) / ".env"
            env_file.write_text("X=1\n", encoding="utf-8")
            self.assertEqual(self._warnings_for(env_file), "")

    @unittest.skipIf(os.name == "nt", "POSIX permission bits")
    def test_world_readable_file_still_warns_on_posix(self):
        with tempfile.TemporaryDirectory() as tmp:
            env_file = Path(tmp) / ".env"
            env_file.write_text("X=1\n", encoding="utf-8")
            env_file.chmod(0o644)
            self.assertIn("chmod 600", self._warnings_for(env_file))


class MissingBinaryMessageTest(unittest.TestCase):
    def _message(self, fn) -> str:
        with mock.patch("shutil.which", return_value=None):
            with self.assertRaises(SystemExit) as ctx:
                fn()
        return str(ctx.exception.code)

    def test_missing_binary_messages_point_to_setup_not_brew(self):
        with tempfile.TemporaryDirectory() as tmp:
            calls = {
                "yt-dlp": lambda: download.download_url("https://example.com/v", Path(tmp)),
                "ffprobe": lambda: frames.get_metadata("v.mp4"),
                "ffmpeg (frames)": lambda: frames.extract("v.mp4", Path(tmp), fps=1.0),
                "ffmpeg (audio)": lambda: whisper.extract_audio("v.mp4", Path(tmp) / "a.mp3"),
            }
            for name, fn in calls.items():
                with self.subTest(name):
                    msg = self._message(fn)
                    self.assertNotIn("brew", msg)
                    self.assertIn("setup.py", msg)


class SetupCommandTest(unittest.TestCase):
    def test_uses_python_on_windows_and_python3_elsewhere(self):
        expected = "python" if os.name == "nt" else "python3"
        self.assertTrue(setup.setup_command().startswith(expected + " "))
        self.assertTrue(setup.setup_command().rstrip('"').endswith("setup.py"))


if __name__ == "__main__":
    unittest.main()
