from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from transcribe import parse_vtt  # noqa: E402

# Same shape as YouTube auto-captions: each cue repeats the previous cue's line
# above the new one, separated by 10ms cues that hold only the repeated line.
YOUTUBE_ROLLING = """WEBVTT
Kind: captions
Language: en

00:00:00.000 --> 00:00:01.550 align:start position:0%

alpha one.

00:00:01.550 --> 00:00:01.560 align:start position:0%
alpha one.


00:00:01.560 --> 00:00:04.830 align:start position:0%
alpha one.
beta<00:00:02.360><c> two</c><00:00:02.520><c> words</c>

00:00:04.830 --> 00:00:04.840 align:start position:0%
beta two words


00:00:04.840 --> 00:00:06.630 align:start position:0%
beta two words
gamma<00:00:04.960><c> three.</c>
"""

MANUAL = """WEBVTT

00:00:01.000 --> 00:00:03.000
Hello there
General Kenobi

00:00:03.500 --> 00:00:05.000
You are
a bold one

00:00:05.000 --> 00:00:06.000
a bold one
"""


def _parse(text: str) -> list[dict]:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "subs.vtt"
        path.write_text(text, encoding="utf-8")
        return parse_vtt(str(path))


class ParseVttTest(unittest.TestCase):
    def test_youtube_rolling_captions_have_no_repeated_text(self):
        segments = _parse(YOUTUBE_ROLLING)
        self.assertEqual(
            [(s["start"], s["text"]) for s in segments],
            [(1.55, "alpha one."), (1.56, "beta two words"), (4.84, "gamma three.")],
        )

    def test_manual_multiline_cues_are_kept_whole(self):
        segments = _parse(MANUAL)
        self.assertEqual(
            [s["text"] for s in segments],
            ["Hello there General Kenobi", "You are a bold one", "a bold one"],
        )


if __name__ == "__main__":
    unittest.main()
