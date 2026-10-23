from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from frames import extract  # noqa: E402


def _make_video(path: Path, lavfi_graph: str) -> None:
    subprocess.run(
        ["ffmpeg", "-loglevel", "error", "-y", "-filter_complex", lavfi_graph, "-pix_fmt", "yuv420p", str(path)],
        check=True,
    )


@unittest.skipUnless(shutil.which("ffmpeg"), "needs ffmpeg")
class ExtractTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def _red_then_blue(self) -> Path:
        video = self.tmp / "red_blue.mp4"
        _make_video(
            video,
            "color=c=red:s=160x120:r=10:d=6[a];color=c=blue:s=160x120:r=10:d=4[b];[a][b]concat=n=2:v=1",
        )
        return video

    def test_static_stretches_collapse_to_one_frame_with_true_timestamps(self):
        frames = extract(str(self._red_then_blue()), self.tmp / "out", fps=1.0, resolution=160)
        self.assertEqual([f["timestamp_seconds"] for f in frames], [0.0, 6.0])

    def test_timestamps_stay_absolute_with_start_offset(self):
        frames = extract(str(self._red_then_blue()), self.tmp / "out", fps=1.0, resolution=160, start_seconds=3.0)
        self.assertEqual([f["timestamp_seconds"] for f in frames], [3.0, 6.0])

    def test_time_offset_maps_clip_frames_to_source_time(self):
        # A section-downloaded clip starts at source time `time_offset`.
        frames = extract(str(self._red_then_blue()), self.tmp / "out", fps=1.0, resolution=160, time_offset=270.0)
        self.assertEqual([f["timestamp_seconds"] for f in frames], [270.0, 276.0])

    def test_changing_frames_are_all_kept(self):
        video = self.tmp / "moving.mp4"
        _make_video(video, "testsrc=duration=5:size=160x120:rate=10")
        frames = extract(str(video), self.tmp / "out", fps=2.0, resolution=160, start_seconds=1.0)
        self.assertEqual([f["timestamp_seconds"] for f in frames], [1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5])
        self.assertTrue(all(Path(f["path"]).exists() for f in frames))


if __name__ == "__main__":
    unittest.main()
