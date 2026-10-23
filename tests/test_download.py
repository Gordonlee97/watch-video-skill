from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import download  # noqa: E402


class SectionDownloadTest(unittest.TestCase):
    def _run(self, section, produce_video_on_call):
        """Run download_url with yt-dlp mocked; it writes video.mp4 only on the given call numbers."""
        calls = []

        def fake_run(cmd, **kwargs):
            calls.append(cmd)
            if len(calls) in produce_video_on_call:
                (out_dir / "video.mp4").write_bytes(b"x")
            return mock.Mock(returncode=0)

        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            with mock.patch.object(download.shutil, "which", return_value="yt-dlp"), \
                 mock.patch.object(download.subprocess, "run", side_effect=fake_run):
                result = download.download_url("https://example.com/v", out_dir, section=section)
        return result, calls

    def test_range_downloads_only_that_section(self):
        result, calls = self._run((270.0, 300.0), produce_video_on_call={1})
        self.assertEqual(len(calls), 1)
        self.assertIn("--download-sections", calls[0])
        self.assertEqual(calls[0][calls[0].index("--download-sections") + 1], "*270.0-300.0")
        self.assertEqual(result["clip_start"], 270.0)

    def test_open_ended_range_runs_to_end(self):
        _, calls = self._run((270.0, None), produce_video_on_call={1})
        self.assertEqual(calls[0][calls[0].index("--download-sections") + 1], "*270.0-inf")

    def test_no_range_downloads_whole_video(self):
        result, calls = self._run(None, produce_video_on_call={1})
        self.assertNotIn("--download-sections", calls[0])
        self.assertIsNone(result["clip_start"])

    def test_failed_section_download_falls_back_to_full_video(self):
        result, calls = self._run((270.0, 300.0), produce_video_on_call={2})
        self.assertEqual(len(calls), 2)
        self.assertNotIn("--download-sections", calls[1])
        self.assertIsNone(result["clip_start"])


class DiscardDownloadTest(unittest.TestCase):
    def test_downloaded_video_and_info_json_are_deleted(self):
        with tempfile.TemporaryDirectory() as tmp:
            video = Path(tmp) / "video.mp4"
            info = Path(tmp) / "video.info.json"
            subs = Path(tmp) / "video.en.vtt"
            for f in (video, info, subs):
                f.write_bytes(b"x")
            download.discard_download({"video_path": str(video), "downloaded": True})
            self.assertFalse(video.exists())
            self.assertFalse(info.exists())
            self.assertTrue(subs.exists(), "captions are small; leave them for inspection")

    def test_local_source_file_is_never_deleted(self):
        with tempfile.TemporaryDirectory() as tmp:
            video = Path(tmp) / "my-recording.mp4"
            video.write_bytes(b"x")
            download.discard_download(download.resolve_local(str(video)))
            self.assertTrue(video.exists())


if __name__ == "__main__":
    unittest.main()
