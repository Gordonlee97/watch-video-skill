"""Non-ASCII text must survive the pipeline on Windows (cp1252 default locale)."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

import download  # noqa: E402
import setup  # noqa: E402


def _locale_env() -> dict:
    """Environment without UTF-8 overrides, so Python uses the OS default encoding."""
    env = dict(os.environ)
    env.pop("PYTHONUTF8", None)
    env.pop("PYTHONIOENCODING", None)
    return env


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "needs ffmpeg")
class ReportEncodingTest(unittest.TestCase):
    def test_report_with_emoji_title_survives_redirected_stdout(self):
        with tempfile.TemporaryDirectory() as tmp:
            video = Path(tmp) / "clip \U0001f525.mp4"
            subprocess.run(
                ["ffmpeg", "-loglevel", "error", "-f", "lavfi", "-i", "testsrc=duration=2:size=160x120:rate=10",
                 "-pix_fmt", "yuv420p", str(video)],
                check=True,
            )
            result = subprocess.run(
                [sys.executable, str(SCRIPTS / "watch.py"), str(video), "--no-whisper",
                 "--out-dir", str(Path(tmp) / "work")],
                capture_output=True, env=_locale_env(),
            )
            self.assertEqual(result.returncode, 0, result.stderr.decode("utf-8", "replace"))
            self.assertIn("clip \U0001f525.mp4", result.stdout.decode("utf-8"))
            self.assertTrue(video.exists(), "a local source video must never be deleted")


class ConfigEncodingTest(unittest.TestCase):
    def test_info_json_title_read_as_utf8(self):
        with tempfile.TemporaryDirectory() as tmp:
            info_path = Path(tmp) / "video.info.json"
            info_path.write_text(json.dumps({"title": "Café ünïcode", "uploader": "Zoë"}, ensure_ascii=False),
                                 encoding="utf-8")
            info = download._read_info(info_path, "https://example.com/v")
            self.assertEqual(info["title"], "Café ünïcode")
            self.assertEqual(info["uploader"], "Zoë")

    def test_env_value_read_as_utf8(self):
        with tempfile.TemporaryDirectory() as tmp:
            env_file = Path(tmp) / ".env"
            env_file.write_text("WATCH_NOTES_DIR=C:/Users/Zoë/Notes\n", encoding="utf-8")
            original = setup.CONFIG_FILE
            setup.CONFIG_FILE = env_file
            try:
                os.environ.pop("WATCH_NOTES_DIR", None)
                self.assertEqual(setup._read_env_key("WATCH_NOTES_DIR"), "C:/Users/Zoë/Notes")
            finally:
                setup.CONFIG_FILE = original

    def test_legacy_cp1252_env_still_readable(self):
        # Older setup.py runs wrote the template (with em dashes) in the locale codepage.
        with tempfile.TemporaryDirectory() as tmp:
            env_file = Path(tmp) / ".env"
            env_file.write_bytes("# Whisper — fallback\nGROQ_API_KEY=abc123\n".encode("cp1252"))
            original = setup.CONFIG_FILE
            setup.CONFIG_FILE = env_file
            try:
                os.environ.pop("GROQ_API_KEY", None)
                self.assertEqual(setup._read_env_key("GROQ_API_KEY"), "abc123")
                setup._write_setup_complete()
                self.assertEqual(setup._read_env_key("SETUP_COMPLETE"), "true")
            finally:
                setup.CONFIG_FILE = original


if __name__ == "__main__":
    unittest.main()
