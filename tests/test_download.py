from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import download  # noqa: E402


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
